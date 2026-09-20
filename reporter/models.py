"""Request/response schemas for the reports API."""
from pydantic import BaseModel


class UsageStats(BaseModel):
    total: int
    used: int
    free: int


class CpuUsage(BaseModel):
    cores: int
    used_percent: float


class StatusReport(BaseModel):
    """
    A single worker status report.

    Field names and shapes match what gustavo's Cache.py already reads
    (see gustavo/src/Cache.py's getIndividualVitals/getIndividualContainers)
    so the stored value needs no translation on the read side.
    """
    node_id: str
    report_creation_time: int
    memory_usage: UsageStats
    root_disk_usage: UsageStats
    cpu_usage: CpuUsage
    apps_containers: list[dict]


class NodeIdentity(BaseModel):
    """
    A single worker's self-reported identity: a stable id plus its
    currently-observed network location. `device_group` is not a field
    here - like StatusReport, it's supplied via the URL path instead,
    since it also drives the write-authorization check.

    `node_id` is the same opaque, caller-supplied identity StatusReport
    uses - generated and persisted by the worker itself, not inferred
    by reporter.
    """
    node_id: str
    host_ip: str
    remote_ip: str


class WhoAmI(BaseModel):
    """Response for `GET /whoami` - the caller's address as reporter observes it."""
    remote_ip: str
