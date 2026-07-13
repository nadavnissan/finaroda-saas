"""B6 Academy shell API (F6).

The 12 modules map 1:1 to the `academy` ids in concept_tooltips_content.json. This
phase seeds each module from its terms' plain-language `what` content (rendered by the
frontend from the same bundled JSON) — no invented lessons. Completion XP (+100, once
per lesson, XP_ECONOMY §1) is awarded ONLY for modules with real content (>= 3 terms);
stub modules (volume/positioning/regime-transitions) award nothing.

Plan gating (F7): 'basic' modules are open to all plans; 'full' modules need Advanced+
or an active Pro trial. Two modules are rank-unlocked BONUS content (Spike Autopsies at
1,000 XP, Regime Transitions at 3,000 XP) — orthogonal to plan gates (XP_ECONOMY §3).
"""
import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException

from backend.core.auth import get_current_user
from backend.core.database import get_db_connection
from backend.models.academy import AcademyModule, AcademyResponse, LessonResult
from backend.models.auth import CurrentUser

router = APIRouter(prefix="/api/academy", tags=["academy"])
log = structlog.get_logger(__name__)

ACADEMY_LESSON_SOURCE = "academy_lesson"
ACADEMY_LESSON_XP = 100
LESSON_MIN_TERMS = 3  # a module needs >= this many seed terms to be a real lesson

# id -> (title[no em dash], minutes, term_count, tier, rank_unlock)
# term_count mirrors concept_tooltips_content.json's grouping by `academy`.
_MODULES: list[dict] = [
    {"id": "regime_ema200", "title": "The 200-day average: reading regime", "minutes": 10, "term_count": 3, "tier": "basic", "rank_unlock": None},
    {"id": "ema7_timing", "title": "EMA7 timing: the verified slope", "minutes": 12, "term_count": 4, "tier": "basic", "rank_unlock": None},
    {"id": "closed_candle_scoring", "title": "Closed-candle scoring: why we wait for the close", "minutes": 8, "term_count": 3, "tier": "basic", "rank_unlock": None},
    {"id": "methodology_overview", "title": "The Trading Blueprint: PASS, WATCH, and the score", "minutes": 14, "term_count": 8, "tier": "basic", "rank_unlock": None},
    {"id": "smart_skip", "title": "Smart-skip: the discipline curriculum", "minutes": 18, "term_count": 4, "tier": "full", "rank_unlock": None},
    {"id": "momentum_basics", "title": "Momentum basics: RSI and exhaustion", "minutes": 11, "term_count": 3, "tier": "full", "rank_unlock": None},
    {"id": "risk_geometry", "title": "R and risk geometry: one number to rule sizing", "minutes": 15, "term_count": 9, "tier": "full", "rank_unlock": None},
    {"id": "structure_levels", "title": "Structure and levels: support, resistance, gaps", "minutes": 13, "term_count": 4, "tier": "full", "rank_unlock": None},
    {"id": "volume_basics", "title": "Volume: confirmation, not prediction", "minutes": 6, "term_count": 1, "tier": "basic", "rank_unlock": None},
    {"id": "positioning_basics", "title": "Positioning: funding and isolation", "minutes": 7, "term_count": 2, "tier": "full", "rank_unlock": None},
    {"id": "spike_anatomy", "title": "Anatomy of a spike: why most fade", "minutes": 12, "term_count": 3, "tier": "full", "rank_unlock": 1000},
    {"id": "regime_transitions", "title": "Regime transitions: reading the turn", "minutes": 9, "term_count": 2, "tier": "full", "rank_unlock": 3000},
]
_MODULE_IDS = {m["id"] for m in _MODULES}


def _has_lesson(m: dict) -> bool:
    return m["term_count"] >= LESSON_MIN_TERMS


def _is_pro_access(user: CurrentUser) -> bool:
    """Advanced/Pro plans, or an active Pro trial (trial = full library, B6b)."""
    return user.tier in ("advanced", "pro") or user.subscription_status == "trial"


def _is_unlocked(m: dict, user: CurrentUser, xp_total: int) -> bool:
    if m["rank_unlock"] is not None:
        return xp_total >= m["rank_unlock"]        # bonus content, plan-agnostic
    if m["tier"] == "basic":
        return True
    return _is_pro_access(user)                     # 'full' → Advanced+ or Pro trial


@router.get("", response_model=AcademyResponse)
async def list_modules(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> AcademyResponse:
    xp_rows = await db.execute_fetchall(
        "SELECT COALESCE(SUM(amount), 0) FROM xp_events WHERE user_id = ?", (user.internal_id,)
    )
    xp_total = xp_rows[0][0] if xp_rows else 0

    done_rows = await db.execute_fetchall(
        "SELECT ref FROM xp_events WHERE user_id = ? AND source = ?",
        (user.internal_id, ACADEMY_LESSON_SOURCE),
    )
    completed = {r[0] for r in done_rows}

    modules = [
        AcademyModule(
            id=m["id"], title=m["title"], minutes=m["minutes"], term_count=m["term_count"],
            has_lesson=_has_lesson(m), tier=m["tier"], rank_unlock=m["rank_unlock"],
            unlocked=_is_unlocked(m, user, xp_total), completed=m["id"] in completed,
        )
        for m in _MODULES
    ]
    return AcademyResponse(modules=modules, xp_total=xp_total)


@router.post("/{module_id}/complete", response_model=LessonResult)
async def complete_lesson(
    module_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> LessonResult:
    """Award +100 XP once per real lesson. Stub / locked modules award nothing."""
    m = next((x for x in _MODULES if x["id"] == module_id), None)
    if m is None:
        raise HTTPException(404, "unknown module")

    xp_rows = await db.execute_fetchall(
        "SELECT COALESCE(SUM(amount), 0) FROM xp_events WHERE user_id = ?", (user.internal_id,)
    )
    xp_total = xp_rows[0][0] if xp_rows else 0

    if not _is_unlocked(m, user, xp_total):
        raise HTTPException(403, "module locked for this plan/rank")
    if not _has_lesson(m):
        # Honest: a stub with no real lesson content grants no XP.
        return LessonResult(xp_awarded=0, completed=False)

    xp_cur = await db.execute(
        """INSERT OR IGNORE INTO xp_events (user_id, source, ref, amount)
           VALUES (?, ?, ?, ?)""",
        (user.internal_id, ACADEMY_LESSON_SOURCE, module_id, ACADEMY_LESSON_XP),
    )
    awarded = xp_cur.rowcount == 1
    await db.commit()
    return LessonResult(xp_awarded=ACADEMY_LESSON_XP if awarded else 0, completed=True)
