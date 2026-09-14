# gustavo-reporter

REST alternative to gustavo-worker's direct Redis writes for status
reports (vitals + container stats). Workers keep the ability to write
to Redis directly — this is an additional path, not a replacement.

## Why

Workers writing straight to Redis means every worker needs Redis
network access and the platform's shared Redis credential. Reporter
lets a worker report over HTTPS instead, authenticated with the same
Nebula identity it already uses for the Manager — no direct Redis
access required for that worker.

## API

### `POST /api/reports/{device_group}`

HTTP Basic auth (Nebula username/token). Body:

```json
{
  "node_id": "worker-01",
  "report_creation_time": 1741270000,
  "memory_usage": {"total": 8192, "used": 4096, "free": 4096},
  "root_disk_usage": {"total": 100000, "used": 50000, "free": 50000},
  "cpu_usage": {"cores": 4, "used_percent": 23.5},
  "apps_containers": [{"name": "/my_app", "cpu_stats": {}, "precpu_stats": {}, "memory_stats": {}}]
}
```

`node_id` is an opaque, caller-supplied worker identity. Reporter
does not infer it from the network connection — a self-resolved
hostname (`socket.getfqdn()`, what gustavo-worker's `reporting.py`
currently does) returns a container-internal address, not a real
host identifier, and the request's observed peer address is just as
unreliable behind NAT/a proxy or when multiple workers share egress.
Whoever calls this endpoint is responsible for supplying a `node_id`
that's actually distinct per worker.

Responses: `200` on success, `401` if the credential doesn't verify,
`403` if it verifies but isn't granted `rw` on `device_group`.

### `GET /health`

Liveness only — doesn't touch Redis or gustavo.

## How a report gets authorized

1. Reporter calls gustavo's `POST /api/auth/verify` with the
   credential from the request's Basic auth header.
2. Gustavo verifies it the same way `/api/auth/login` does, and
   returns the identity's device-group grants — no session token
   minted for this.
3. Reporter allows the write only if the identity is admin, or has
   `rw` on the specific `device_group` in the request path. A valid
   credential alone does not grant write access to every device
   group.

Reporter never talks to Nebula directly and holds no Nebula
credentials of its own — every check is delegated to gustavo.

## Storage

Reports are pickled and written to the *same* Redis gustavo's own
`Cache.py` reads, in the same key format:

```
{CACHE_PREFIX}_{report_creation_time}_{device_group}@{node_id}
```

Gustavo's Dashboard/Monitoring pages work against reports written
this way with no changes on gustavo's side.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `GUSTAVO_API_HOST` / `GUSTAVO_API_PORT` | `gustavo` / `3000` | Where to reach gustavo's own API. Port **must** be gustavo's Next.js port — **not** FastAPI's 8000, which is bound to `127.0.0.1` inside gustavo's own container. `/api/*` is proxied through by Next.js. |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_AUTH_TOKEN` | — / `6379` / — | Same Redis instance gustavo's platform config points at. |
| `CACHE_PREFIX` | `gustavo-reports` | Must match gustavo's own `CACHE_PREFIX`. |
| `CACHE_EXPIRE_TIME` | `120` | Redis key TTL in seconds. Must match gustavo's own `CACHE_EXPIRE_TIME` for consistent expiry behavior. |

## Running

```bash
docker build -t gustavo-reporter .
docker run -d --name gustavo-reporter -p 8080:8080 \
  -e GUSTAVO_API_HOST=gustavo -e GUSTAVO_API_PORT=3000 \
  -e REDIS_HOST=... -e REDIS_AUTH_TOKEN=... \
  --network <same network as the gustavo container> \
  gustavo-reporter
```

Or run directly for local development:

```bash
pip install -r requirements.txt
GUSTAVO_API_HOST=localhost GUSTAVO_API_PORT=3000 REDIS_HOST=localhost REDIS_AUTH_TOKEN=... \
  uvicorn reporter.main:app --reload --port 8080
```

### Testing without a real worker

```bash
curl -u nebula:nebula -X POST http://localhost:8080/api/reports/testdevicegroup1 \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "test-worker-1",
    "report_creation_time": 1741270000,
    "memory_usage": {"total": 8192, "used": 4096, "free": 4096},
    "root_disk_usage": {"total": 100000, "used": 50000, "free": 50000},
    "cpu_usage": {"cores": 4, "used_percent": 23.5},
    "apps_containers": []
  }'
```

## Current scope

- Write path only. There's no read/query API yet — viewing reports
  still goes through gustavo's own (currently admin-only) Monitoring
  endpoints, reading the same Redis.
- gustavo-worker itself is unchanged — it doesn't call this yet.
  Adding that is a separate, later task; this repo is tested against
  a stub client (see above) until then.
