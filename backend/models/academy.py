"""Academy 2.0 models (F6). DB-backed lessons (mig 033), flat card grid, dual gating
(min_plan + min_rank), text/video content types. Completion/XP stays in xp_events
(source='academy_lesson', ref=slug) UNCHANGED — see api/academy.py."""
from typing import Optional

from pydantic import BaseModel


class AcademyLesson(BaseModel):
    """Card / list metadata. Never carries the gated body/video_url (D-AC7)."""
    slug: str
    title: str
    description: str = ""
    content_type: str = "text"           # 'text' | 'video'
    duration_minutes: int = 0
    tags: list[str] = []
    min_plan: str = "free"
    min_rank: int = 0
    sort_index: int = 0
    unlocked: bool = False
    completed: bool = False
    awards_xp: bool = True
    lock_reason: Optional[str] = None    # plain language, only when locked
    # Backward-compatible aliases for the B6 client + existing tests.
    id: str = ""                         # == slug
    minutes: int = 0                     # == duration_minutes


class AcademyResponse(BaseModel):
    modules: list[AcademyLesson]         # key kept 'modules' for backward compat
    xp_total: int = 0


class LessonContent(BaseModel):
    """Full gated content, served by GET /api/academy/{slug} only when unlocked."""
    slug: str
    title: str
    description: str = ""
    content_type: str = "text"
    duration_minutes: int = 0
    tags: list[str] = []
    body: str = ""
    video_url: Optional[str] = None
    completed: bool = False
    awards_xp: bool = True


class LessonResult(BaseModel):
    xp_awarded: int = 0
    completed: bool = False


# ── Admin models ─────────────────────────────────────────────────────────────
class AdminLesson(BaseModel):
    id: int
    slug: str
    title: str
    description: str = ""
    content_type: str = "text"
    body: str = ""
    video_url: Optional[str] = None
    duration_minutes: int = 0
    tags: list[str] = []
    min_plan: str = "free"
    min_rank: int = 0
    sort_index: int = 0
    awards_xp: bool = True
    archived: bool = False


class LessonCreate(BaseModel):
    title: str
    slug: Optional[str] = None
    description: str = ""
    content_type: str = "text"
    body: str = ""
    video_url: Optional[str] = None
    duration_minutes: int = 0
    tags: list[str] = []
    min_plan: str = "free"
    min_rank: int = 0
    awards_xp: bool = True


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content_type: Optional[str] = None
    body: Optional[str] = None
    video_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    tags: Optional[list[str]] = None
    min_plan: Optional[str] = None
    min_rank: Optional[int] = None
    awards_xp: Optional[bool] = None


class ReorderRequest(BaseModel):
    ordered_ids: list[int]
