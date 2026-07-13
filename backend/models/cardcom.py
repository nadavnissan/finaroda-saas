"""Cardcom payment models. Amounts in agorot (1/100 ILS). FINARODA plans."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class CardcomInitiateRequest(BaseModel):
    """Initiate a Cardcom checkout for a FINARODA plan."""
    plan: Literal["basic", "pro"]
    is_upgrade: bool = False


class CardcomInitiateResponse(BaseModel):
    redirect_url: str
    transaction_id: int
    expires_at: datetime


class CardcomCancelResponse(BaseModel):
    cancelled_at: datetime
    access_until: Optional[datetime]
    message: str


class SubscriptionStatusResponse(BaseModel):
    tier: str
    subscription_status: str
    trial_ends_at: Optional[datetime] = None
    next_billing_at: Optional[datetime] = None
    cancelled_pending_at: Optional[datetime] = None
