"""Academy 2.0 admin API (F6 / deliverable D): create / edit / reorder / archive / restore
lessons. Admin-only (require_admin -> 403 for everyone else). Every mutation is audited to
admin_events (same pattern as api/admin.py).

Video is by URL only (D-AC2: YouTube / Vimeo), validated + normalized to an embed URL at
write time; there are no uploads to our infra. Archive-not-delete (D-AC6): archived lessons
disappear from the user library but stay here with a restore action, and XP already granted
is never revoked (completions live in xp_events, untouched by archive).
"""
import json
import re

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from backend.core.academy_gate import VALID_MIN_RANKS, VALID_PLANS, validate_video_url
from backend.core.auth import require_admin
from backend.core.database import get_db_connection
from backend.models.academy import (
    AdminLesson,
    LessonCreate,
    LessonUpdate,
    ReorderRequest,
)
from backend.models.auth import CurrentUser

router = APIRouter(prefix="/api/admin/academy", tags=["admin-academy"])

_SELECT = """SELECT id, slug, title, description, content_type, body, video_url,
                    duration_minutes, tags, min_plan, min_rank, sort_index, awards_xp, archived_at
             FROM academy_lessons"""


async def _audit(db: aiosqlite.Connection, admin_id: int, event_type: str, details: dict) -> None:
    await db.execute(
        """INSERT INTO admin_events (admin_id, event_type, target_user_id, details_json)
           VALUES (?, ?, NULL, ?)""",
        (admin_id, event_type, json.dumps(details)),
    )


def _slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (title or "").lower()).strip("_")
    return s or "lesson"


async def _unique_slug(db: aiosqlite.Connection, base: str) -> str:
    slug, n = base, 1
    while await db.execute_fetchall("SELECT 1 FROM academy_lessons WHERE slug = ?", (slug,)):
        n += 1
        slug = f"{base}_{n}"
    return slug


def _row_to_admin(r) -> AdminLesson:
    (id_, slug, title, desc, ctype, body, video_url, dur, tags, min_plan, min_rank,
     sort_index, awards_xp, archived_at) = r
    return AdminLesson(
        id=id_, slug=slug, title=title, description=desc, content_type=ctype, body=body,
        video_url=video_url, duration_minutes=dur, tags=json.loads(tags or "[]"),
        min_plan=min_plan, min_rank=min_rank, sort_index=sort_index,
        awards_xp=bool(awards_xp), archived=archived_at is not None,
    )


def _validate_gates(min_plan: str, min_rank: int) -> None:
    if min_plan not in VALID_PLANS:
        raise HTTPException(400, {"code": "INVALID_MIN_PLAN", "message": "min_plan must be free/basic/pro."})
    if min_rank not in VALID_MIN_RANKS:
        raise HTTPException(400, {"code": "INVALID_MIN_RANK", "message": "min_rank must be 0/1000/3000/8000."})


def _resolve_video(content_type: str, video_url) -> str | None:
    """A video lesson requires a valid YouTube/Vimeo URL; text lessons store none."""
    if content_type != "video":
        return None
    norm = validate_video_url(video_url or "")
    if not norm:
        raise HTTPException(400, {"code": "INVALID_VIDEO_URL",
                                  "message": "Paste a valid YouTube or Vimeo link."})
    return norm


