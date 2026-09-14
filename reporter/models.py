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
