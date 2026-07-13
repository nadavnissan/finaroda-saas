"""B7 Admin console API (desktop-first, admin-role gated). Every route depends on
require_admin → 403 for non-admins. Every mutation is written to admin_events with the
admin id + reason (audit trail). No em dashes in any copy; disclaimers/limits live in
system_settings so the business is tunable without a deploy, but the engine's honesty
(85/82 score gate, card-off D1) is never an editable setting.
"""
import json

import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.core.auth import require_admin
from backend.core.database import get_db_connection
from backend.models.admin import (
    BroadcastCreate,
    SettingsUpdateBatch,
    TicketReplyCreate,
    TicketStatusUpdate,
    UserOverride,
)
from backend.models.auth import CurrentUser

router = APIRouter(prefix="/api/admin", tags=["admin"])
log = structlog.get_logger(__name__)

# Editable settings surfaced in the B7e Settings frame (keys in system_settings).
_EDITABLE_SETTINGS = [
    "plan_price_basic", "plan_price_advanced", "plan_price_pro",
    "scan_coins_free", "scan_coins_basic", "scan_coins_advanced", "scan_coins_pro",
    "scans_per_day_free", "chart_layers_free",
    "trial_days", "trial_reminder_day", "journal_history_days_free",
]
_PLAN_PRICE_KEYS = {"basic": "plan_price_basic", "advanced": "plan_price_advanced", "pro": "plan_price_pro"}


async def _audit(db, admin_id: int, event_type: str, target_user_id, details: dict) -> None:
    await db.execute(
        """INSERT INTO admin_events (admin_id, event_type, target_user_id, details_json)
           VALUES (?, ?, ?, ?)""",
        (admin_id, event_type, target_user_id, json.dumps(details)),
    )


