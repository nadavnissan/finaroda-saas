"""
backend/config.py — Authoritative configuration for FINARODA SaaS.
Reads all values from environment variables (loaded from .env / .env.local).
All module-level constants are exported for use across the backend.

Scope: infra only. Career/Agent/RAG/Morning config NOT inherited (SPEC §3.3).
Payment provider is Stripe (Checkout + Billing) as of Stage 3R (2026-07-14); prior PSP retired.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env")
load_dotenv(_project_root / ".env.local", override=True)

# ── General ──────────────────────────────────────────────────────────────────
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")
API_URL = os.getenv("API_URL", "http://localhost:8000")
ADMIN_URL = os.getenv("ADMIN_URL", "http://localhost:3001")
FRONTEND_URL = os.getenv("FRONTEND_URL", BASE_URL)
DATABASE_URL = os.getenv("DATABASE_URL", "data/finaroda.db")

# ── JWT / Auth ────────────────────────────────────────────────────────────────
_raw_jwt_secret = os.getenv("JWT_SECRET", "")
if not _raw_jwt_secret:
    if ENVIRONMENT in ("production", "staging"):
        raise RuntimeError(
            "JWT_SECRET env var is required in production/staging. "
            "Generate with: openssl rand -hex 32"
        )
    JWT_SECRET = "dev-only-jwt-secret-do-not-use-in-production"
    logging.warning(
        "⚠️  Using development JWT_SECRET. "
        "Set JWT_SECRET env var before deploying to production."
    )
else:
    JWT_SECRET = _raw_jwt_secret

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = int(os.getenv("JWT_EXPIRE_DAYS", "30"))
MAGIC_LINK_EXPIRE_MINUTES = int(os.getenv("MAGIC_LINK_EXPIRE_MINUTES", "15"))
OAUTH_STATE_TTL_MINUTES = int(os.getenv("OAUTH_STATE_TTL_MINUTES", "10"))

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "")
APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID", "")

# Admin is a DB role (`users.is_admin`), per SPEC §4 — NOT an env id list.
# These emails are auto-granted is_admin=1 on signup, to bootstrap the first admin.
ADMIN_BOOTSTRAP_EMAILS: list[str] = [
    e.strip().lower()
    for e in os.getenv("ADMIN_BOOTSTRAP_EMAILS", "rodanis@gmail.com").split(",")
    if e.strip()
]

# Beta gate (closed beta until public launch).
FEATURE_PUBLIC_SIGNUPS_OPEN: bool = os.getenv("FEATURE_PUBLIC_SIGNUPS_OPEN", "false").lower() == "true"

# F16b/F17 Arena gate. Default OFF. Gates the R4 (save_confirmed) and R5 (save_missed)
# Outcome Narratives, which need F17's counterfactual data and final lawyer clearance.
# R1/R2/R3 (win/loss/expired) ship LIVE and are NOT gated. The frontend mirrors this via
# NEXT_PUBLIC_FEATURE_ARENA (also default OFF).
FEATURE_ARENA: bool = os.getenv("FEATURE_ARENA", "false").lower() == "true"

# ── Storage Backend ───────────────────────────────────────────────────────────
# "local" (default): saves files to disk — no external deps.
# "r2": uploads to Cloudflare R2 via aioboto3 — set in production .env.
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower()
LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "_local_storage")

# ── Cloudflare R2 ─────────────────────────────────────────────────────────────
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_ENDPOINT_URL = os.getenv(
    "R2_ENDPOINT_URL",
    f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else "",
)
R2_BUCKET_ACADEMY = os.getenv("R2_BUCKET_ACADEMY", "finaroda-academy")
R2_BUCKET_DB_BACKUP = os.getenv("R2_BUCKET_DB_BACKUP", "finaroda-db-backup")
R2_PUBLIC_URL_ACADEMY = os.getenv("R2_PUBLIC_URL_ACADEMY", "").rstrip("/")

# ── Encryption ───────────────────────────────────────────────────────────────
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# ── Email (Resend, transactional only — marketing goes via admin broadcast) ──
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM_BRAND = os.getenv("EMAIL_FROM_BRAND", "FINARODA <noreply@finaroda.com>")
EMAIL_REPLY_TO = os.getenv("EMAIL_REPLY_TO", "support@finaroda.com")
EMAIL_SENDING_ENABLED = os.getenv("EMAIL_SENDING_ENABLED", "false").lower() == "true"
# DEV ONLY — when True and RESEND_API_KEY empty, magic link returned in API response.
# Must be False (default) in production.
DEV_RETURN_MAGIC_LINK = os.getenv("DEV_RETURN_MAGIC_LINK", "false").lower() == "true"

# ── Cron (Stage 5 scheduled notification sweeps — SPEC §5) ───────────────────
# Shared secret for POST /api/cron/notifications (day-11 reminder + reveal-teaser).
# Sent as the `X-Cron-Secret` header. Empty in dev disables the endpoint (503) so a
# misconfigured deploy never runs unauthenticated. Railway wiring is manual (HANDOFF).
CRON_SECRET = os.getenv("CRON_SECRET", "")

# ── Trial ─────────────────────────────────────────────────────────────────────
# Trial WITHOUT card (D1 change order 2026-07-09; SPEC §9/§12.3, PRD F7): no card,
# no tokenization, no auto-charge. A reminder goes out TRIAL_REMINDER_LEAD_DAYS before
# the end (day 11 of a 14-day trial); at expiry the user is moved to Free, never charged.
TRIAL_DAYS: int = int(os.getenv("TRIAL_DAYS", "14"))
TRIAL_REMINDER_LEAD_DAYS: int = int(os.getenv("TRIAL_REMINDER_LEAD_DAYS", "3"))

# ── Billing (Stage 3R — Stripe Billing owns recurring + dunning) ─────────────
# Fallback recurring period in days, used only to compute a display "renews on" date
# when a webhook does not carry the subscription's current_period_end (e.g. DEV mode).
# The authoritative period boundary comes from Stripe (subscription.current_period_end).
# Dunning (retries) is Stripe Smart Retries now — the homegrown +24h/+72h scheduler was
# deleted in Stage 3R. Our failure/recovery emails still fire from the Stripe webhook.
BILLING_PERIOD_DAYS: int = int(os.getenv("BILLING_PERIOD_DAYS", "30"))

# ── Stripe (Checkout + Billing — sole PSP since Stage 3R, 2026-07-14) ─────────
# ⚠️ TEST by default: FEATURE_STRIPE_LIVE=false and/or an empty STRIPE_SECRET_KEY put
# the layer in DEV fallback (checkout returns a dev-mode fake session, no network — the
# same pattern as DEV_RETURN_MAGIC_LINK). Going live is a manual step by Nadav on the
# LTD's Stripe account (see the GO-LIVE box in SESSION_HANDOFF). Never commit a live key.
FEATURE_STRIPE_LIVE: bool = os.getenv("FEATURE_STRIPE_LIVE", "false").lower() == "true"
STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
# Post-checkout redirect targets (Stripe appends its own session id to the success URL).
STRIPE_SUCCESS_PATH: str = os.getenv("STRIPE_SUCCESS_PATH", "/checkout/success")
STRIPE_CANCEL_PATH: str = os.getenv("STRIPE_CANCEL_PATH", "/checkout/cancelled")

# ── Israeli tax-invoice provider (Stage 3R) ──────────────────────────────────
# The provider that issues the legal Israeli tax-invoice-receipt per successful charge.
# 'mock' (default) writes a clearly-marked offline document (zero network) so the whole
# flow stays testable. Real providers (green_invoice | icount | ezcount) are a documented
# interface in core/invoice_provider.py — NOT chosen yet. Stripe's own invoices are NOT
# Israeli tax documents and are never presented as such.
INVOICE_PROVIDER: str = os.getenv("INVOICE_PROVIDER", "mock").lower()

# ── Scan engine (FINARODA core — SPEC §6) ────────────────────────────────────
# Bybit public market endpoint (no API key). Default fetch is client-side; this is
# the thin CORS-fallback proxy base. Coin/threshold limits live in system_settings.
BYBIT_PUBLIC_BASE_URL: str = os.getenv("BYBIT_PUBLIC_BASE_URL", "https://api.bybit.com/v5/market")
DEFAULT_SCAN_THRESHOLD: float = float(os.getenv("DEFAULT_SCAN_THRESHOLD", "70.0"))

# ── Monitoring / Sentry ───────────────────────────────────────────────────────
# Backend DSN: prefer SENTRY_DSN_BACKEND, fall back to a shared SENTRY_DSN. Absent in
# dev/test → Sentry fully disabled (zero network). Frontend uses NEXT_PUBLIC_SENTRY_DSN.
SENTRY_DSN_BACKEND: str = os.getenv("SENTRY_DSN_BACKEND") or os.getenv("SENTRY_DSN", "")
SENTRY_ENVIRONMENT: str = os.getenv("SENTRY_ENVIRONMENT", ENVIRONMENT)
SENTRY_TRACES_SAMPLE_RATE: float = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
SENTRY_RELEASE: str = os.getenv("SENTRY_RELEASE", "")


def get_frontend_url() -> str:
    """Lazy lookup so .env.local can be loaded after config import."""
    return os.getenv("FRONTEND_URL") or BASE_URL
