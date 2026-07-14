"""
Billing API (Stage 3R) — Stripe Checkout + Billing (sole PSP; replaces the prior provider).

Endpoints (mounted at /api/billing): checkout, trial, webhook, status, cancel.
Checkout runs in DEV mode (fake session, zero network) until a live key is set. Activation
happens ONLY through the signature-verified webhook, never the browser redirect (AC2).
"""
import aiosqlite
import structlog
from fastapi import APIRouter, Depends, Header, Request

from backend.core import stripe_service
from backend.core.auth import get_current_user
from backend.core.database import get_db_connection
from backend.models.auth import CurrentUser
from backend.models.billing import (
    CheckoutInitiateRequest,
    CheckoutInitiateResponse,
    SubscriptionCancelResponse,
    SubscriptionStatusResponse,
)

router = APIRouter(prefix="/billing", tags=["payments"])
log = structlog.get_logger(__name__)


@router.post("/checkout", response_model=CheckoutInitiateResponse)
async def checkout(
    body: CheckoutInitiateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> CheckoutInitiateResponse:
    """Create a Stripe Checkout Session for a plan (DEV fake session until a live key)."""
    return await stripe_service.initiate_checkout(
        user_id=user.internal_id, plan=body.plan, db=db, is_upgrade=body.is_upgrade
    )


@router.post("/trial")
async def start_trial(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Start the 14-day Pro trial WITHOUT a card (D-R2). 409 if already used."""
    return await stripe_service.start_trial(db=db, user_id=user.internal_id, plan="pro")


@router.post("/webhook")
async def webhook(
    request: Request,
    stripe_signature: str = Header(default=""),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Stripe webhook (signature-verified, idempotent by event id). Always 200."""
    raw_body = await request.body()
    await stripe_service.handle_webhook(raw_body, stripe_signature, db)
    return {"received": True}


@router.get("/status", response_model=SubscriptionStatusResponse)
async def status(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> SubscriptionStatusResponse:
    """Return the current user's subscription/trial status."""
    rows = await db.execute_fetchall(
        """SELECT tier, subscription_status, trial_ends_at, next_billing_at,
                  subscription_cancelled_pending_at
           FROM users WHERE internal_id = ?""",
        (user.internal_id,),
    )
    row = dict(rows[0])
    return SubscriptionStatusResponse(
        tier=row["tier"],
        subscription_status=row["subscription_status"],
        trial_ends_at=row.get("trial_ends_at"),
        next_billing_at=row.get("next_billing_at"),
        cancelled_pending_at=row.get("subscription_cancelled_pending_at"),
    )


@router.post("/cancel", response_model=SubscriptionCancelResponse)
async def cancel(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> SubscriptionCancelResponse:
    """Cancel the active subscription at period end (Stripe cancel_at_period_end)."""
    return await stripe_service.cancel_subscription(user_id=user.internal_id, db=db)
