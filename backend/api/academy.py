"""Academy 2.0 user API (F6): flat lesson list (card grid), server-authoritative gated
content, completion XP. Lessons are DB-backed (mig 033). Completion/XP stays in xp_events
(source='academy_lesson', ref=slug), idempotent per lesson (+100 first time only,
XP_ECONOMY §1) — unchanged from B6, so no completion or XP is lost in the rebuild.

Gating (D-AC1): each lesson carries min_plan (free/basic/pro) + min_rank (0/1000/3000/8000);
both must pass (STATUS-based, never XP-as-currency). Locked lessons show metadata + a
plain-language lock reason; their CONTENT is never sent (D-AC7): GET /{slug} returns 403.
"""
import json

import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException

from backend.core.academy_gate import is_unlocked, lock_reason
from backend.core.auth import get_current_user
from backend.core.database import get_db_connection
from backend.models.academy import (
    AcademyLesson,
    AcademyResponse,
    LessonContent,
    LessonResult,
)
from backend.models.auth import CurrentUser

router = APIRouter(prefix="/api/academy", tags=["academy"])
log = structlog.get_logger(__name__)

ACADEMY_LESSON_SOURCE = "academy_lesson"
ACADEMY_LESSON_XP = 100


async def _xp_total(db: aiosqlite.Connection, uid: int) -> int:
    rows = await db.execute_fetchall(
        "SELECT COALESCE(SUM(amount), 0) FROM xp_events WHERE user_id = ?", (uid,)
    )
    return rows[0][0] if rows else 0


async def _completed_slugs(db: aiosqlite.Connection, uid: int) -> set:
    rows = await db.execute_fetchall(
        "SELECT ref FROM xp_events WHERE user_id = ? AND source = ?",
        (uid, ACADEMY_LESSON_SOURCE),
    )
    return {r[0] for r in rows}


@router.get("", response_model=AcademyResponse)
async def list_lessons(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> AcademyResponse:
    xp_total = await _xp_total(db, user.internal_id)
    completed = await _completed_slugs(db, user.internal_id)
    rows = await db.execute_fetchall(
        """SELECT slug, title, description, content_type, duration_minutes, tags,
                  min_plan, min_rank, sort_index, awards_xp
           FROM academy_lessons WHERE archived_at IS NULL
           ORDER BY sort_index, id"""
    )
    lessons = [
        AcademyLesson(
            slug=slug, id=slug, title=title, description=desc, content_type=ctype,
            duration_minutes=dur, minutes=dur, tags=json.loads(tags or "[]"),
            min_plan=min_plan, min_rank=min_rank, sort_index=sort_index,
            awards_xp=bool(awards_xp),
            unlocked=is_unlocked(user, xp_total, min_plan, min_rank),
            completed=slug in completed,
            lock_reason=lock_reason(user, xp_total, min_plan, min_rank),
        )
        for (slug, title, desc, ctype, dur, tags, min_plan, min_rank, sort_index, awards_xp)
        in rows
    ]
    return AcademyResponse(modules=lessons, xp_total=xp_total)


@router.get("/{slug}", response_model=LessonContent)
async def lesson_content(
    slug: str,
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> LessonContent:
    rows = await db.execute_fetchall(
        """SELECT slug, title, description, content_type, duration_minutes, tags, body,
                  video_url, min_plan, min_rank, awards_xp
           FROM academy_lessons WHERE slug = ? AND archived_at IS NULL""",
        (slug,),
    )
    if not rows:
        raise HTTPException(404, "unknown lesson")
    (slug, title, desc, ctype, dur, tags, body, video_url, min_plan, min_rank, awards_xp) = rows[0]
    xp_total = await _xp_total(db, user.internal_id)
    if not is_unlocked(user, xp_total, min_plan, min_rank):
        # D-AC7: content is server-authoritative — never leak a locked lesson's body/video.
        raise HTTPException(
            403,
            {"code": "LESSON_LOCKED",
             "reason": lock_reason(user, xp_total, min_plan, min_rank)},
        )
    completed = slug in await _completed_slugs(db, user.internal_id)
    return LessonContent(
        slug=slug, title=title, description=desc, content_type=ctype, duration_minutes=dur,
        tags=json.loads(tags or "[]"), body=body, video_url=video_url,
        completed=completed, awards_xp=bool(awards_xp),
    )


@router.post("/{slug}/complete", response_model=LessonResult)
async def complete_lesson(
    slug: str,
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> LessonResult:
    """Award +100 XP once per lesson. Locked lessons 403; non-XP (seed stub) lessons 0."""
    rows = await db.execute_fetchall(
        "SELECT min_plan, min_rank, awards_xp FROM academy_lessons WHERE slug = ? AND archived_at IS NULL",
        (slug,),
    )
    if not rows:
        raise HTTPException(404, "unknown lesson")
    min_plan, min_rank, awards_xp = rows[0]
    xp_total = await _xp_total(db, user.internal_id)
    if not is_unlocked(user, xp_total, min_plan, min_rank):
        raise HTTPException(403, "lesson locked for this plan/rank")
    if not awards_xp:
        # Honest: a seed reference lesson with no XP grants nothing (B6 stub parity).
        return LessonResult(xp_awarded=0, completed=False)
    cur = await db.execute(
        """INSERT OR IGNORE INTO xp_events (user_id, source, ref, amount)
           VALUES (?, ?, ?, ?)""",
        (user.internal_id, ACADEMY_LESSON_SOURCE, slug, ACADEMY_LESSON_XP),
    )
    awarded = cur.rowcount == 1
    await db.commit()
    return LessonResult(xp_awarded=ACADEMY_LESSON_XP if awarded else 0, completed=True)
