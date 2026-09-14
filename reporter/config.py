"""
Environment-driven configuration, read once at import time.

Mirrors gustavo's own os.environ.get(...) style rather than a config
file — reporter has no persistent state of its own to justify one.
"""
import os

# Gustavo's Next.js port (NOT FastAPI's 8000 — that's bound to 127.0.0.1
# inside gustavo's own container and unreachable from here). /api/* is
# proxied through to FastAPI by Next.js's own rewrites.
GUSTAVO_API_URL = os.environ.get("GUSTAVO_API_URL", "http://gustavo:3000")

REDIS_HOST = os.environ.get("REDIS_HOST", "")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_AUTH_TOKEN = os.environ.get("REDIS_AUTH_TOKEN", "")

# Must match gustavo's own CACHE_PREFIX/CACHE_EXPIRE_TIME (platform.yaml)
# for Cache.py to find what reporter writes.
CACHE_PREFIX = os.environ.get("CACHE_PREFIX", "gustavo-reports")
CACHE_EXPIRE_TIME = int(os.environ.get("CACHE_EXPIRE_TIME", "120"))
