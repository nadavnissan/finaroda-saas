"""
Cardcom v11 REST — sole payment provider (SPEC §9). Wired in TEST/SANDBOX mode:
all charges gated by FEATURE_CARDCOM_LIVE (default false). No Morning/Stripe/legacy.

Endpoints: initiate (checkout), webhook (HMAC), status, cancel.
"""
import aiosqlite
import structlog
from fastapi import APIRouter, Depends, Header, Request

from backend.core import cardcom_service
from backend.core.auth import get_current_user
from backend.core.database import get_db_connection
from backend.models.auth import CurrentUser
from backend.models.cardcom import (
    CardcomCancelResponse,
    CardcomInitiateRequest,
    CardcomInitiateResponse,
    SubscriptionStatusResponse,
)

router = APIRouter(prefix="/cardcom", tags=["payments"])
log = structlog.get_logger(__name__)


@router.post("/initiate", response_model=CardcomInitiateResponse)
async def initiate(
    body: CardcomInitiateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> CardcomInitiateResponse:
    """Start a Cardcom checkout for a plan (503 in test mode until a terminal is wired)."""
    return await cardcom_service.initiate_checkout(
        user_id=user.internal_id, plan=body.plan, db=db, is_upgrade=body.is_upgrade
    )


@router.post("/webhook")
async def webhook(
    request: Request,
    x_cardcom_signature: str = Header(default=""),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Cardcom payment webhook (HMAC-verified). Always returns 200 (idempotent)."""
    raw_body = await request.body()
    await cardcom_service.handle_webhook(raw_body, x_cardcom_signature, db)
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


@router.post("/cancel", response_model=CardcomCancelResponse)
async def cancel(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> CardcomCancelResponse:
    """Cancel the active subscription at period end."""
    return await cardcom_service.cancel_subscription(user_id=user.internal_id, db=db)
