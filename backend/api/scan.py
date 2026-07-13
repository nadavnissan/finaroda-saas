"""
Scan persistence (SPEC §5). Every scan → scan_events + one score_log row per coin
scanned (score NULL until engine pass 2). Blueprint shown → decision_snapshots.

Auth-required: rows are keyed on the current user. The client treats persistence as
best-effort (a signed-out scan still works; it just isn't logged).
"""
import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException

from backend.core.auth import get_current_user
from backend.core.database import get_db_connection
from backend.core.entitlements import resolve_entitlements
from backend.core import journal
from backend.models.auth import CurrentUser
from backend.models.scan import (
    EntitlementsResponse,
    ScanEventCreate,
    ScanEventResponse,
    ScanHistoryItem,
    ScanHistoryResponse,
    SnapshotCreate,
    SnapshotResponse,
    StoredScanResponse,
    StoredScanRow,
)

router = APIRouter(prefix="/api/scan", tags=["scan"])
log = structlog.get_logger(__name__)

# First-scan-of-the-day XP (XP_ECONOMY.md §1, D3): +50, once per calendar day.
# Server owns the amount (RED LINE); the client only learns whether it was awarded.
DAILY_FIRST_SCAN_SOURCE = "daily_first_scan"
DAILY_FIRST_SCAN_XP = 50


