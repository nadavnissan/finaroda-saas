"""
Cardcom v11 REST — sole payment provider for FINARODA V1 (SPEC §9).

P0 scope: PLACEHOLDER router only — routes are declared so the app boots and the
contract is visible, but the live Cardcom wiring (LowProfile/Create, ChargeToken,
HMAC webhook, trial tokenization) is implemented in P1 (SPEC §11).

Morning (Green Invoice), legacy aiohttp payment, and the Stripe stub are NOT
inherited — Cardcom is the single payment stack.
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/cardcom", tags=["payments"])

_NOT_IMPLEMENTED = JSONResponse(
    status_code=501,
    content={
        "error": {
            "code": "NOT_IMPLEMENTED",
            "message": "Cardcom wiring lands in P1 (SPEC §9). P0 is skeleton only.",
        }
    },
)


@router.post("/initiate")
async def initiate_checkout() -> JSONResponse:
    """Create a Cardcom LowProfile checkout session. Wired in P1."""
    return _NOT_IMPLEMENTED


@router.post("/webhook")
async def cardcom_webhook(request: Request) -> JSONResponse:
    """Receive Cardcom payment webhook (HMAC-verified). Wired in P1."""
    return _NOT_IMPLEMENTED


@router.post("/cancel")
async def cancel_subscription() -> JSONResponse:
    """Cancel an active recurring subscription. Wired in P1."""
    return _NOT_IMPLEMENTED
