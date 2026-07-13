"""B4 journal / "What Would Have Happened" models (F3).

ScenarioView is deliberately shaped so outcome fields are Optional and OMITTED
(exclude_none) for unrevealed rows — the reveal-gating contract is enforced by never
populating status / r_result / resolved_at until revealed.
"""
from typing import Literal, Optional

from pydantic import BaseModel


class ScenarioView(BaseModel):
    id: int
    type: Literal["pass", "no_setups_day"]
    coin: Optional[str] = None
    direction: Optional[Literal["long", "short"]] = None
    score: Optional[float] = None
    scan_date: Optional[str] = None
    revealed: bool = False
    # --- Outcome (present ONLY when revealed) ---
    status: Optional[str] = None          # win | loss | save | expired | skip
    r_result: Optional[float] = None      # hypothetical R, never money (F3 AC4)
    resolved_at: Optional[str] = None
    viewed: Optional[bool] = None


class JournalStats(BaseModel):
    cumulative_r_revealed: float = 0.0
    capital_saves: int = 0
    awaiting_reveal: int = 0
    skip_days: int = 0
    tracked_days: int = 0
    discipline_pct: int = 0


class JournalResponse(BaseModel):
    stats: JournalStats
    scenarios: list[ScenarioView] = []


class JournalBadge(BaseModel):
    unrevealed: int = 0


class ViewResult(BaseModel):
    xp_awarded: int = 0
