"""Billing models (Stage 3R — Stripe). Amounts in agorot (1/100 ILS). FINARODA plans."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class CheckoutInitiateRequest(BaseModel):
    """Start a Stripe Checkout Session for a FINARODA plan.

    `promotion_code` is optional: when supplied (e.g. from a promo link), it is validated
    our-side for the plan BEFORE the session is created (D-S1/AC2) and applied via the
    session `discounts`. When omitted, the session enables Stripe's hosted promotion-code
    field instead (allow_promotion_codes, D-S3)."""
    plan: Literal["basic", "pro"]
    is_upgrade: bool = False
    promotion_code: Optional[str] = None


class CouponValidateRequest(BaseModel):
    code: str
    plan: Literal["basic", "pro"]


class CouponValidateResponse(BaseModel):
    valid: bool
    reason: Optional[str] = None
    discount_type: Optional[str] = None
    percent_off: Optional[int] = None
    amount_off_agorot: Optional[int] = None


class CheckoutInitiateResponse(BaseModel):
    redirect_url: str            # hosted Stripe Checkout URL (or a DEV success-page URL)
    transaction_id: int
    expires_at: datetime
    dev_mode: bool = False


class SubscriptionCancelResponse(BaseModel):
    cancelled_at: datetime
    access_until: Optional[datetime]
    message: str


class SubscriptionStatusResponse(BaseModel):
    tier: str
    subscription_status: str
    trial_ends_at: Optional[datetime] = None
    next_billing_at: Optional[datetime] = None
    cancelled_pending_at: Optional[datetime] = None
