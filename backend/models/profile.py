"""B5 profile models (F5). Rank ladder is derived client-side from xp_total
(XP_ECONOMY.md v1.0); the API returns the raw total + remembered settings."""
from typing import Literal, Optional

from pydantic import BaseModel


class TrialState(BaseModel):
    active: bool
    day: int
    total: int
    no_card: bool = True


class ProfileSettings(BaseModel):
    analysis_lens: Literal["ema200", "rsi", "volume", "full"] = "full"
    risk_style: Literal["conservative", "balanced", "aggressive"] = "balanced"
    coin_prefs: list[str] = []
    palette: str = "terminal"


class ProfileResponse(BaseModel):
    call_sign: str
    email: str
    tier: str
    subscription_status: str
    trial: Optional[TrialState] = None
    xp_total: int = 0
    settings: ProfileSettings


class SettingsUpdate(BaseModel):
    call_sign: Optional[str] = None
    analysis_lens: Optional[Literal["ema200", "rsi", "volume", "full"]] = None
    risk_style: Optional[Literal["conservative", "balanced", "aggressive"]] = None
    coin_prefs: Optional[list[str]] = None
    palette: Optional[str] = None
