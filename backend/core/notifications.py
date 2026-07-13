"""Stage 5 notification service — bell feed, prefs, and signed unsubscribe tokens.

Two red lines enforced here:
  * in-app rows are gated by `inapp_enabled` (D-N3/AC3): when off, `create_notification`
    is a no-op, so nothing new surfaces in the bell. Emails are a SEPARATE gate.
  * unsubscribe tokens are HMAC-signed via the existing JWT_SECRET (D-N7): per-category,
    no login required, idempotent, tamper-evident.

`notifications` (user-facing bell feed) is distinct from `notifications_log` (mig 028,
the system-send idempotency + admin-audit ledger). This module owns the former only.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite
from jose import JWTError, jwt

from backend.config import JWT_ALGORITHM, JWT_SECRET

# Notification-pref categories that a signed unsubscribe link may flip.
EMAIL_CATEGORIES = ("email_product", "email_broadcast")
_UNSUB_PURPOSE = "email_unsubscribe"
_UNSUB_TTL_DAYS = 365  # links live in old emails; keep them valid for a long window


# ── preferences ──────────────────────────────────────────────────────────────
_PREF_FIELDS = (
    "inapp_enabled",
    "sound_enabled",
    "vibration_enabled",
    "email_product",
    "email_broadcast",
)
_PREF_DEFAULTS = {k: True for k in _PREF_FIELDS}


async def get_prefs(db: aiosqlite.Connection, user_id: int) -> dict:
    """Return this user's prefs as a bool dict, lazily creating defaults on first read."""
    rows = await db.execute_fetchall(
        f"SELECT {', '.join(_PREF_FIELDS)} FROM notification_prefs WHERE user_id = ?",
        (user_id,),
    )
    if rows:
        # Positional mapping works whether or not the connection uses a Row factory.
        vals = rows[0]
        return {k: bool(vals[i]) for i, k in enumerate(_PREF_FIELDS)}
    await db.execute(
        "INSERT OR IGNORE INTO notification_prefs (user_id) VALUES (?)", (user_id,)
    )
    await db.commit()
    return dict(_PREF_DEFAULTS)


async def update_prefs(db: aiosqlite.Connection, user_id: int, patch: dict) -> dict:
    """Persist a partial prefs patch (only known bool fields). Returns the full prefs."""
    await db.execute(
        "INSERT OR IGNORE INTO notification_prefs (user_id) VALUES (?)", (user_id,)
    )
    sets, params = [], []
    for field in _PREF_FIELDS:
        if field in patch and patch[field] is not None:
            sets.append(f"{field} = ?")
            params.append(1 if patch[field] else 0)
    if sets:
        sets.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user_id)
        await db.execute(
            f"UPDATE notification_prefs SET {', '.join(sets)} WHERE user_id = ?",
            tuple(params),
        )
        await db.commit()
    return await get_prefs(db, user_id)


# ── bell feed ────────────────────────────────────────────────────────────────
async def create_notification(
    db: aiosqlite.Connection,
    user_id: int,
    ntype: str,
    title: str,
    body: str,
    link_path: Optional[str] = None,
    *,
    commit: bool = True,
) -> Optional[int]:
    """Insert a bell row IF the user has in-app notifications enabled (AC3).

    Returns the new row id, or None when suppressed by prefs. Callers that batch
    inside a larger transaction pass commit=False.
    """
    prefs = await get_prefs(db, user_id)
    if not prefs["inapp_enabled"]:
        return None
    cur = await db.execute(
        """INSERT INTO notifications (user_id, type, title, body, link_path)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, ntype, title, body, link_path),
    )
    if commit:
        await db.commit()
    return cur.lastrowid


async def list_notifications(
    db: aiosqlite.Connection, user_id: int, limit: int = 30
) -> list[dict]:
    """Newest-first bell feed for this user."""
    rows = await db.execute_fetchall(
        """SELECT id, type, title, body, link_path, created_at, read_at
             FROM notifications WHERE user_id = ?
            ORDER BY created_at DESC, id DESC LIMIT ?""",
        (user_id, limit),
    )
    return [dict(r) for r in rows]


async def unread_count(db: aiosqlite.Connection, user_id: int) -> int:
    """Server-authoritative unread count (survives client refresh, AC1)."""
    rows = await db.execute_fetchall(
        "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read_at IS NULL",
        (user_id,),
    )
    return rows[0][0] if rows else 0


async def mark_read(
    db: aiosqlite.Connection, user_id: int, ids: Optional[list[int]] = None
) -> int:
    """Stamp read_at on the given ids (or all unread when ids is None). Idempotent."""
    if ids is not None and not ids:
        return 0
    if ids is None:
        cur = await db.execute(
            "UPDATE notifications SET read_at = CURRENT_TIMESTAMP "
            "WHERE user_id = ? AND read_at IS NULL",
            (user_id,),
        )
    else:
        placeholders = ",".join("?" for _ in ids)
        cur = await db.execute(
            f"UPDATE notifications SET read_at = CURRENT_TIMESTAMP "
            f"WHERE user_id = ? AND read_at IS NULL AND id IN ({placeholders})",
            (user_id, *ids),
        )
    await db.commit()
    return cur.rowcount


# ── signed unsubscribe tokens (D-N7) ─────────────────────────────────────────
def make_unsubscribe_token(user_id: int, category: str) -> str:
    """HMAC-signed per-category unsubscribe token (reuses JWT_SECRET, no new infra)."""
    if category not in EMAIL_CATEGORIES:
        raise ValueError(f"not an unsubscribable category: {category}")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "cat": category,
        "purpose": _UNSUB_PURPOSE,
        "iat": now,
        "exp": now + timedelta(days=_UNSUB_TTL_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_unsubscribe_token(token: str) -> Optional[tuple[int, str]]:
    """Return (user_id, category) for a valid token, else None (tampered/expired/wrong)."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
    if payload.get("purpose") != _UNSUB_PURPOSE:
        return None
    category = payload.get("cat")
    if category not in EMAIL_CATEGORIES:
        return None
    try:
        return int(payload["sub"]), category
    except (KeyError, ValueError, TypeError):
        return None
