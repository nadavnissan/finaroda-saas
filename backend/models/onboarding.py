"""Onboarding F13 models — episodes (with server-side withholding), XP, funnel."""
from typing import Literal, Optional

from pydantic import BaseModel

# ── Candles ───────────────────────────────────────────────────────────────────


class Candle(BaseModel):
    t: int  # epoch ms (daily)
    o: float
    h: float
    l: float
    c: float
    v: float
    ema7: Optional[float] = None    # real fast EMA (verified edge)
    ema200: Optional[float] = None  # real 200-day average (the macro blocking flag, S3)


# ── Episodes ──────────────────────────────────────────────────────────────────


class EpisodeSetup(BaseModel):
    """Pre-decision view. Deliberately OMITS reveal candles and outcome."""
    ext_id: str
    coin: str
    date_range: str
    scenario_type: str
    lesson_flag: Optional[str] = None
    direction: Optional[str] = None
    entry_index: int
    entry_price: Optional[float] = None
    spike_index: Optional[int] = None  # candle with the biggest move in the setup (annotation)
    setup_klines: list[Candle]      # candles 0..entry_index (inclusive)
    reveal_count: int               # how many candles are withheld (for playback UI)
    score: Optional[float] = None   # only for valid_setup (PASS demo)


class EpisodeOutcome(BaseModel):
    resolved: Literal["win", "loss"]
    direction: str
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    risk_price: Optional[float] = None   # Calculated Risk Level (drawn on the Blueprint)
    r_multiple: Optional[float] = None
    pct: Optional[float] = None
    squeeze_pct: Optional[float] = None  # up-move against an impulse short before the fade
    checks: Optional[list[dict]] = None  # top passed checks for the PASS demo (Why PASS)
    score: Optional[float] = None
    real_stats_ref: Optional[str] = None


class EpisodeReveal(BaseModel):
    """Returned only by the explicit reveal call (S1 trap, S10 time-machine)."""
    ext_id: str
    reveal_klines: list[Candle]     # candles entry_index+1..end
    outcome: EpisodeOutcome


# ── XP (server-authoritative; granted once at completion) ─────────────────────


class XPState(BaseModel):
    total: int
    events: list[dict]  # [{source, ref, amount}]


# ── Funnel ────────────────────────────────────────────────────────────────────


class FunnelEventCreate(BaseModel):
    stage: str
    anon_id: Optional[str] = None
    detail: Optional[dict] = None


class OkResponse(BaseModel):
    ok: bool = True
