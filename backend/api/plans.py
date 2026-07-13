"""Public plans endpoint (B2 Subscribe). The price / coins / scans values come from
system_settings (admin-editable, mig 019 + 027) so the comparison table stays a
single source of truth with the scan gating. Product rows that are NOT admin-tunable
(Blueprint full on every plan, export, academy) are copy owned by the frontend.
"""
import aiosqlite
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core.database import get_db_connection
from backend.core.entitlements import resolve_entitlements

router = APIRouter(prefix="/api/plans", tags=["plans"])

# Three live plans (Decision A, 2026-07-13). Advanced retired (mig 029).
TIERS = ("free", "basic", "pro")


class Plan(BaseModel):
    tier: str
    price_ils: int          # whole shekels / month (0 for Free)
    coins_per_scan: int
    scans_per_day: int      # 0 = unlimited
    chart_layers: str       # ema200_only | full


class PlansResponse(BaseModel):
    currency: str
    plans: list[Plan]


async def _price_ils(db: aiosqlite.Connection, tier: str) -> int:
    if tier == "free":
        return 0
    rows = await db.execute_fetchall(
        "SELECT value FROM system_settings WHERE key = ?", (f"plan_price_{tier}",)
    )
    if rows and rows[0][0] is not None:
        try:
            return int(rows[0][0]) // 100  # agorot → shekels
        except (TypeError, ValueError):
            return 0
    return 0


@router.get("", response_model=PlansResponse)
async def list_plans(db: aiosqlite.Connection = Depends(get_db_connection)) -> PlansResponse:
    plans = []
    for tier in TIERS:
        ent = await resolve_entitlements(db, tier)
        plans.append(
            Plan(
                tier=tier,
                price_ils=await _price_ils(db, tier),
                coins_per_scan=ent["coins_per_scan"],
                scans_per_day=ent["scans_per_day"],
                chart_layers=ent["chart_layers"],
            )
        )
    return PlansResponse(currency="₪", plans=plans)