@router.get("/lessons", response_model=list[AdminLesson])
async def list_all(
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> list[AdminLesson]:
    rows = await db.execute_fetchall(_SELECT + " ORDER BY sort_index, id")
    return [_row_to_admin(r) for r in rows]


@router.post("/lessons", response_model=AdminLesson)
async def create(
    payload: LessonCreate,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> AdminLesson:
    if payload.content_type not in ("text", "video"):
        raise HTTPException(400, {"code": "INVALID_CONTENT_TYPE"})
    _validate_gates(payload.min_plan, payload.min_rank)
    video_url = _resolve_video(payload.content_type, payload.video_url)
    slug = await _unique_slug(db, _slugify(payload.slug or payload.title))
    nxt = await db.execute_fetchall("SELECT COALESCE(MAX(sort_index), -1) + 1 FROM academy_lessons")
    sort_index = nxt[0][0]
    cur = await db.execute(
        """INSERT INTO academy_lessons
           (slug, title, description, content_type, body, video_url, duration_minutes,
            tags, min_plan, min_rank, sort_index, awards_xp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (slug, payload.title, payload.description, payload.content_type, payload.body,
         video_url, payload.duration_minutes, json.dumps(payload.tags), payload.min_plan,
         payload.min_rank, sort_index, 1 if payload.awards_xp else 0),
    )
    await _audit(db, admin.internal_id, "academy_lesson_create", {"slug": slug, "title": payload.title})
    await db.commit()
    row = await db.execute_fetchall(_SELECT + " WHERE id = ?", (cur.lastrowid,))
    return _row_to_admin(row[0])


@router.put("/lessons/{lesson_id}", response_model=AdminLesson)
async def update(
    lesson_id: int,
    payload: LessonUpdate,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> AdminLesson:
    cur_rows = await db.execute_fetchall(_SELECT + " WHERE id = ?", (lesson_id,))
    if not cur_rows:
        raise HTTPException(404, "unknown lesson")
    existing = _row_to_admin(cur_rows[0])

    content_type = payload.content_type if payload.content_type is not None else existing.content_type
    if content_type not in ("text", "video"):
        raise HTTPException(400, {"code": "INVALID_CONTENT_TYPE"})
    min_plan = payload.min_plan if payload.min_plan is not None else existing.min_plan
    min_rank = payload.min_rank if payload.min_rank is not None else existing.min_rank
    _validate_gates(min_plan, min_rank)
    raw_video = payload.video_url if payload.video_url is not None else existing.video_url
    video_url = _resolve_video(content_type, raw_video)  # None for text; validated for video

    fields = {
        "title": payload.title if payload.title is not None else existing.title,
        "description": payload.description if payload.description is not None else existing.description,
        "content_type": content_type,
        "body": payload.body if payload.body is not None else existing.body,
        "video_url": video_url,
        "duration_minutes": payload.duration_minutes if payload.duration_minutes is not None else existing.duration_minutes,
        "tags": json.dumps(payload.tags if payload.tags is not None else existing.tags),
        "min_plan": min_plan,
        "min_rank": min_rank,
        "awards_xp": 1 if (payload.awards_xp if payload.awards_xp is not None else existing.awards_xp) else 0,
    }
    await db.execute(
        f"""UPDATE academy_lessons SET {", ".join(f"{k} = ?" for k in fields)},
            updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
        (*fields.values(), lesson_id),
    )
    await _audit(db, admin.internal_id, "academy_lesson_update", {"id": lesson_id, "slug": existing.slug})
    await db.commit()
    row = await db.execute_fetchall(_SELECT + " WHERE id = ?", (lesson_id,))
    return _row_to_admin(row[0])


async def _set_archived(db, lesson_id: int, value: str | None, admin_id: int, event: str) -> AdminLesson:
    rows = await db.execute_fetchall("SELECT slug FROM academy_lessons WHERE id = ?", (lesson_id,))
    if not rows:
        raise HTTPException(404, "unknown lesson")
    clause = "archived_at = CURRENT_TIMESTAMP" if value == "now" else "archived_at = NULL"
    await db.execute(f"UPDATE academy_lessons SET {clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (lesson_id,))
    await _audit(db, admin_id, event, {"id": lesson_id, "slug": rows[0][0]})
    await db.commit()
    row = await db.execute_fetchall(_SELECT + " WHERE id = ?", (lesson_id,))
    return _row_to_admin(row[0])


@router.post("/lessons/{lesson_id}/archive", response_model=AdminLesson)
async def archive(
    lesson_id: int,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> AdminLesson:
    return await _set_archived(db, lesson_id, "now", admin.internal_id, "academy_lesson_archive")


@router.post("/lessons/{lesson_id}/restore", response_model=AdminLesson)
async def restore(
    lesson_id: int,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> AdminLesson:
    return await _set_archived(db, lesson_id, None, admin.internal_id, "academy_lesson_restore")


@router.post("/lessons/reorder", response_model=list[AdminLesson])
async def reorder(
    payload: ReorderRequest,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> list[AdminLesson]:
    """Explicit admin ordering (D-AC5): the client sends the full ordered id list (driven by
    up/down buttons); we rewrite sort_index by position."""
    for idx, lesson_id in enumerate(payload.ordered_ids):
        await db.execute(
            "UPDATE academy_lessons SET sort_index = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (idx, lesson_id),
        )
    await _audit(db, admin.internal_id, "academy_lesson_reorder", {"order": payload.ordered_ids})
    await db.commit()
    rows = await db.execute_fetchall(_SELECT + " ORDER BY sort_index, id")
    return [_row_to_admin(r) for r in rows]
