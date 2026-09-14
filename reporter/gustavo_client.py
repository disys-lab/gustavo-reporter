"""Client for gustavo's own API — currently just credential verification."""
from dataclasses import dataclass

import httpx

from reporter.config import GUSTAVO_API_URL


@dataclass
class VerifiedIdentity:
    username: str
    is_admin: bool
    device_groups: dict[str, str]  # {name: "ro"|"rw"}


async def verify_credential(username: str, secret: str) -> VerifiedIdentity | None:
    """
    Verify a worker's Nebula credential against gustavo's own /api/auth/verify.

    Parameters
    ----------
    username, secret : str
        The worker's Nebula username/token, as sent via HTTP Basic auth.

    Returns
    -------
    VerifiedIdentity or None
        None if the credential is invalid, or gustavo couldn't be reached.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(
                f"{GUSTAVO_API_URL}/api/auth/verify",
                json={"credential": f"{username}:{secret}"},
            )
        except httpx.RequestError:
            return None

    if resp.status_code != 200:
        return None
    body = resp.json()
    if body.get("error"):
        return None

    data = body["response"]
    return VerifiedIdentity(
        username=data["username"],
        is_admin=data["is_admin"],
        device_groups=data["device_groups"],
    )
