"""Scan persistence models (SPEC §5). score is nullable until engine pass 2."""
from typing import Literal, Optional

from pydantic import BaseModel


class ScoreLogItem(BaseModel):
    coin: str
    direction: Literal["long", "short"]
    profile: str = "momentum"          # momentum (displayed) | pullback | continuation
    score: Optional[float] = None      # real scorer score; may be null if scoring failed
    passed_threshold: int              # 0/1 (real 85/82 gate on the momentum profile)
    ema7_slope_pct: Optional[float] = None
    volume_ratio: Optional[float] = None
    price: Optional[float] = None
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    trailing_pct: Optional[float] = None


class ScanEventCreate(BaseModel):
    coins_scanned: int
    coins_passed: int
    threshold: Optional[float] = None
    client_ip_region: Optional[str] = None
    coins: list[ScoreLogItem] = []


class ScanEventResponse(BaseModel):
    scan_event_id: int
    score_logs: list[dict]  # [{coin, id}]
    first_scan_of_day: bool = False   # true only on the day's first scan (D3)
    xp_awarded: int = 0               # +50 on first scan of day, else 0 (server-authoritative)


class EntitlementsResponse(BaseModel):
    """Server-authoritative scan gating for the current user's plan (B1)."""
    tier: str
    coins_per_scan: int
    chart_layers: Literal["ema200_only", "full"]
    scans_per_day: int  # 0 = unlimited


class SnapshotCreate(BaseModel):
    score_log_id: int
    card_json: str


class SnapshotResponse(BaseModel):
    id: int
