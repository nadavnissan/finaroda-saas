"""B5 profile API (F5): identity, remembered scan settings, XP total.

Settings are display & geometry only (Analysis Lens / Risk Style / coin prefs) — never
what counts as an opportunity (RED LINE §3.5.5). Call-sign is the user's identity from
onboarding S9; if never set we derive a stable fallback from the email local-part.
"""
import json
import re
from datetime import datetime, timezone

import aiosqlite
import structlog
from fastapi import APIRouter, Depends

from backend.core.auth import get_current_user
from backend.core.database import get_db_connection
from backend.models.auth import CurrentUser
from backend.models.profile import (
    ProfileResponse,
    ProfileSettings,
    SettingsUpdate,
    TrialState,
)

router = APIRouter(prefix="/api/profile", tags=["profile"])
log = structlog.get_logger(__name__)


def _fallback_call_sign(email: str) -> str:
    local = email.split("@", 1)[0]
    cleaned = re.sub(r"[^A-Za-z0-9]", "", local).upper()
    return cleaned or "TRADER"


async def _get_settings_row(db: aiosqlite.Connection, user_id: int) -> dict:
    rows = await db.execute_fetchall(
        """SELECT call_sign, analysis_lens, risk_style, coin_prefs, palette
             FROM user_settings WHERE user_id = ?""",
        (user_id,),
    )
    if rows:
        return dict(rows[0])
    # Lazily create defaults on first read.
    await db.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))
    await db.commit()
    return {
        "call_sign": None, "analysis_lens": "full", "risk_style": "balanced",
        "coin_prefs": "[]", "palette": "terminal",
    }


def _trial_state(row: dict) -> TrialState | None:
    if row.get("subscription_status") != "trial":
        return None
    started = row.get("trial_started_at")
    ends = row.get("trial_ends_at")
    if not started or not ends:
        return TrialState(active=True, day=1, total=14)
    s = datetime.fromisoformat(started).replace(tzinfo=timezone.utc)
    e = datetime.fromisoformat(ends).replace(tzinfo=timezone.utc)
    total = max(1, round((e - s).total_seconds() / 86400))
    now = datetime.now(timezone.utc)
    day = min(total, max(1, (now - s).days + 1))
    return TrialState(active=now < e, day=day, total=total)


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> ProfileResponse:
    urows = await db.execute_fetchall(
        """SELECT email, tier, subscription_status, trial_started_at, trial_ends_at
             FROM users WHERE internal_id = ?""",
        (user.internal_id,),
    )
    urow = dict(urows[0]) if urows else {}
    s = await _get_settings_row(db, user.internal_id)

    xp_rows = await db.execute_fetchall(
        "SELECT COALESCE(SUM(amount), 0) FROM xp_events WHERE user_id = ?",
        (user.internal_id,),
    )
    xp_total = xp_rows[0][0] if xp_rows else 0

    try:
        coin_prefs = json.loads(s.get("coin_prefs") or "[]")
    except (TypeError, ValueError):
        coin_prefs = []

    return ProfileResponse(
        call_sign=s.get("call_sign") or _fallback_call_sign(user.email),
        email=user.email,
        tier=urow.get("tier", user.tier),
        subscription_status=urow.get("subscription_status", user.subscription_status),
        trial=_trial_state(urow),
        xp_total=xp_total,
        settings=ProfileSettings(
            analysis_lens=s.get("analysis_lens", "full"),
            risk_style=s.get("risk_style", "balanced"),
            coin_prefs=coin_prefs,
            palette=s.get("palette", "terminal"),
        ),
    )


@router.put("/settings", response_model=ProfileResponse)
async def update_settings(
    body: SettingsUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> ProfileResponse:
    """Persist remembered settings. Only the display/geometry fields, never a threshold."""
    await db.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user.internal_id,))
    updates: list[str] = []
    params: list = []
    if body.call_sign is not None:
        updates.append("call_sign = ?")
        params.append(body.call_sign.strip()[:32] or None)
    if body.analysis_lens is not None:
        updates.append("analysis_lens = ?")
        params.append(body.analysis_lens)
    if body.risk_style is not None:
        updates.append("risk_style = ?")
        params.append(body.risk_style)
    if body.coin_prefs is not None:
        updates.append("coin_prefs = ?")
        params.append(json.dumps(body.coin_prefs))
    if body.palette is not None:
        updates.append("palette = ?")
        params.append(body.palette)
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user.internal_id)
        await db.execute(
            f"UPDATE user_settings SET {', '.join(updates)} WHERE user_id = ?", tuple(params)
        )
        await db.commit()
    return await get_profile(user, db)
