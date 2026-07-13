"""B4 "What Would Have Happened" dashboard API (F3).

Reveal-gating is enforced HERE at serialization: a scenario whose outcome has not
been revealed to this user is returned WITHOUT any outcome field (no status, no
r_result, no resolved_at). Blurred client rows therefore carry no outcome data at all
(regression-tested). The reveal itself happens on the user's next scan (see
core/journal.on_scan); this endpoint only reads.

R only, never money (F3 AC4). Symmetric framing (wins and capital-saves co-equal) is
a presentation concern; the API just reports honest counts.
"""
import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException

from backend.core import journal
from backend.core.auth import get_current_user
from backend.core.database import get_db_connection
from backend.core.entitlements import get_setting_int
from backend.models.auth import CurrentUser
from backend.models.journal import (
    JournalBadge,
    JournalResponse,
    JournalStats,
    ScenarioView,
    ViewResult,
)

router = APIRouter(prefix="/api/journal", tags=["journal"])
log = structlog.get_logger(__name__)

DISCIPLINE_WINDOW_DAYS = 12  # "skipped 9 of last 12 days"


@router.get("", response_model=JournalResponse)
async def get_journal(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> JournalResponse:
    """The dashboard payload. Withholds every unrevealed outcome by construction."""
    # Free tier sees only the last N days of journal history (F7 · admin-editable).
    where_window = ""
    params: list = [user.internal_id]
    if user.tier == "free":
        days = await get_setting_int(db, "journal_history_days_free", 7)
        where_window = "AND scan_date >= date('now', ?)"
        params.append(f"-{days} days")

    rows = await db.execute_fetchall(
        f"""SELECT id, scenario_type, coin, direction, score, scan_date,
                   status, r_result, resolved_at, revealed_at, viewed_at
              FROM journal_scenarios
             WHERE user_id = ? {where_window}
             ORDER BY scan_date DESC, id DESC""",
        tuple(params),
    )

    scenarios: list[ScenarioView] = []
    cumulative_r = 0.0
    capital_saves = 0
    awaiting = 0
    for r in rows:
        d = dict(r)
        stype = d["scenario_type"]
        if stype == "no_setups_day":
            # Ambient discipline record: always visible, no outcome to gate.
            scenarios.append(ScenarioView(
                id=d["id"], type="no_setups_day", scan_date=d["scan_date"],
                revealed=True,
            ))
            continue

        revealed = d["revealed_at"] is not None
        base = ScenarioView(
            id=d["id"], type="pass", coin=d["coin"], direction=d["direction"],
            score=d["score"], scan_date=d["scan_date"], revealed=revealed,
        )
        if revealed:
            # Outcome is now disclosed for this user.
            base.status = d["status"]
            base.r_result = d["r_result"]
            base.resolved_at = d["resolved_at"]
            base.viewed = d["viewed_at"] is not None
            if d["status"] == "save":
                capital_saves += 1
            elif d["r_result"] is not None:
                cumulative_r += d["r_result"]
        else:
            # WITHHELD. No status / r_result / resolved_at leaves the server.
            if d["status"] != "open" and d["resolved_at"] is not None:
                awaiting += 1
        scenarios.append(base)

    # Discipline meter over the last N days (real data only, no fabricated ratio).
    disc = await db.execute_fetchall(
        """SELECT
              SUM(CASE WHEN scenario_type='no_setups_day' THEN 1 ELSE 0 END) AS skips,
              COUNT(DISTINCT scan_date) AS tracked
             FROM journal_scenarios
            WHERE user_id = ? AND scan_date >= date('now', ?)""",
        (user.internal_id, f"-{DISCIPLINE_WINDOW_DAYS} days"),
    )
    skip_days = (disc[0]["skips"] or 0) if disc else 0
    tracked_days = (disc[0]["tracked"] or 0) if disc else 0
    discipline_pct = round(100 * skip_days / tracked_days) if tracked_days else 0

    stats = JournalStats(
        cumulative_r_revealed=round(cumulative_r, 2),
        capital_saves=capital_saves,
        awaiting_reveal=awaiting,
        skip_days=skip_days,
        tracked_days=tracked_days,
        discipline_pct=discipline_pct,
    )
    return JournalResponse(stats=stats, scenarios=scenarios)


@router.get("/badge", response_model=JournalBadge)
async def get_badge(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> JournalBadge:
    """Nav badge = count of unrevealed resolved outcomes. Count only, never content."""
    return JournalBadge(unrevealed=await journal.unrevealed_count(db, user.internal_id))


@router.post("/scenarios/{scenario_id}/view", response_model=ViewResult)
async def view_scenario(
    scenario_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> ViewResult:
    """Mark a REVEALED outcome as viewed → +25 XP once per scenario (XP_ECONOMY §1)."""
    rows = await db.execute_fetchall(
        """SELECT user_id, scenario_type, revealed_at FROM journal_scenarios
            WHERE id = ?""",
        (scenario_id,),
    )
    if not rows or rows[0]["user_id"] != user.internal_id:
        raise HTTPException(404, "scenario not found for this user")
    row = rows[0]
    if row["scenario_type"] != "pass" or row["revealed_at"] is None:
        # Cannot earn XP for viewing something that has no revealed outcome.
        raise HTTPException(409, "scenario has no revealed outcome to view")

    await db.execute(
        "UPDATE journal_scenarios SET viewed_at = CURRENT_TIMESTAMP WHERE id = ? AND viewed_at IS NULL",
        (scenario_id,),
    )
    # Idempotent per scenario via UNIQUE(user_id, source, ref) — server owns the amount.
    xp_cur = await db.execute(
        """INSERT OR IGNORE INTO xp_events (user_id, source, ref, amount)
           VALUES (?, ?, ?, ?)""",
        (user.internal_id, journal.JOURNAL_VIEW_SOURCE, str(scenario_id), journal.JOURNAL_VIEW_XP),
    )
    awarded = xp_cur.rowcount == 1
    await db.commit()
    return ViewResult(xp_awarded=journal.JOURNAL_VIEW_XP if awarded else 0)
