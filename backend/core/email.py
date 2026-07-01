"""
Transactional email via Resend. Console fallback when RESEND_API_KEY is unset (dev).
FINARODA emails are English. Marketing goes via admin broadcast, never here.
"""
import logging

import httpx

from backend.config import (
    EMAIL_FROM_BRAND,
    EMAIL_REPLY_TO,
    RESEND_API_KEY,
    get_frontend_url,
)

log = logging.getLogger(__name__)

_RESEND_EMAILS_URL = "https://api.resend.com/emails"


def _wrap(headline: str, body_html: str, cta_url: str | None = None, cta_text: str | None = None) -> str:
    cta = (
        f'<p><a href="{cta_url}" style="background:#111;color:#e6e8ec;'
        f'padding:12px 20px;border-radius:8px;text-decoration:none;'
        f'font-family:monospace">{cta_text}</a></p>'
        if cta_url and cta_text
        else ""
    )
    return (
        f'<div style="font-family:system-ui,sans-serif;max-width:520px;margin:auto;'
        f'background:#0b0d12;color:#e6e8ec;padding:24px;border-radius:12px">'
        f"<h2>{headline}</h2>{body_html}{cta}"
        f'<hr style="border-color:#222"><small>FINARODA — analysis, not advice.</small></div>'
    )


async def _send(to_email: str, subject: str, html: str, text: str) -> bool:
    """POST to Resend. Returns True on 2xx, False otherwise. Never raises."""
    payload = {
        "from": EMAIL_FROM_BRAND,
        "to": [to_email],
        "reply_to": EMAIL_REPLY_TO,
        "subject": subject,
        "html": html,
        "text": text,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _RESEND_EMAILS_URL,
                json=payload,
                headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            )
        if resp.status_code in (200, 201):
            log.info("email_sent to=%s subject=%s", to_email, subject)
            return True
        log.error("resend_api_error status=%s body=%s", resp.status_code, resp.text[:200])
        return False
    except httpx.RequestError as exc:
        log.error("resend_request_error to=%s error=%s", to_email, str(exc))
        return False


class ResendEmailClient:
    async def send_magic_link(
        self, to_email: str, token: str, first_name: str | None = None
    ) -> str | bool:
        """
        Send the sign-in magic link.
        - RESEND_API_KEY set → sends; returns True/False.
        - RESEND_API_KEY unset → logs the link, returns the URL (dev mode).
        """
        verify_url = f"{get_frontend_url()}/verify?token={token}"
        if not RESEND_API_KEY:
            log.info("📧 [DEV] Magic link for %s: %s", to_email, verify_url)
            return verify_url

        greeting = f"Hi {first_name}," if first_name else "Hi,"
        html = _wrap(
            "Your FINARODA sign-in link",
            f"<p>{greeting}</p><p>Click to sign in. This link is valid for 15 minutes.</p>",
            verify_url,
            "Sign in",
        )
        text = f"{greeting}\n\nSign in to FINARODA:\n{verify_url}\n\nValid for 15 minutes."
        return await _send(to_email, "Your FINARODA sign-in link", html, text)


async def send_welcome_email(to_email: str, first_name: str | None = None) -> None:
    """Welcome email for a new user. No-op without RESEND_API_KEY. Non-blocking."""
    if not RESEND_API_KEY:
        log.info("send_welcome_email: RESEND_API_KEY unset, skipping %s", to_email)
        return
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    html = _wrap(
        "Welcome to FINARODA",
        f"<p>{greeting}</p><p>You have a <strong>14-day trial</strong>. "
        f"Scan → score → decision board. Analysis, not advice — you decide.</p>",
        get_frontend_url(),
        "Open FINARODA",
    )
    text = f"{greeting}\n\nWelcome to FINARODA. You have a 14-day trial.\n{get_frontend_url()}"
    await _send(to_email, "Welcome to FINARODA", html, text)


async def send_beta_approved_email(to_email: str, first_name: str | None = None) -> None:
    """Beta-access approval email. No-op without RESEND_API_KEY. Non-blocking."""
    if not RESEND_API_KEY:
        log.info("send_beta_approved_email: RESEND_API_KEY unset, skipping %s", to_email)
        return
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    html = _wrap(
        "You're in — FINARODA beta access",
        f"<p>{greeting}</p><p>Your beta access is approved. You have a 14-day trial.</p>",
        get_frontend_url(),
        "Sign in",
    )
    text = f"{greeting}\n\nYour FINARODA beta access is approved.\n{get_frontend_url()}"
    await _send(to_email, "You're in — FINARODA beta access", html, text)
