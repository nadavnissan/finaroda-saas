"""Billing models (Stage 3R — Stripe). Amounts in agorot (1/100 ILS). FINARODA plans."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class CheckoutInitiateRequest(BaseModel):
    """Start a Stripe Checkout Session for a FINARODA plan."""
    plan: Literal["basic", "pro"]
    is_upgrade: bool = False


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
