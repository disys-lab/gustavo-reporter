"""
gustavo-reporter — receives worker status reports over REST and writes
them to gustavo's Redis, replacing direct worker-to-Redis writes for
callers that use this instead. See README.md for the full design.
"""
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from reporter.gustavo_client import verify_credential
from reporter.models import StatusReport
from reporter.redis_store import store_report

app = FastAPI(title="gustavo-reporter")
_basic_auth = HTTPBasic()


@app.post("/api/reports/{device_group}")
async def submit_report(
    device_group: str,
    report: StatusReport,
    credentials: HTTPBasicCredentials = Depends(_basic_auth),
):
    """
    Accept one worker status report and store it in gustavo's Redis.

    Parameters
    ----------
    device_group : str
        The device group this report is for (path parameter).
    report : StatusReport
        Vitals + container stats for `report.node_id`.
    credentials : HTTPBasicCredentials
        The worker's Nebula username/token, via HTTP Basic auth.

    Returns
    -------
    dict
        ``{"error": False, "response": "stored"}`` on success.

    Raises
    ------
    HTTPException
        401 if the credential doesn't verify against gustavo; 403 if
        it verifies but isn't granted rw on `device_group`.

    Notes
    -----
    Authentication (is this a real Nebula identity) and authorization
    (is it allowed to report *as this device group*) are checked
    separately — a valid credential alone doesn't grant write access
    to every device group, only the ones it's been given rw on.
    """
    identity = await verify_credential(credentials.username, credentials.password)
    if identity is None:
        raise HTTPException(status_code=401, detail="Invalid credential")

    if not identity.is_admin and identity.device_groups.get(device_group) != "rw":
        raise HTTPException(status_code=403, detail=f"Not permitted to report for device group '{device_group}'")

    await store_report(device_group, report)
    return {"error": False, "response": "stored"}


@app.get("/health")
async def health():
    """Liveness check — does not touch Redis or gustavo."""
    return {"status": "ok"}
