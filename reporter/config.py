"""
Environment-driven configuration, read once at import time.

Mirrors gustavo's own os.environ.get(...) style rather than a config
file — reporter has no persistent state of its own to justify one.
"""
import os

# Host/port kept separate, matching every other service's own config
# (MANAGER_HOST/MANAGER_PORT, REDIS_HOST/REDIS_PORT, ...) rather than
# one pre-built URL. GUSTAVO_API_PORT must be gustavo's Next.js port
# (NOT FastAPI's 8000 — that's bound to 127.0.0.1 inside gustavo's own
# container and unreachable from here). /api/* is proxied through to
# FastAPI by Next.js's own rewrites.
GUSTAVO_API_HOST = os.environ.get("GUSTAVO_API_HOST", "gustavo")
GUSTAVO_API_PORT = os.environ.get("GUSTAVO_API_PORT", "3000")

REDIS_HOST = os.environ.get("REDIS_HOST", "")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_AUTH_TOKEN = os.environ.get("REDIS_AUTH_TOKEN", "")

# Must match gustavo's own CACHE_PREFIX/CACHE_EXPIRE_TIME (platform.yaml)
# for Cache.py to find what reporter writes.
CACHE_PREFIX = os.environ.get("CACHE_PREFIX", "gustavo-reports")
CACHE_EXPIRE_TIME = int(os.environ.get("CACHE_EXPIRE_TIME", "120"))

# Key prefix for the worker identity directory - separate namespace from
# CACHE_PREFIX above, since directory entries are upserted-in-place
# (one current record per node_id) rather than a report-per-timestamp log.
DIRECTORY_PREFIX = os.environ.get("DIRECTORY_PREFIX", "gustavo-directory")

# Gustavo-Settings-managed - injected as an env var whenever gustavo
# launches/restarts this container. Unset or -1 means directory entries
# never expire; a positive integer is the Redis TTL in seconds,
# reapplied on every write.
DIRECTORY_TTL_SECONDS = int(os.environ.get("DIRECTORY_TTL_SECONDS", "-1"))
