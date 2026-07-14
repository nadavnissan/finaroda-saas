"""B7 admin console request models. GET responses are plain dicts (internal console)."""
from typing import Literal, Optional

from pydantic import BaseModel


class UserOverride(BaseModel):
    action: Literal["plan_override", "extend_trial", "grant_xp", "suspend", "unsuspend"]
    value: Optional[str] = None       # tier for plan_override; days for extend; amount for grant_xp
    note: str                          # audit reason (required)


class TicketReplyCreate(BaseModel):
    body: str
    status: Optional[Literal["open", "in_progress", "resolved", "closed"]] = None


class TicketStatusUpdate(BaseModel):
    status: Literal["open", "in_progress", "resolved", "closed"]


class BroadcastCreate(BaseModel):
    title: str
    body: str
    audience: Literal["all", "plan", "trial_ending"] = "all"
    target_tier: Optional[Literal["free", "basic", "pro"]] = None
    channel_in_app: bool = True
    channel_email: bool = False


class SettingUpdate(BaseModel):
    key: str
    value: str


class SettingsUpdateBatch(BaseModel):
    updates: list[SettingUpdate]
    note: str = "settings edit"


# ── Stage 4: coupons + referral admin ────────────────────────────────────────
class CouponCreate(BaseModel):
    """Admin-created coupon → drives Stripe Coupon + Promotion Code (D-S2). Amounts in
    agorot (ILS minor unit). duration is always 'once' (first charge only, D-S1)."""
    code: str
    discount_type: Literal["percent", "fixed"]
    percent_off: Optional[int] = None            # 1..100 for percent
    amount_off_agorot: Optional[int] = None      # positive agorot for fixed
    max_redemptions: Optional[int] = None        # None = unlimited
    expires_at: Optional[str] = None             # ISO datetime or None
    plan_restriction: Optional[Literal["basic", "pro"]] = None
    description: Optional[str] = None


class ReferralVoid(BaseModel):
    note: str = "referral voided"
