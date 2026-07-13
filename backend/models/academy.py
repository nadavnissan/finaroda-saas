"""B6 academy models (F6). Modules map 1:1 to the 12 `academy` ids in
concept_tooltips_content.json. has_lesson gates the +100 XP (stubs award nothing)."""
from typing import Optional

from pydantic import BaseModel


class AcademyModule(BaseModel):
    id: str                      # academy id (deep-link #anchor target)
    title: str
    minutes: int
    term_count: int
    has_lesson: bool             # real content → completable for +100 XP
    tier: str                    # 'basic' | 'full' (plan gate) — ignored if bonus
    rank_unlock: Optional[int] = None   # bonus module: unlocked at this XP, plan-agnostic
    unlocked: bool = False       # for THIS user (plan / rank)
    completed: bool = False


class AcademyResponse(BaseModel):
    modules: list[AcademyModule]
    xp_total: int = 0


class LessonResult(BaseModel):
    xp_awarded: int = 0
    completed: bool = False