@router.get("/entitlements", response_model=EntitlementsResponse)
async def get_entitlements(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> EntitlementsResponse:
    """The binding gating config for this user's plan (coins/scan, chart layers)."""
    ent = await resolve_entitlements(db, user.tier)
    return EntitlementsResponse(**ent)


@router.post("/events", response_model=ScanEventResponse)
async def record_scan(
    body: ScanEventCreate,
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> ScanEventResponse:
    """Record one scan_event + one score_log row per coin scanned.

    Server-authoritative gating (B1): the scan runs client-side, but an over-limit
    scan is rejected here so a plan's coin count cannot be exceeded in the logged
    journal (the product's value). Also credits the +50 first-scan-of-day XP (D3).
    """
    ent = await resolve_entitlements(db, user.tier)
    limit = ent["coins_per_scan"]
    # Distinct coins in the displayed (momentum) rows — the real scanned breadth.
    distinct_coins = {c.coin for c in body.coins if c.profile == "momentum"}
    over = max(body.coins_scanned, len(distinct_coins))
    if over > limit:
        raise HTTPException(
            403,
            {
                "code": "PLAN_COIN_LIMIT",
                "message": f"Your plan scans up to {limit} coins; received {over}.",
                "coins_per_scan": limit,
                "tier": ent["tier"],
            },
        )

    # Daily scan cap (Bug 3 / F7): Free = 1 scan/day, paid = unlimited (scans_per_day=0).
    # Server-authoritative like the coin gate — the logged journal cannot exceed the
    # plan's daily breadth. Admin-tunable per plan via system_settings (scans_per_day_*).
    daily_limit = ent["scans_per_day"]
    if daily_limit > 0:
        used_rows = await db.execute_fetchall(
            "SELECT COUNT(*) FROM scan_events WHERE user_id = ? AND date(scanned_at) = date('now')",
            (user.internal_id,),
        )
        used_today = used_rows[0][0] if used_rows else 0
        if used_today >= daily_limit:
            raise HTTPException(
                429,
                {
                    "code": "DAILY_SCAN_LIMIT",
                    "message": (
                        f"Your plan includes {daily_limit} scan"
                        f"{'s' if daily_limit != 1 else ''} per day. "
                        "Your journal resets tomorrow."
                    ),
                    "scans_per_day": daily_limit,
                    "used_today": used_today,
                    "tier": ent["tier"],
                },
            )

    cursor = await db.execute(
        """INSERT INTO scan_events (user_id, coins_scanned, coins_passed, threshold, client_ip_region)
           VALUES (?, ?, ?, ?, ?)""",
        (user.internal_id, body.coins_scanned, body.coins_passed, body.threshold, body.client_ip_region),
    )
    scan_event_id = cursor.lastrowid

    score_logs = []
    momentum_rows: list[dict] = []
    for c in body.coins:
        cur = await db.execute(
            """INSERT INTO score_log
               (scan_event_id, user_id, coin, direction, profile, score, passed_threshold,
                ema7_slope_pct, volume_ratio, price, entry, sl, tp, trailing_pct)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (scan_event_id, user.internal_id, c.coin, c.direction, c.profile, c.score,
             c.passed_threshold, c.ema7_slope_pct, c.volume_ratio, c.price, c.entry, c.sl, c.tp,
             c.trailing_pct),
        )
        # Return only the DISPLAYED (momentum) rows for snapshot linking.
        if c.profile == "momentum":
            score_logs.append({"coin": c.coin, "id": cur.lastrowid})
            momentum_rows.append({
                "score_log_id": cur.lastrowid, "profile": "momentum", "coin": c.coin,
                "direction": c.direction, "score": c.score,
                "passed_threshold": c.passed_threshold, "entry": c.entry, "sl": c.sl,
                "tp": c.tp, "trailing_pct": c.trailing_pct,
            })

    # B4/F3 journal (reveal-gated): reveal any resolved-but-unrevealed prior scenarios
    # (the scan IS the reveal event, ALIGNMENT B3), then record this scan's PASS setups
    # (or a no_setups_day discipline row). Server-side; outcomes stay withheld.
    scan_date_rows = await db.execute_fetchall("SELECT date('now')")
    scan_date = scan_date_rows[0][0]
    await journal.on_scan(db, user.internal_id, scan_event_id, scan_date, momentum_rows)

    # First-scan-of-the-day XP (D3): idempotent per calendar day via
    # UNIQUE(user_id, source, ref). rowcount == 1 means this was the day's first.
    xp_cur = await db.execute(
        """INSERT OR IGNORE INTO xp_events (user_id, source, ref, amount)
           VALUES (?, ?, date('now'), ?)""",
        (user.internal_id, DAILY_FIRST_SCAN_SOURCE, DAILY_FIRST_SCAN_XP),
    )
    first_scan_of_day = xp_cur.rowcount == 1
    await db.commit()
    return ScanEventResponse(
        scan_event_id=scan_event_id,
        score_logs=score_logs,
        first_scan_of_day=first_scan_of_day,
        xp_awarded=DAILY_FIRST_SCAN_XP if first_scan_of_day else 0,
    )


@router.get("/history", response_model=ScanHistoryResponse)
async def scan_history(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> ScanHistoryResponse:
    """Read-only list of the user's recent scans (Decision B): time, coins, passes.
    History is display-only — it never re-runs a scan or reveals a withheld outcome."""
    rows = await db.execute_fetchall(
        """SELECT id, scanned_at, coins_scanned, coins_passed
             FROM scan_events WHERE user_id = ?
            ORDER BY scanned_at DESC LIMIT 50""",
        (user.internal_id,),
    )
    return ScanHistoryResponse(
        scans=[
            ScanHistoryItem(
                scan_event_id=r[0], scanned_at=r[1],
                coins_scanned=r[2] or 0, coins_passed=r[3] or 0,
            )
            for r in rows
        ]
    )


@router.get("/history/{scan_event_id}", response_model=StoredScanResponse)
async def stored_scan(
    scan_event_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> StoredScanResponse:
    """The stored result of one past scan (Decision B) — the displayed (momentum) rows
    exactly as logged. Owner-scoped; no outcome data (that stays reveal-gated in F3)."""
    head = await db.execute_fetchall(
        """SELECT scanned_at, coins_scanned, coins_passed
             FROM scan_events WHERE id = ? AND user_id = ?""",
        (scan_event_id, user.internal_id),
    )
    if not head:
        raise HTTPException(404, "scan not found for this user")
    rows = await db.execute_fetchall(
        """SELECT coin, direction, score, passed_threshold, price, entry, sl, tp, trailing_pct
             FROM score_log
            WHERE scan_event_id = ? AND user_id = ? AND profile = 'momentum'
            ORDER BY passed_threshold DESC, score DESC""",
        (scan_event_id, user.internal_id),
    )
    return StoredScanResponse(
        scan_event_id=scan_event_id,
        scanned_at=head[0][0],
        coins_scanned=head[0][1] or 0,
        coins_passed=head[0][2] or 0,
        rows=[
            StoredScanRow(
                coin=r[0], direction=r[1], score=r[2], passed_threshold=r[3],
                price=r[4], entry=r[5], sl=r[6], tp=r[7], trailing_pct=r[8],
            )
            for r in rows
        ],
    )


@router.post("/snapshot", response_model=SnapshotResponse)
async def record_snapshot(
    body: SnapshotCreate,
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> SnapshotResponse:
    """Record the Trading Blueprint exactly as shown to the user (evidentiary)."""
    rows = await db.execute_fetchall(
        "SELECT user_id FROM score_log WHERE id = ?", (body.score_log_id,)
    )
    if not rows or rows[0][0] != user.internal_id:
        raise HTTPException(404, "score_log row not found for this user")

    cursor = await db.execute(
        "INSERT INTO decision_snapshots (score_log_id, user_id, card_json) VALUES (?, ?, ?)",
        (body.score_log_id, user.internal_id, body.card_json),
    )
    await db.commit()
    return SnapshotResponse(id=cursor.lastrowid)
