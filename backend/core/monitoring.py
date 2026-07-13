"""Sentry helpers (Stage 7, D-A6). Env-gated: with no DSN nothing initializes and there
are zero network calls (tests run in this mode). PII is scrubbed before any event leaves
the process — only the user id is retained, never email/ip/cookies/auth headers.
"""
from typing import Optional

from backend.config import SENTRY_DSN_BACKEND


def sentry_enabled() -> bool:
    """True only when a backend DSN is configured (absent in dev/test)."""
    return bool(SENTRY_DSN_BACKEND)


def scrub_event(event: dict, hint: Optional[dict] = None) -> dict:
    """`before_send` hook: strip PII from an outgoing event.

    Keeps `user.id` only (drops email/username/ip); removes request cookies and the
    Cookie/Authorization headers; drops any stray top-level `email`/`username` keys.
    """
    user = event.get("user")
    if isinstance(user, dict):
        event["user"] = {"id": user["id"]} if "id" in user else {}

    req = event.get("request")
    if isinstance(req, dict):
        req.pop("cookies", None)
        headers = req.get("headers")
        if isinstance(headers, dict):
            for h in list(headers):
                if h.lower() in ("cookie", "authorization", "x-cron-secret"):
                    headers.pop(h, None)

    for pii_key in ("email", "username"):
        event.pop(pii_key, None)
    return event


def set_request_user(user_id: int) -> None:
    """Attach the user id (only) to the current Sentry scope. No-op when disabled."""
    if not sentry_enabled():
        return
    try:
        import sentry_sdk

        sentry_sdk.set_user({"id": str(user_id)})
    except Exception:  # noqa: BLE001 — monitoring must never break a request
        pass


def init_sentry() -> bool:
    """Initialize Sentry if a DSN is set. Returns True when initialized, else False."""
    if not sentry_enabled():
        return False
    from backend.config import (
        SENTRY_ENVIRONMENT,
        SENTRY_RELEASE,
        SENTRY_TRACES_SAMPLE_RATE,
    )
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN_BACKEND,
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        release=SENTRY_RELEASE or None,
        send_default_pii=False,          # never attach PII by default
        max_request_body_size="never",
        before_send=scrub_event,         # belt-and-suspenders PII scrub (D-A6)
        integrations=[FastApiIntegration()],
    )
    return True
