"""Public email-action endpoints. No login required — actions are authorized by a
signed token in the URL (D-N7). Currently: one-click unsubscribe (Israeli spam-law
compliance for broadcast email; also covers product email)."""
import aiosqlite
import structlog
from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse

from backend.core.database import get_db_connection
from backend.core.notifications import verify_unsubscribe_token

router = APIRouter(prefix="/api/email", tags=["email"])
log = structlog.get_logger(__name__)

_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FINARODA</title></head>
<body style="font-family:system-ui,sans-serif;background:#0b0d12;color:#e6e8ec;
display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0">
<div style="max-width:420px;padding:28px;text-align:center">
<h2 style="margin:0 0 12px">{headline}</h2>
<p style="color:#8593a2;line-height:1.5">{message}</p>
<p style="margin-top:20px;font-size:12px;color:#5c6672">FINARODA — analysis, not advice.</p>
</div></body></html>"""

_CATEGORY_LABEL = {
    "email_product": "product update emails",
    "email_broadcast": "FINARODA update emails",
}


def _page(headline: str, message: str, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(_PAGE.format(headline=headline, message=message), status_code=status_code)


@router.get("/unsubscribe")
async def unsubscribe(
    token: str = Query(...),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> HTMLResponse:
    """Flip the token's pref category to off. Idempotent; tampered tokens are rejected."""
    parsed = verify_unsubscribe_token(token)
    if parsed is None:
        return _page(
            "Link not valid",
            "This unsubscribe link is invalid or has expired. "
            "You can manage all notification preferences from Settings in the app.",
            status_code=400,
        )
    user_id, category = parsed
    # Idempotent: creating the prefs row if absent, then forcing the category off.
    await db.execute(
        "INSERT OR IGNORE INTO notification_prefs (user_id) VALUES (?)", (user_id,)
    )
    await db.execute(
        f"UPDATE notification_prefs SET {category} = 0, updated_at = CURRENT_TIMESTAMP "
        f"WHERE user_id = ?",
        (user_id,),
    )
    await db.commit()
    label = _CATEGORY_LABEL.get(category, "these emails")
    log.info("email_unsubscribe", user_id=user_id, category=category)
    return _page(
        "You're unsubscribed",
        f"You will no longer receive {label}. "
        f"You can re-enable them anytime from Settings in the app.",
    )
