"""Client for gustavo's own API — currently just credential verification."""
import logging
from dataclasses import dataclass

import httpx

from reporter.config import GUSTAVO_API_HOST, GUSTAVO_API_PORT

logging.basicConfig(level=logging.INFO)


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
                f"http://{GUSTAVO_API_HOST}:{GUSTAVO_API_PORT}/api/auth/verify",
                json={"credential": f"{username}:{secret}"},
            )
        except httpx.RequestError as exc:
            # never log secret - username only, plus the exception type/message,
            # which is enough to tell a connection failure from a timeout.
            logging.warning(f"verify_credential({username!r}): request to gustavo failed - {type(exc).__name__}: {exc}")
            return None

    if resp.status_code != 200:
        logging.warning(f"verify_credential({username!r}): gustavo returned HTTP {resp.status_code}: {resp.text[:200]!r}")
        return None
    body = resp.json()
    if body.get("error"):
        logging.warning(f"verify_credential({username!r}): gustavo rejected the credential - {body.get('response')!r}")
        return None

    data = body["response"]
    return VerifiedIdentity(
        username=data["username"],
        is_admin=data["is_admin"],
        device_groups=data["device_groups"],
    )
