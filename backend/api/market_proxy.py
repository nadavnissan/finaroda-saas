"""
Thin CORS-fallback proxy for Bybit public market endpoints (SPEC §6.2).

The DEFAULT path is a direct browser fetch (client IP, no shared cache). This proxy
exists ONLY as a CORS fallback for endpoints the browser can't reach directly. It does
NOT merge or cache data — it forwards the query and returns Bybit's JSON verbatim.
Whitelisted endpoints only.
"""
import httpx
import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.config import BYBIT_PUBLIC_BASE_URL

router = APIRouter(prefix="/api/market", tags=["market"])
log = structlog.get_logger(__name__)

_ALLOWED = {"kline", "tickers", "orderbook", "open-interest"}
_TIMEOUT = 15.0


@router.get("/proxy/{endpoint}")
async def bybit_proxy(endpoint: str, request: Request) -> JSONResponse:
    """Forward GET {BYBIT_PUBLIC_BASE_URL}/{endpoint}?<same query>. No merge, no cache."""
    if endpoint not in _ALLOWED:
        raise HTTPException(400, f"Endpoint not allowed: {endpoint}")
    url = f"{BYBIT_PUBLIC_BASE_URL}/{endpoint}"
    params = dict(request.query_params)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, params=params)
        return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as e:  # noqa: BLE001
        log.warning("bybit_proxy_error", endpoint=endpoint, error=str(e))
        raise HTTPException(502, "Upstream market data error")
