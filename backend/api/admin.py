"""B7 Admin console API (desktop-first, admin-role gated). Every route depends on
require_admin → 403 for non-admins. Every mutation is written to admin_events with the
admin id + reason (audit trail). No em dashes in any copy; disclaimers/limits live in
system_settings so the business is tunable without a deploy, but the engine's honesty
(85/82 score gate, card-off D1) is never an editable setting.
"""
import csv
import io
import json

import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.core import notifications as notif
from backend.core.auth import require_admin
from backend.core.database import get_db_connection
from backend.core.email import send_broadcast_email
from backend.core.ranks import rank_for
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
# Three live plans (Decision A, mig 029): Advanced retired. scans_per_day_* are
# admin-editable so per-plan daily limits can be retuned without a deploy.
_EDITABLE_SETTINGS = [
    "plan_price_basic", "plan_price_pro",
    "scan_coins_free", "scan_coins_basic", "scan_coins_pro",
    "scans_per_day_free", "scans_per_day_basic", "scans_per_day_pro",
    "chart_layers_free",
    "trial_days", "trial_reminder_day", "journal_history_days_free",
]
_PLAN_PRICE_KEYS = {"basic": "plan_price_basic", "pro": "plan_price_pro"}


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
        "SELECT key, value FROM system_settings WHERE key IN ('plan_price_basic','plan_price_pro')"
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


# ── Users (v1.1: richer columns + server-side filters + CSV export) ──────────
# Correlated-subquery fragments reused by list + CSV export so both compute identically.
# active-days are ADMIN ANALYTICS only (D-A1): distinct calendar days with a scan in the
# rolling window — read-only from scan_events, never user-facing, never grant XP.
_LAST_ACTIVE = "COALESCE(u.last_scan_at, u.last_login_at)"
_XP = "(SELECT COALESCE(SUM(amount),0) FROM xp_events x WHERE x.user_id=u.internal_id)"
_SCANS_TOTAL = "(SELECT COUNT(*) FROM scan_events se WHERE se.user_id=u.internal_id)"
_SCANS_WEEK = ("(SELECT COUNT(*) FROM scan_events se WHERE se.user_id=u.internal_id "
               "AND se.scanned_at >= datetime('now','-7 days'))")
_ACTIVE_7D = ("(SELECT COUNT(DISTINCT date(se.scanned_at)) FROM scan_events se "
              "WHERE se.user_id=u.internal_id AND date(se.scanned_at) >= date('now','-6 days'))")
_ACTIVE_30D = ("(SELECT COUNT(DISTINCT date(se.scanned_at)) FROM scan_events se "
               "WHERE se.user_id=u.internal_id AND date(se.scanned_at) >= date('now','-29 days'))")
_CHURN_FLAG = "EXISTS(SELECT 1 FROM churn_reasons cr WHERE cr.user_id=u.internal_id)"
# Stage 4: real referral count (friends this user has referred). Goes live now (D-S10).
_REFERRALS = "(SELECT COUNT(*) FROM referrals rf WHERE rf.referrer_id=u.internal_id)"