# ── Overview ────────────────────────────────────────────────────────────────
@router.get("/overview")
async def overview(
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """First-100 vitals, computed from real data (no sample rows)."""
    async def scalar(sql: str, params: tuple = ()) -> int:
        rows = await db.execute_fetchall(sql, params)
        return rows[0][0] if rows else 0

    users_total = await scalar("SELECT COUNT(*) FROM users")
    users_week = await scalar("SELECT COUNT(*) FROM users WHERE created_at >= date('now','-7 days')")
    trials_active = await scalar("SELECT COUNT(*) FROM users WHERE subscription_status='trial'")
    trials_expiring = await scalar(
        "SELECT COUNT(*) FROM users WHERE subscription_status='trial' "
        "AND trial_ends_at BETWEEN datetime('now') AND datetime('now','+3 days')"
    )
    trials_expired = await scalar("SELECT COUNT(*) FROM users WHERE subscription_status='expired'")

    # MRR: sum of active subscriptions' plan prices (agorot in settings → ₪).
    price_rows = await db.execute_fetchall(
        "SELECT key, value FROM system_settings WHERE key IN ('plan_price_basic','plan_price_advanced','plan_price_pro')"
    )
    prices = {r[0]: int(r[1]) for r in price_rows} if price_rows else {}
    mrr_agorot = 0
    tier_counts = {}
    for tier, key in _PLAN_PRICE_KEYS.items():
        n = await scalar("SELECT COUNT(*) FROM users WHERE subscription_status='active' AND tier=?", (tier,))
        tier_counts[tier] = n
        mrr_agorot += n * prices.get(key, 0)

    scans_today = await scalar("SELECT COUNT(*) FROM scan_events WHERE scanned_at >= date('now')")
    scans_7d = await scalar("SELECT COUNT(*) FROM scan_events WHERE scanned_at >= date('now','-7 days')")

    # Scans/day, last 14 days series.
    series_rows = await db.execute_fetchall(
        """SELECT date(scanned_at) AS d, COUNT(*) AS n FROM scan_events
            WHERE scanned_at >= date('now','-14 days') GROUP BY date(scanned_at) ORDER BY d"""
    )
    scans_series = [{"date": r[0], "count": r[1]} for r in series_rows]

    # Churn: exit-survey reasons (placeholder counts until data accrues).
    churn_rows = await db.execute_fetchall(
        """SELECT reason_category AS c, COUNT(*) AS n FROM churn_reasons
            GROUP BY reason_category ORDER BY n DESC"""
    )
    churn = [{"reason": r[0], "count": r[1]} for r in churn_rows]

    return {
        "sample": False,
        "users": {"total": users_total, "new_this_week": users_week},
        "trials": {"active": trials_active, "expiring_3d": trials_expiring, "expired": trials_expired},
        "mrr_ils": round(mrr_agorot / 100, 2),
        "mrr_breakdown": tier_counts,
        "scans": {"today": scans_today, "avg_7d": round(scans_7d / 7, 1)},
        "scans_series": scans_series,
        "churn": churn,
    }


# ── Users ───────────────────────────────────────────────────────────────────
@router.get("/users")
async def list_users(
    search: str | None = Query(None),
    plan: str | None = Query(None),
    trial: str | None = Query(None),
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    where = ["1=1"]
    params: list = []
    if search:
        where.append("(u.email LIKE ? OR IFNULL(s.call_sign,'') LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]
    if plan in ("free", "basic", "advanced", "pro"):
        where.append("u.tier = ?")
        params.append(plan)
    if trial == "active":
        where.append("u.subscription_status='trial'")
    elif trial == "expired":
        where.append("u.subscription_status='expired'")

    rows = await db.execute_fetchall(
        f"""SELECT u.internal_id, u.email, u.tier, u.subscription_status,
                   u.trial_started_at, u.trial_ends_at, u.last_scan_at, u.suspended_at,
                   s.call_sign,
                   (SELECT COALESCE(SUM(amount),0) FROM xp_events x WHERE x.user_id=u.internal_id) AS xp
              FROM users u LEFT JOIN user_settings s ON s.user_id=u.internal_id
             WHERE {' AND '.join(where)}
             ORDER BY u.last_scan_at DESC NULLS LAST, u.internal_id DESC
             LIMIT 200""",
        tuple(params),
    )
    users = [
        {
            "id": r["internal_id"], "email": r["email"],
            "call_sign": r["call_sign"], "tier": r["tier"],
            "subscription_status": r["subscription_status"],
            "trial_started_at": r["trial_started_at"], "trial_ends_at": r["trial_ends_at"],
            "last_scan_at": r["last_scan_at"], "suspended": r["suspended_at"] is not None,
            "xp": r["xp"],
        }
        for r in rows
    ]
    return {"users": users, "count": len(users)}


@router.get("/users/{user_id}")
async def user_detail(
    user_id: int,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    rows = await db.execute_fetchall(
        """SELECT u.internal_id, u.email, u.tier, u.subscription_status,
                  u.trial_started_at, u.trial_ends_at, u.last_scan_at, u.suspended_at,
                  s.call_sign,
                  (SELECT COALESCE(SUM(amount),0) FROM xp_events x WHERE x.user_id=u.internal_id) AS xp
             FROM users u LEFT JOIN user_settings s ON s.user_id=u.internal_id
            WHERE u.internal_id=?""",
        (user_id,),
    )
    if not rows:
        raise HTTPException(404, "user not found")
    u = dict(rows[0])
    tickets = await db.execute_fetchall(
        "SELECT id, subject, status, created_at FROM support_tickets WHERE user_id=? ORDER BY created_at DESC",
        (user_id,),
    )
    return {
        "user": {
            "id": u["internal_id"], "email": u["email"], "call_sign": u["call_sign"],
            "tier": u["tier"], "subscription_status": u["subscription_status"],
            "trial_started_at": u["trial_started_at"], "trial_ends_at": u["trial_ends_at"],
            "last_scan_at": u["last_scan_at"], "suspended": u["suspended_at"] is not None,
            "xp": u["xp"],
        },
        "tickets": [dict(t) for t in tickets],
    }


@router.post("/users/{user_id}/override")
async def user_override(
    user_id: int,
    body: UserOverride,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Apply an admin override (plan / trial extension / support XP / suspend). Logged."""
    rows = await db.execute_fetchall("SELECT internal_id FROM users WHERE internal_id=?", (user_id,))
    if not rows:
        raise HTTPException(404, "user not found")

    if body.action == "plan_override":
        if body.value not in ("free", "basic", "advanced", "pro"):
            raise HTTPException(400, "invalid tier")
        await db.execute("UPDATE users SET tier=? WHERE internal_id=?", (body.value, user_id))
    elif body.action == "extend_trial":
        try:
            days = int(body.value or "7")
        except ValueError:
            raise HTTPException(400, "invalid days")
        await db.execute(
            "UPDATE users SET trial_ends_at = datetime(COALESCE(trial_ends_at, datetime('now')), ?), "
            "subscription_status='trial' WHERE internal_id=?",
            (f"+{days} days", user_id),
        )
    elif body.action == "grant_xp":
        try:
            amount = int(body.value or "0")
        except ValueError:
            raise HTTPException(400, "invalid amount")
        # Support grant is a distinct, auditable XP source (idempotency ref = admin event ts).
        ref = f"support:{admin.internal_id}:{body.note[:24]}"
        await db.execute(
            "INSERT OR IGNORE INTO xp_events (user_id, source, ref, amount) VALUES (?, 'admin_grant', ?, ?)",
            (user_id, ref, amount),
        )
    elif body.action == "suspend":
        await db.execute("UPDATE users SET suspended_at=CURRENT_TIMESTAMP, active=0 WHERE internal_id=?", (user_id,))
    elif body.action == "unsuspend":
        await db.execute("UPDATE users SET suspended_at=NULL, active=1 WHERE internal_id=?", (user_id,))

    await _audit(db, admin.internal_id, f"override_{body.action}", user_id,
                 {"value": body.value, "note": body.note})
    await db.commit()
    return {"ok": True}


# ── Tickets ─────────────────────────────────────────────────────────────────
@router.get("/tickets")
async def list_tickets(
    status: str | None = Query(None),
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    where = ["1=1"]
    params: list = []
    if status in ("open", "in_progress", "resolved", "closed"):
        where.append("t.status = ?")
        params.append(status)
    rows = await db.execute_fetchall(
        f"""SELECT t.id, t.subject, t.body, t.category, t.status, t.created_at,
                   u.email, u.tier, u.subscription_status, s.call_sign
              FROM support_tickets t
              JOIN users u ON u.internal_id=t.user_id
              LEFT JOIN user_settings s ON s.user_id=t.user_id
             WHERE {' AND '.join(where)}
             ORDER BY CASE t.status WHEN 'open' THEN 0 WHEN 'in_progress' THEN 1 ELSE 2 END,
                      t.created_at DESC LIMIT 200""",
        tuple(params),
    )
    counts_rows = await db.execute_fetchall(
        "SELECT status, COUNT(*) FROM support_tickets GROUP BY status"
    )
    counts = {r[0]: r[1] for r in counts_rows}
    return {"tickets": [dict(r) for r in rows], "counts": counts}


@router.get("/tickets/{ticket_id}")
async def ticket_detail(
    ticket_id: int,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    rows = await db.execute_fetchall(
        """SELECT t.id, t.subject, t.body, t.category, t.status, t.created_at, t.user_id,
                  u.email, u.tier, u.subscription_status, s.call_sign
             FROM support_tickets t
             JOIN users u ON u.internal_id=t.user_id
             LEFT JOIN user_settings s ON s.user_id=t.user_id
            WHERE t.id=?""",
        (ticket_id,),
    )
    if not rows:
        raise HTTPException(404, "ticket not found")
    replies = await db.execute_fetchall(
        "SELECT id, author_id, is_admin, body, created_at FROM ticket_replies WHERE ticket_id=? ORDER BY created_at",
        (ticket_id,),
    )
    return {"ticket": dict(rows[0]), "replies": [dict(r) for r in replies]}


@router.post("/tickets/{ticket_id}/reply")
async def reply_ticket(
    ticket_id: int,
    body: TicketReplyCreate,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    rows = await db.execute_fetchall("SELECT user_id FROM support_tickets WHERE id=?", (ticket_id,))
    if not rows:
        raise HTTPException(404, "ticket not found")
    # Email send is a logged stub this phase (email_sent=0).
    await db.execute(
        "INSERT INTO ticket_replies (ticket_id, author_id, is_admin, body, email_sent) VALUES (?, ?, 1, ?, 0)",
        (ticket_id, admin.internal_id, body.body),
    )
    if body.status:
        await db.execute(
            "UPDATE support_tickets SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (body.status, ticket_id),
        )
    await _audit(db, admin.internal_id, "ticket_reply", rows[0][0], {"ticket_id": ticket_id, "status": body.status})
    await db.commit()
    log.info("ticket_reply_email_stub", ticket_id=ticket_id)
    return {"ok": True}


@router.patch("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: int,
    body: TicketStatusUpdate,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    cur = await db.execute(
        "UPDATE support_tickets SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (body.status, ticket_id),
    )
    if cur.rowcount == 0:
        raise HTTPException(404, "ticket not found")
    await _audit(db, admin.internal_id, "ticket_status", None, {"ticket_id": ticket_id, "status": body.status})
    await db.commit()
    return {"ok": True}


# ── Settings ────────────────────────────────────────────────────────────────
@router.get("/settings")
async def get_settings(
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    rows = await db.execute_fetchall(
        f"SELECT key, value, value_type, description FROM system_settings WHERE key IN "
        f"({','.join('?' for _ in _EDITABLE_SETTINGS)})",
        tuple(_EDITABLE_SETTINGS),
    )
    return {
        "settings": [dict(r) for r in rows],
        # Rendered as LOCKED, never inputs (RED LINE / D1).
        "locked": [
            {"key": "score_gate", "value": "85+ PASS / 82-84 WATCH", "reason": "RED LINE"},
            {"key": "card_required", "value": "OFF", "reason": "D1 no-card trial"},
        ],
    }


@router.put("/settings")
async def update_settings_batch(
    body: SettingsUpdateBatch,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    changed = []
    for upd in body.updates:
        if upd.key not in _EDITABLE_SETTINGS:
            raise HTTPException(400, f"setting not editable: {upd.key}")
        await db.execute(
            "UPDATE system_settings SET value=?, updated_at=CURRENT_TIMESTAMP WHERE key=?",
            (upd.value, upd.key),
        )
        changed.append({"key": upd.key, "value": upd.value})
    await _audit(db, admin.internal_id, "settings_update", None, {"changes": changed, "note": body.note})
    await db.commit()
    return {"ok": True, "changed": changed}


# ── Broadcast ───────────────────────────────────────────────────────────────
@router.get("/broadcasts")
async def list_broadcasts(
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    async def scalar(sql: str) -> int:
        r = await db.execute_fetchall(sql)
        return r[0][0] if r else 0

    audience_counts = {
        "all": await scalar("SELECT COUNT(*) FROM users WHERE active=1"),
        "trial_ending": await scalar(
            "SELECT COUNT(*) FROM users WHERE subscription_status='trial' "
            "AND trial_ends_at BETWEEN datetime('now') AND datetime('now','+3 days')"
        ),
    }
    rows = await db.execute_fetchall(
        """SELECT id, title, body, audience, target_tier, channel_in_app, channel_email, created_at
             FROM admin_broadcasts ORDER BY created_at DESC LIMIT 50"""
    )
    return {"broadcasts": [dict(r) for r in rows], "audience_counts": audience_counts}


@router.post("/broadcasts")
async def create_broadcast(
    body: BroadcastCreate,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    if body.audience == "plan" and body.target_tier is None:
        raise HTTPException(400, "target_tier required for plan audience")
    cur = await db.execute(
        """INSERT INTO admin_broadcasts
           (title, body, audience, target_tier, channel_in_app, channel_email, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (body.title, body.body, body.audience,
         body.target_tier if body.audience == "plan" else None,
         1 if body.channel_in_app else 0, 1 if body.channel_email else 0, admin.internal_id),
    )
    bid = cur.lastrowid
    # Log the broadcast as a notification send (email fan-out is a logged stub).
    await db.execute(
        """INSERT OR IGNORE INTO notifications_log (notif_type, channel, ref, status, detail)
           VALUES ('broadcast', ?, ?, 'sent', ?)""",
        ("email_in_app" if body.channel_email and body.channel_in_app else
         ("email" if body.channel_email else "in_app"),
         f"broadcast:{bid}", body.title),
    )
    await _audit(db, admin.internal_id, "broadcast_send", None,
                 {"broadcast_id": bid, "audience": body.audience, "target_tier": body.target_tier})
    await db.commit()
    if body.channel_email:
        log.info("broadcast_email_stub", broadcast_id=bid)
    return {"ok": True, "id": bid}


# ── In-app broadcast banner (for all authed clients) ─────────────────────────
@router.get("/notifications")
async def notifications_log(
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    rows = await db.execute_fetchall(
        """SELECT n.id, n.notif_type, n.channel, n.status, n.detail, n.created_at, u.email
             FROM notifications_log n LEFT JOIN users u ON u.internal_id=n.user_id
            ORDER BY n.created_at DESC LIMIT 200"""
    )
    return {"notifications": [dict(r) for r in rows]}
