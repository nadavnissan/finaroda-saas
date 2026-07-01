"""
Google OAuth ID-token verification via Google's tokeninfo endpoint.

Hardened (SPEC §4): issuer (`iss`) is always enforced; audience (`aud`) is enforced
against GOOGLE_CLIENT_ID when set, and in production an empty GOOGLE_CLIENT_ID is a
hard error (we refuse to skip audience verification silently).
"""
import logging

import httpx

from backend.config import ENVIRONMENT, GOOGLE_CLIENT_ID

log = logging.getLogger(__name__)

_GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
_VALID_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


async def verify_google_id_token(id_token: str) -> dict:
    """
    Verify a Google ID token. Returns {email, given_name, family_name, picture, google_sub}.
    Raises ValueError on any invalid/expired/mismatched token.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(_GOOGLE_TOKENINFO_URL, params={"id_token": id_token})
    except httpx.RequestError as exc:
        raise ValueError(f"Google tokeninfo request failed: {exc}") from exc

    if resp.status_code != 200:
        raise ValueError(f"Google tokeninfo returned {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    if "error_description" in data:
        raise ValueError(f"Invalid Google token: {data['error_description']}")

    # Issuer — always enforced.
    if data.get("iss") not in _VALID_ISSUERS:
        raise ValueError(f"Invalid token issuer: {data.get('iss')!r}")

    # Audience — enforced against the configured client id; never silently skipped.
    if GOOGLE_CLIENT_ID:
        if data.get("aud") != GOOGLE_CLIENT_ID:
            raise ValueError(
                f"Token audience mismatch. Expected {GOOGLE_CLIENT_ID!r}, got {data.get('aud')!r}"
            )
    elif ENVIRONMENT in ("production", "staging"):
        raise ValueError(
            "GOOGLE_CLIENT_ID is not set — refusing to verify Google tokens without audience "
            "checking in production/staging."
        )
    else:
        log.warning("google_oauth: GOOGLE_CLIENT_ID empty (dev) — audience check skipped")

    if data.get("email_verified") != "true":
        raise ValueError("Google account email is not verified")

    log.info("google_token_verified sub=%s", data.get("sub"))
    return {
        "email": data.get("email", "").lower(),
        "given_name": data.get("given_name", ""),
        "family_name": data.get("family_name", ""),
        "picture": data.get("picture", ""),
        "google_sub": data.get("sub", ""),
    }
