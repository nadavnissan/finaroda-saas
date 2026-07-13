"""
FINARODA SaaS — FastAPI application entry point.
Start with: uvicorn backend.main:app --reload --port 8000

P0 scope: clean skeleton. Only health + Cardcom placeholder are wired.
Scan / dashboard / admin / academy / auth routers arrive in later phases (SPEC §11).
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env.local first (dev overrides), .env second (defaults).
# Must run before backend.config is imported so os.getenv() picks up the values.
_env_dir = Path(__file__).parent
load_dotenv(_env_dir / ".env.local")
load_dotenv(_env_dir / ".env")

# Ensure project root is on the path when running from project root.
sys.path.insert(0, str(Path(__file__).parent.parent))

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import (
    ADMIN_URL,
    BASE_URL,
    DEV_RETURN_MAGIC_LINK,
    ENVIRONMENT,
    FRONTEND_URL,
)
from backend.core.logging_config import configure_logging

configure_logging()

import structlog

log = structlog.get_logger(__name__)

if ENVIRONMENT == "production" and DEV_RETURN_MAGIC_LINK:
    raise RuntimeError(
        "DEV_RETURN_MAGIC_LINK must be False in production — "
        "it exposes magic links in API responses."
    )


def _init_sentry() -> None:
    from backend.config import SENTRY_ENVIRONMENT
    from backend.core.monitoring import init_sentry

    if init_sentry():
        log.info("sentry_init", environment=SENTRY_ENVIRONMENT)


_init_sentry()


async def _run_startup_migrations() -> None:
    from backend.config import DATABASE_URL
    from backend.migrations.run_migrations import apply_migrations

    db_path = (
        DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    )
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    await apply_migrations(db_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", environment=ENVIRONMENT)
    await _run_startup_migrations()
    log.info("startup_complete", message="FINARODA API is ready")
    yield
    log.info("shutdown", message="FINARODA API shutting down")


app = FastAPI(
    title="FINARODA SaaS API",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
_cors_origins = [BASE_URL, ADMIN_URL, FRONTEND_URL]
if ENVIRONMENT != "production":
    _cors_origins += ["http://localhost:3000", "http://localhost:3001"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(_cors_origins)),  # deduplicate
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────────


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "NOT_FOUND", "message": "Resource not found"}},
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    log.error("unhandled_error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}},
    )


# ── Health endpoint ───────────────────────────────────────────────────────────


@app.get("/api/health", tags=["system"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.2.0",
        "environment": ENVIRONMENT,
    }


# ── Routers ───────────────────────────────────────────────────────────────────
from backend.api.academy import router as academy_router
from backend.api.admin import router as admin_router
from backend.api.auth import router as auth_router
from backend.api.broadcasts import router as broadcasts_router
from backend.api.cardcom import router as cardcom_router
from backend.api.churn import router as churn_router
from backend.api.cron import router as cron_router
from backend.api.email import router as email_router
from backend.api.journal import router as journal_router
from backend.api.market_proxy import router as market_proxy_router
from backend.api.notifications import router as notifications_router
from backend.api.onboarding import router as onboarding_router
from backend.api.plans import router as plans_router
from backend.api.profile import router as profile_router
from backend.api.scan import router as scan_router
from backend.api.support import router as support_router
from backend.api.waitlist import router as waitlist_router

app.include_router(auth_router)
app.include_router(waitlist_router)
app.include_router(cardcom_router, prefix="/api")
app.include_router(scan_router)
app.include_router(market_proxy_router)
app.include_router(onboarding_router)
app.include_router(support_router)
app.include_router(plans_router)
app.include_router(journal_router)
app.include_router(profile_router)
app.include_router(academy_router)
app.include_router(admin_router)
app.include_router(broadcasts_router)
app.include_router(notifications_router)
app.include_router(email_router)
app.include_router(cron_router)
app.include_router(churn_router)
