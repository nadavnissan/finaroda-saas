"""P0 smoke tests — the clean skeleton boots and the schema applies."""
import os
import tempfile
from pathlib import Path

import aiosqlite
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.migrations.run_migrations import apply_migrations

# Every table the clean migration set must create.
EXPECTED_TABLES = {
    "users",
    "payment_transactions",
    "subscription_events",
    "coupons",
    "coupon_redemptions",
    "referrals",
    "referral_credits",
    "notifications",
    "consent_log",
    "customer_segments",
    "churn_reasons",
    "admin_events",
    "feature_flags",
    "user_feature_overrides",
    "system_settings",
    "academy_bundles",
    "academy_episodes",
    "academy_episode_views",
    "academy_task_uploads",
    "oauth_states",
    "beta_allowlist",
    "waitlist",
    "admin_broadcasts",
    "broadcast_reads",
    "onboarding_questions",
    "onboarding_responses",
    "scan_events",
    "score_log",
    "decision_snapshots",
    "support_tickets",
    "episodes",
    "xp_events",
    "onboarding_funnel_events",
}

# Career/Agent tables that must NOT exist (discarded — SPEC §3.3).
FORBIDDEN_TABLES = {
    "conversations",
    "agent_tool_calls",
    "cv_versions",
    "jobs_pool",
    "nadav_brain_embeddings",
    "simulation_sessions",
    "panel_reviews",
    "linkedin_connections",
    "daily_exercises",
    "imposter_events",
    "brand_narrative_checkins",
    "pending_questions",
}


@pytest.mark.asyncio
async def test_migrations_apply_clean_schema():
    """All clean migrations apply and produce exactly the expected infra schema."""
    tmp_db = Path(tempfile.gettempdir()) / "finaroda_migrate_test.db"
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(tmp_db) + suffix)
        if p.exists():
            p.unlink()

    await apply_migrations(str(tmp_db))

    async with aiosqlite.connect(str(tmp_db)) as db:
        rows = await db.execute_fetchall(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    tables = {r[0] for r in rows}

    missing = EXPECTED_TABLES - tables
    assert not missing, f"Missing expected tables: {sorted(missing)}"

    leaked = FORBIDDEN_TABLES & tables
    assert not leaked, f"Career-layer tables must not exist: {sorted(leaked)}"


def test_health_endpoint():
    """The app boots (runs startup migrations) and /api/health responds 200."""
    with TestClient(app) as client:
        resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.2.0"


def test_billing_checkout_requires_auth():
    """Billing checkout is auth-protected (P1): no cookie → 401."""
    with TestClient(app) as client:
        resp = client.post("/api/billing/checkout", json={"plan": "basic"})
    assert resp.status_code == 401
