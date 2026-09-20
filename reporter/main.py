"""
gustavo-reporter — receives worker status reports over REST and writes
them to gustavo's Redis, replacing direct worker-to-Redis writes for
callers that use this instead. See README.md for the full design.
"""
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from reporter.gustavo_client import verify_credential
from reporter.models import NodeIdentity, StatusReport, WhoAmI
from reporter.redis_store import delete_identity, list_identities, store_identity, store_report

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


@app.get("/whoami", response_model=WhoAmI)
async def whoami(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(_basic_auth),
):
    """
    Return the caller's address as reporter observes it.

    Parameters
    ----------
    request : Request
        Used only for `request.client.host` - the direct TCP peer
        address, not a caller-supplied value.
    credentials : HTTPBasicCredentials
        The worker's Nebula username/token, via HTTP Basic auth.

    Returns
    -------
    WhoAmI
        ``{"remote_ip": ...}``.

    Raises
    ------
    HTTPException
        401 if the credential doesn't verify against gustavo.

    Notes
    -----
    No device-group authorization check - any valid Nebula identity
    may call this, since it returns nothing about any device group,
    only the caller's own observed address. Requires auth anyway so
    this can't be used as an open IP-echo service by anyone who finds
    the endpoint.

    Like `node_id` in StatusReport, this is only as reliable as the
    network path to reporter - if reporter itself sits behind another
    reverse proxy, `request.client.host` reflects that proxy, not the
    original caller, unless the proxy forwards and reporter is
    configured to trust `X-Forwarded-For` (not currently done here).
    """
    identity = await verify_credential(credentials.username, credentials.password)
    if identity is None:
        raise HTTPException(status_code=401, detail="Invalid credential")

    return WhoAmI(remote_ip=request.client.host if request.client else "")


@app.post("/api/directory/{device_group}")
async def submit_identity(
    device_group: str,
    identity_report: NodeIdentity,
    credentials: HTTPBasicCredentials = Depends(_basic_auth),
):
    """
    Upsert one worker's identity into the directory for `device_group`.

    Parameters
    ----------
    device_group : str
        The device group this identity is for (path parameter).
    identity_report : NodeIdentity
        The worker's own id, host ip, and remote ip.
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
    Same authentication/authorization split as `submit_report` - a
    valid credential alone does not grant write access to every
    device group, only the ones it's been given rw on.
    """
    identity = await verify_credential(credentials.username, credentials.password)
    if identity is None:
        raise HTTPException(status_code=401, detail="Invalid credential")

    if not identity.is_admin and identity.device_groups.get(device_group) != "rw":
        raise HTTPException(status_code=403, detail=f"Not permitted to report for device group '{device_group}'")

    await store_identity(device_group, identity_report)
    return {"error": False, "response": "stored"}


@app.get("/api/directory/{device_group}")
async def get_directory(
    device_group: str,
    credentials: HTTPBasicCredentials = Depends(_basic_auth),
):
    """
    List the worker directory for `device_group`.

    Parameters
    ----------
    device_group : str
        The device group to list (path parameter).
    credentials : HTTPBasicCredentials
        A Nebula username/token, via HTTP Basic auth.

    Returns
    -------
    dict
        ``{"error": False, "response": [NodeIdentity-shaped dicts]}``.

    Raises
    ------
    HTTPException
        401 if the credential doesn't verify against gustavo; 403 if
        it verifies but has no grant (ro or rw) on `device_group`.

    Notes
    -----
    Unlike the write path, `ro` is sufficient here - viewing the
    directory doesn't need write access, matching gustavo's own
    ro-to-view/rw-to-change convention elsewhere.
    """
    identity = await verify_credential(credentials.username, credentials.password)
    if identity is None:
        raise HTTPException(status_code=401, detail="Invalid credential")

    if not identity.is_admin and identity.device_groups.get(device_group) is None:
        raise HTTPException(status_code=403, detail=f"Not permitted for device group '{device_group}'")

    entries = await list_identities(device_group)
    return {"error": False, "response": entries}


@app.delete("/api/directory/{device_group}/{node_id}")
async def remove_identity(
    device_group: str,
    node_id: str,
    credentials: HTTPBasicCredentials = Depends(_basic_auth),
):
    """
    Remove one worker's directory entry.

    Parameters
    ----------
    device_group : str
        The device group the entry belongs to (path parameter).
    node_id : str
        The worker's own id (path parameter).
    credentials : HTTPBasicCredentials
        The worker's Nebula username/token, via HTTP Basic auth.

    Returns
    -------
    dict
        ``{"error": False, "response": "deleted"}`` on success.

    Raises
    ------
    HTTPException
        401 if the credential doesn't verify against gustavo; 403 if
        it verifies but isn't granted rw on `device_group`.

    Notes
    -----
    rw-gated, same tier as the write path - deleting a directory entry
    is a mutation, not a view.
    """
    identity = await verify_credential(credentials.username, credentials.password)
    if identity is None:
        raise HTTPException(status_code=401, detail="Invalid credential")

    if not identity.is_admin and identity.device_groups.get(device_group) != "rw":
        raise HTTPException(status_code=403, detail=f"Not permitted to modify device group '{device_group}'")

    await delete_identity(device_group, node_id)
    return {"error": False, "response": "deleted"}


@app.get("/health")
async def health():
    """Liveness check — does not touch Redis or gustavo."""
    return {"status": "ok"}