def _user_filters(
    search: str | None, plan: str | None, status: str | None,
    signup_from: str | None, signup_to: str | None,
    active_from: str | None, active_to: str | None, min_scans: int | None,
) -> tuple[list[str], list]:
    """Build the shared WHERE clause (AND semantics) for /users and its CSV export."""
    where = ["1=1"]
    params: list = []
    if search:
        where.append("(u.email LIKE ? OR IFNULL(s.call_sign,'') LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]
    if plan in ("free", "basic", "pro"):
        where.append("u.tier = ?")
        params.append(plan)
    # churned = user submitted an exit survey (distinct from a silently-expired trial).
    if status == "churned":
        where.append(_CHURN_FLAG)
    elif status in ("trial", "active", "expired"):
        where.append("u.subscription_status = ?")
        params.append(status)
    if signup_from:
        where.append("date(u.created_at) >= date(?)")
        params.append(signup_from)
    if signup_to:
        where.append("date(u.created_at) <= date(?)")
        params.append(signup_to)
    if active_from:
        where.append(f"date({_LAST_ACTIVE}) >= date(?)")
        params.append(active_from)
    if active_to:
        where.append(f"date({_LAST_ACTIVE}) <= date(?)")
        params.append(active_to)
    if min_scans is not None:
        where.append(f"{_SCANS_TOTAL} >= ?")
        params.append(min_scans)
    return where, params


def _user_select(where: list[str], limit: int) -> str:
    return f"""
        SELECT u.internal_id, u.email, u.tier, u.subscription_status,
               u.created_at, u.trial_started_at, u.trial_ends_at, u.suspended_at,
               {_LAST_ACTIVE} AS last_active, s.call_sign,
               {_XP} AS xp, {_SCANS_TOTAL} AS scans_total, {_SCANS_WEEK} AS scans_week,
               {_ACTIVE_7D} AS active_days_7d, {_ACTIVE_30D} AS active_days_30d,
               {_CHURN_FLAG} AS churn_flag, {_REFERRALS} AS referrals
          FROM users u LEFT JOIN user_settings s ON s.user_id=u.internal_id
         WHERE {' AND '.join(where)}
         ORDER BY last_active DESC, u.internal_id DESC
         LIMIT {limit}"""


def _shape_user(r: dict) -> dict:
    xp = r["xp"] or 0
    rank = rank_for(xp)
    return {
        "id": r["internal_id"], "email": r["email"], "call_sign": r["call_sign"],
        "tier": r["tier"], "subscription_status": r["subscription_status"],
        "signup_at": r["created_at"], "last_active": r["last_active"],
        "trial_started_at": r["trial_started_at"], "trial_ends_at": r["trial_ends_at"],
        "suspended": r["suspended_at"] is not None,
        "xp": xp, "rank_level": rank["level"], "rank_name": rank["name"],
        "scans_total": r["scans_total"], "scans_week": r["scans_week"],
        "active_days_7d": r["active_days_7d"], "active_days_30d": r["active_days_30d"],
        "referrals": r["referrals"] or 0,  # live referral count (Stage 4, D-S10)
        "churn_survey": bool(r["churn_flag"]),
    }


@router.get("/users")
async def list_users(
    search: str | None = Query(None),
    plan: str | None = Query(None),
    status: str | None = Query(None),          # trial | active | expired | churned
    signup_from: str | None = Query(None),      # YYYY-MM-DD
    signup_to: str | None = Query(None),
    active_from: str | None = Query(None),
    active_to: str | None = Query(None),
    min_scans: int | None = Query(None, ge=0),
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    where, params = _user_filters(
        search, plan, status, signup_from, signup_to, active_from, active_to, min_scans
    )
    rows = await db.execute_fetchall(_user_select(where, 200), tuple(params))
    return {"users": [_shape_user(dict(r)) for r in rows], "count": len(rows)}


_CSV_COLUMNS = [
    "id", "email", "call_sign", "tier", "subscription_status", "signup_at",
    "last_active", "xp", "rank_level", "rank_name", "scans_total", "scans_week",
    "active_days_7d", "active_days_30d", "referrals", "churn_survey", "suspended",
]


@router.get("/users/export.csv")
async def export_users_csv(
    search: str | None = Query(None),
    plan: str | None = Query(None),
    status: str | None = Query(None),
    signup_from: str | None = Query(None),
    signup_to: str | None = Query(None),
    active_from: str | None = Query(None),
    active_to: str | None = Query(None),
    min_scans: int | None = Query(None, ge=0),
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> StreamingResponse:
    """Stream the CURRENT filtered view as CSV (admin-only; row-capped, no unbounded load)."""
    where, params = _user_filters(
        search, plan, status, signup_from, signup_to, active_from, active_to, min_scans
    )
    rows = await db.execute_fetchall(_user_select(where, 5000), tuple(params))
    shaped = [_shape_user(dict(r)) for r in rows]

    def generate():
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        yield buf.getvalue(); buf.seek(0); buf.truncate(0)
        for u in shaped:
            writer.writerow(u)
            yield buf.getvalue(); buf.seek(0); buf.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="finaroda_users.csv"'},
    )


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
        if body.value not in ("free", "basic", "pro"):
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
                  t.app_version, t.breadcrumbs, u.email, u.tier, u.subscription_status, s.call_sign
             FROM support_tickets t
             JOIN users u ON u.internal_id=t.user_id
             LEFT JOIN user_settings s ON s.user_id=t.user_id
            WHERE t.id=?""",
        (ticket_id,),
    )
    if not rows:
        raise HTTPException(404, "ticket not found")
    ticket = dict(rows[0])
    # Client-side breadcrumb trail (Stage 7), already sanitized at write time.
    try:
        ticket["breadcrumbs"] = json.loads(ticket["breadcrumbs"]) if ticket.get("breadcrumbs") else []
    except (TypeError, ValueError):
        ticket["breadcrumbs"] = []
    replies = await db.execute_fetchall(
        "SELECT id, author_id, is_admin, body, created_at FROM ticket_replies WHERE ticket_id=? ORDER BY created_at",
        (ticket_id,),
    )
    # Diagnostic context (Nadav 2026-07-13): the reporter's last 20 logged actions,
    # unioned from the existing xp / scan / funnel logs — so we can debug blind.
    recent = await db.execute_fetchall(
        """SELECT ts, kind, detail FROM (
               SELECT ts            AS ts, 'xp'     AS kind, source || ' +' || amount AS detail
                 FROM xp_events WHERE user_id = ?
               UNION ALL
               SELECT scanned_at    AS ts, 'scan'   AS kind,
                      coins_scanned || ' scanned / ' || coins_passed || ' passed' AS detail
                 FROM scan_events WHERE user_id = ?
               UNION ALL
               SELECT ts            AS ts, 'funnel' AS kind, stage AS detail
                 FROM onboarding_funnel_events WHERE user_id = ?
           ) ORDER BY ts DESC LIMIT 20""",
        (ticket["user_id"], ticket["user_id"], ticket["user_id"]),
    )
    return {
        "ticket": ticket,
        "replies": [dict(r) for r in replies],
        "recent_events": [dict(r) for r in recent],
    }


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


# ── Churn / exit survey (Stage 7) ────────────────────────────────────────────
@router.get("/churn")
async def list_churn(
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Recent exit-survey responses (detail behind the /overview churn aggregate)."""
    rows = await db.execute_fetchall(
        """SELECT c.id, c.reason_category, c.reason_free_text, c.improvement_text,
                  c.days_as_customer, c.subscription_plan, c.would_return, c.created_at,
                  u.email, s.call_sign
             FROM churn_reasons c
             JOIN users u ON u.internal_id=c.user_id
             LEFT JOIN user_settings s ON s.user_id=c.user_id
            ORDER BY c.created_at DESC LIMIT 200"""
    )
    return {"responses": [dict(r) for r in rows], "count": len(rows)}


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
def _audience_where(audience: str, target_tier) -> tuple[str, tuple]:
    """SQL predicate (over `users u`) selecting a broadcast audience. active=1 always."""
    if audience == "plan":
        return "u.active=1 AND u.tier=?", (target_tier,)
    if audience == "trial_ending":
        return (
            "u.active=1 AND u.subscription_status='trial' AND "
            "datetime(u.trial_ends_at) BETWEEN datetime('now') AND datetime('now','+3 days')",
            (),
        )
    return "u.active=1", ()


async def _broadcast_recipients(db, audience: str, target_tier, email_only: bool) -> list[dict]:
    """Resolve recipients. When email_only, exclude broadcast-email opt-outs
    (email_broadcast=0); users without a prefs row default to opted-in (COALESCE 1)."""
    where, params = _audience_where(audience, target_tier)
    optin = "AND COALESCE(np.email_broadcast, 1) = 1" if email_only else ""
    rows = await db.execute_fetchall(
        f"""SELECT u.internal_id, u.email, u.first_name
              FROM users u
              LEFT JOIN notification_prefs np ON np.user_id = u.internal_id
             WHERE {where} {optin}""",
        params,
    )
    return [dict(r) for r in rows]


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
            "AND datetime(trial_ends_at) BETWEEN datetime('now') AND datetime('now','+3 days')"
        ),
    }
    rows = await db.execute_fetchall(
        """SELECT id, title, body, audience, target_tier, channel_in_app, channel_email, created_at
             FROM admin_broadcasts ORDER BY created_at DESC LIMIT 50"""
    )
    return {"broadcasts": [dict(r) for r in rows], "audience_counts": audience_counts}


