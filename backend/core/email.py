"""
Transactional email via Resend. Console fallback when RESEND_API_KEY is unset (dev).
FINARODA emails are English. Marketing goes via admin broadcast, never here.
"""
import logging

import httpx

from backend.config import (
    API_URL,
    EMAIL_FROM_BRAND,
    EMAIL_REPLY_TO,
    RESEND_API_KEY,
    get_frontend_url,
)
from backend.core.notifications import make_unsubscribe_token

log = logging.getLogger(__name__)

_RESEND_EMAILS_URL = "https://api.resend.com/emails"


def unsubscribe_url(user_id: int, category: str) -> str:
    """Signed one-click unsubscribe link for a pref category (D-N7)."""
    token = make_unsubscribe_token(user_id, category)
    return f"{API_URL}/api/email/unsubscribe?token={token}"


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
        f'<hr style="border-color:#222"><small>FINARODA - analysis, not advice.</small></div>'
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


# ── Stage 5 flows — pure renderers (testable) + send wrappers (DEV fallback) ──
# Renderers return (subject, html, text). Tests assert on the rendered body, which is
# why they are pure and separate from the network send.

def render_trial_reminder(first_name: str | None, days_left: int) -> tuple[str, str, str]:
    """Day-11 trial reminder. No auto-charge — it prompts an active choice."""
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    day_phrase = "a day" if days_left == 1 else f"{days_left} days"
    subject = "Your FINARODA trial is ending soon"
    html = _wrap(
        "Your trial is ending soon",
        f"<p>{greeting}</p><p>Your FINARODA trial ends in {day_phrase}. "
        f"There is no automatic charge. Choose a paid plan to keep the full toolkit, "
        f"or continue on Free. You decide.</p>",
        f"{get_frontend_url()}/subscribe",
        "Choose a plan",
    )
    text = (
        f"{greeting}\n\nYour FINARODA trial ends in {day_phrase}. No automatic charge. "
        f"Choose a paid plan or continue on Free:\n{get_frontend_url()}/subscribe"
    )
    return subject, html, text


def render_reveal_teaser(first_name: str | None) -> tuple[str, str, str]:
    """Journal reveal teaser (D-N5). Contains ZERO outcome values — the reveal happens
    only on the user's next scan. Copy is fixed and content-free by design."""
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    subject = "A journal reveal is waiting"
    html = _wrap(
        "A journal reveal is waiting",
        f"<p>{greeting}</p><p>A journal reveal is waiting. "
        f"Run your next scan to unlock it.</p>",
        f"{get_frontend_url()}/dashboard",
        "Run a scan",
    )
    text = (
        f"{greeting}\n\nA journal reveal is waiting. Run your next scan to unlock it.\n"
        f"{get_frontend_url()}/dashboard"
    )
    return subject, html, text


def render_broadcast(subject: str, body: str, unsub_link: str) -> tuple[str, str, str]:
    """Admin broadcast body with a mandatory one-click unsubscribe link (D-N6)."""
    safe_body = body.replace("\n", "<br>")
    html = _wrap(
        subject,
        f"<p>{safe_body}</p>",
        None,
        None,
    ) + (
        f'<div style="max-width:520px;margin:8px auto;font-family:system-ui,sans-serif">'
        f'<small style="color:#8593A2">You are receiving this because you opted in to '
        f'FINARODA updates. <a href="{unsub_link}" style="color:#8593A2">Unsubscribe</a>.'
        f"</small></div>"
    )
    text = f"{body}\n\n---\nUnsubscribe from FINARODA updates: {unsub_link}"
    return subject, html, text


async def _send_or_log(to_email: str, subject: str, html: str, text: str) -> bool:
    """Send via Resend, or log the full payload in DEV (no RESEND_API_KEY). D-N8:
    zero network calls in dev/test — mirrors DEV_RETURN_MAGIC_LINK."""
    if not RESEND_API_KEY:
        log.info("📧 [DEV] email to=%s subject=%s\n%s", to_email, subject, text)
        return True
    return await _send(to_email, subject, html, text)


async def send_trial_reminder_email(
    to_email: str, first_name: str | None, days_left: int
) -> bool:
    subject, html, text = render_trial_reminder(first_name, days_left)
    return await _send_or_log(to_email, subject, html, text)


async def send_reveal_teaser_email(to_email: str, first_name: str | None) -> bool:
    subject, html, text = render_reveal_teaser(first_name)
    return await _send_or_log(to_email, subject, html, text)


async def send_broadcast_email(
    to_email: str, user_id: int, subject: str, body: str
) -> bool:
    subject, html, text = render_broadcast(subject, body, unsubscribe_url(user_id, "email_broadcast"))
    return await _send_or_log(to_email, subject, html, text)
