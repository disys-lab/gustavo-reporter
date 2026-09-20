"""
Writes reports to the same Redis, in the same shape, gustavo's own
Cache.py already reads — see gustavo/src/Cache.py's module docstring
for the key format this must match exactly.
"""
import pickle
import time

import redis.asyncio as redis

from reporter.config import (
    CACHE_EXPIRE_TIME, CACHE_PREFIX, DIRECTORY_PREFIX, DIRECTORY_TTL_SECONDS,
    REDIS_AUTH_TOKEN, REDIS_HOST, REDIS_PORT,
)
from reporter.models import NodeIdentity, StatusReport

_redis: redis.Redis | None = None


def _client() -> redis.Redis:
    """Lazily-constructed, process-wide Redis client."""
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT, password=REDIS_AUTH_TOKEN,
        )
    return _redis


async def store_report(device_group: str, report: StatusReport) -> None:
    """
    Write `report` to Redis under the key gustavo's Cache.py expects.

    Parameters
    ----------
    device_group : str
    report : StatusReport

    Notes
    -----
    Key: ``{CACHE_PREFIX}_{report_creation_time}_{device_group}@{node_id}``
    — matches Cache.keyPartition's expected 3-part, "_"-joined shape.
    Value: the report as a plain dict, pickled — matches what
    Cache.getIndividualVitals/getIndividualContainers unpickle and read.
    """
    key = f"{CACHE_PREFIX}_{report.report_creation_time}_{device_group}@{report.node_id}"
    value = pickle.dumps(report.model_dump())
    await _client().set(key, value, ex=CACHE_EXPIRE_TIME)


def _directory_key(device_group: str, node_id: str) -> str:
    """Key for one worker's directory entry - one current record per node_id, not a log."""
    return f"{DIRECTORY_PREFIX}_{device_group}@{node_id}"


async def store_identity(device_group: str, identity: NodeIdentity) -> None:
    """
    Upsert `identity` into the worker directory for `device_group`.

    Parameters
    ----------
    device_group : str
    identity : NodeIdentity

    Notes
    -----
    Unlike `store_report`, this overwrites the same key on every call
    (one current record per node_id) rather than writing a new
    timestamped key each time. Only applies a Redis TTL when
    `DIRECTORY_TTL_SECONDS` is a positive integer - unset or -1 means
    the entry persists until explicitly overwritten or deleted.

    `updated_at` is stamped here, server-side, rather than trusting a
    caller-supplied value - keeps it meaningful across workers with
    unsynced clocks.
    """
    key = _directory_key(device_group, identity.node_id)
    value = pickle.dumps({**identity.model_dump(), "updated_at": int(time.time())})
    if DIRECTORY_TTL_SECONDS > 0:
        await _client().set(key, value, ex=DIRECTORY_TTL_SECONDS)
    else:
        await _client().set(key, value)


async def list_identities(device_group: str) -> list[dict]:
    """
    List all worker directory entries for `device_group`.

    Parameters
    ----------
    device_group : str

    Returns
    -------
    list of dict
        Each entry's `NodeIdentity.model_dump()` shape. Entries whose
        key disappears between the scan and the read (e.g. TTL expiry
        mid-scan) are silently skipped rather than erroring.
    """
    client = _client()
    entries = []
    async for key in client.scan_iter(match=f"{DIRECTORY_PREFIX}_{device_group}@*"):
        value = await client.get(key)
        if value is not None:
            entries.append(pickle.loads(value))
    return entries


async def delete_identity(device_group: str, node_id: str) -> None:
    """
    Remove one worker's directory entry.

    Parameters
    ----------
    device_group : str
    node_id : str
    """
    await _client().delete(_directory_key(device_group, node_id))