@router.get("/broadcasts/preview")
async def preview_broadcast(
    audience: str = Query("all"),
    target_tier: str | None = Query(None),
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Confirm-step preview: audience size + how many will actually receive an email
    (opted-in to broadcast email). Drives the admin confirm dialog count (D-N6)."""
    total = len(await _broadcast_recipients(db, audience, target_tier, email_only=False))
    email_optin = len(await _broadcast_recipients(db, audience, target_tier, email_only=True))
    return {"audience": audience, "recipients": total, "email_optin": email_optin}


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

    # In-app channel: a persistent bell row per recipient (complements the banner),
    # gated per-user by inapp_enabled.
    delivered_inapp = 0
    if body.channel_in_app:
        for r in await _broadcast_recipients(db, body.audience, body.target_tier, email_only=False):
            nid = await notif.create_notification(
                db, r["internal_id"], "broadcast", body.title, body.body, None, commit=False,
            )
            if nid is not None:
                delivered_inapp += 1

    # Email channel: send only to broadcast-email opt-ins, each with a signed one-click
    # unsubscribe link (Israeli spam-law compliance, D-N6). Best-effort per recipient.
    delivered_email = 0
    if body.channel_email:
        for r in await _broadcast_recipients(db, body.audience, body.target_tier, email_only=True):
            if await send_broadcast_email(r["email"], r["internal_id"], body.title, body.body):
                delivered_email += 1

    await db.execute(
        """INSERT OR IGNORE INTO notifications_log (notif_type, channel, ref, status, detail)
           VALUES ('broadcast', ?, ?, 'sent', ?)""",
        ("email_in_app" if body.channel_email and body.channel_in_app else
         ("email" if body.channel_email else "in_app"),
         f"broadcast:{bid}",
         f"{body.title} (in_app={delivered_inapp}, email={delivered_email})"),
    )
    await _audit(db, admin.internal_id, "broadcast_send", None,
                 {"broadcast_id": bid, "audience": body.audience, "target_tier": body.target_tier,
                  "delivered_inapp": delivered_inapp, "delivered_email": delivered_email})
    await db.commit()
    log.info("broadcast_send", broadcast_id=bid, inapp=delivered_inapp, email=delivered_email)
    return {"ok": True, "id": bid, "delivered_inapp": delivered_inapp, "delivered_email": delivered_email}


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
