"""Client-facing in-app broadcast banner (B7d). Returns the latest broadcast whose
audience matches the current user, for a dismissible banner that never covers SCAN or
the disclaimer (enforced client-side). Read-only; composing/sending is admin-only."""
import aiosqlite
import structlog
from fastapi import APIRouter, Depends

from backend.core.auth import get_current_user
from backend.core.database import get_db_connection
from backend.models.auth import CurrentUser

router = APIRouter(prefix="/api/broadcasts", tags=["broadcasts"])
log = structlog.get_logger(__name__)


@router.get("/active")
async def active_banner(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Latest in-app broadcast targeting this user, or {banner: null}."""
    rows = await db.execute_fetchall(
        """SELECT id, title, body, audience, target_tier
             FROM admin_broadcasts
            WHERE channel_in_app = 1
            ORDER BY created_at DESC LIMIT 20"""
    )
    is_trial_ending = False
    if user.subscription_status == "trial":
        te = await db.execute_fetchall(
            "SELECT 1 FROM users WHERE internal_id=? AND trial_ends_at "
            "BETWEEN datetime('now') AND datetime('now','+3 days')",
            (user.internal_id,),
        )
        is_trial_ending = bool(te)

    for r in rows:
        d = dict(r)
        aud = d["audience"]
        if aud == "all":
            match = True
        elif aud == "plan":
            match = d["target_tier"] == user.tier
        elif aud == "trial_ending":
            match = is_trial_ending
        else:
            match = False
        if match:
            return {"banner": {"id": d["id"], "title": d["title"], "body": d["body"]}}
    return {"banner": None}
