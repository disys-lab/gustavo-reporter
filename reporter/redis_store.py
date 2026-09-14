"""
Writes reports to the same Redis, in the same shape, gustavo's own
Cache.py already reads — see gustavo/src/Cache.py's module docstring
for the key format this must match exactly.
"""
import pickle

import redis.asyncio as redis

from reporter.config import CACHE_EXPIRE_TIME, CACHE_PREFIX, REDIS_AUTH_TOKEN, REDIS_HOST, REDIS_PORT
from reporter.models import StatusReport

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
