"""RED-LINE SUITE — server-authoritative entitlements (ATP V1, TC-V1-ENT-xx).

The product's constitution: entitlements are decided on the SERVER, per plan x rank x
subscription-state. Plans buy breadth (coins, chart layers, history) and never a
different verdict — the score/threshold is identical on every plan (RED LINE §3.5.5).

This suite proves, as laws:
  - every logged-in endpoint 401s without a session,
  - every admin endpoint 403s for a non-admin (including the Stage-4 promo endpoints),
  - the plan matrix (free/basic/pro) resolves the documented breadth and nothing else,
  - the subscription state machine collapses non-entitled states to Free,
  - the academy dual-gate honours plan AND the trial=Pro rule,
  - a SUSPENDED account cannot keep using protected endpoints (TC-V1-ENT-09).
"""
from urllib.parse import parse_qs, urlparse

import aiosqlite
import pytest
from fastapi.testclient import TestClient

import backend.config as cfg
from backend.core import billing_state as bs
from backend.core.entitlements import resolve_entitlements
from backend.main import app

_ADMIN = "rodanis@gmail.com"

# Logged-in GET endpoints that must 401 with no cookie.
_AUTH_GETS = [
    "/api/scan/entitlements", "/api/scan/history", "/api/journal", "/api/journal/badge",
    "/api/academy", "/api/profile", "/api/notifications", "/api/notifications/prefs",
    "/api/referral", "/api/billing/status",
]
# Admin GET endpoints that must 403 for a non-admin (includes Stage-4 promos).
_ADMIN_GETS = [
    "/api/admin/overview", "/api/admin/users", "/api/admin/users/export.csv",
    "/api/admin/tickets", "/api/admin/churn", "/api/admin/settings",
    "/api/admin/broadcasts", "/api/admin/notifications", "/api/admin/coupons",
    "/api/admin/referrals", "/api/admin/academy/lessons",
]


def _login(client: TestClient, email: str) -> None:
    r = client.post("/api/auth/magic-link", json={"email": email})
    token = parse_qs(urlparse(r.json()["dev_magic_link"]).query)["token"][0]
    client.get("/api/auth/verify", params={"token": token})


async def _set_user(email: str, **fields) -> None:
    sets = ", ".join(f"{k}=?" for k in fields)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        await db.execute(f"UPDATE users SET {sets} WHERE email=?", (*fields.values(), email))
        await db.commit()


async def _uid(email: str) -> int:
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall("SELECT internal_id FROM users WHERE email=?", (email,))
        return rows[0][0]


# ── TC-V1-ENT-01 — every protected GET is 401 without a session ────────────────
def test_protected_endpoints_401_without_cookie():
    with TestClient(app) as client:
        for path in _AUTH_GETS:
            assert client.get(path).status_code == 401, f"{path} should require auth"


# ── TC-V1-ENT-02 — every admin endpoint is 403 for a non-admin ─────────────────
def test_admin_endpoints_403_for_non_admin():
    with TestClient(app) as client:
        _login(client, "ent_plain@example.com")
        for path in _ADMIN_GETS:
            assert client.get(path).status_code == 403, f"{path} must be admin-gated"
        # A couple of admin mutations too.
        assert client.post("/api/admin/coupons",
                           json={"code": "x", "discount_type": "percent", "percent_off": 5}
                           ).status_code == 403
        assert client.post("/api/admin/broadcasts",
                           json={"title": "t", "body": "b", "audience": "all"}).status_code == 403


# ── TC-V1-ENT-03 — plan matrix resolves documented breadth (and only breadth) ──
@pytest.mark.asyncio
async def test_plan_entitlement_matrix():
    from backend.migrations.run_migrations import apply_migrations
    await apply_migrations(cfg.DATABASE_URL)
    expected = {
        "free":  {"coins_per_scan": 2,  "chart_layers": "ema200_only", "scans_per_day": 1},
        "basic": {"coins_per_scan": 5,  "chart_layers": "full",        "scans_per_day": 0},
        "pro":   {"coins_per_scan": 10, "chart_layers": "full",        "scans_per_day": 0},
    }
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        for tier, exp in expected.items():
            ent = await resolve_entitlements(db, tier)
            for k, v in exp.items():
                assert ent[k] == v, f"{tier}.{k} = {ent[k]} != {v}"
            # RED LINE: entitlements buy breadth only — never a score/threshold/verdict knob.
            assert set(ent) == {"tier", "coins_per_scan", "chart_layers", "scans_per_day"}
            assert "threshold" not in ent and "score" not in ent and "gate" not in ent


# ── TC-V1-ENT-04 — coin limit + daily cap enforced server-side ─────────────────
def test_scan_gating_enforced():
    def payload(n):
        return {"coins_scanned": n, "coins_passed": 0, "threshold": 85,
                "coins": [{"coin": f"C{i}USDT", "direction": "long", "score": None,
                           "passed_threshold": 0} for i in range(n)]}
    with TestClient(app) as client:
        _login(client, "ent_scan@example.com")
        over = client.post("/api/scan/events", json=payload(3))  # free = 2 coins
        assert over.status_code == 403 and over.json()["detail"]["code"] == "PLAN_COIN_LIMIT"
        assert client.post("/api/scan/events", json=payload(2)).status_code == 200  # first ok
        cap = client.post("/api/scan/events", json=payload(1))  # free = 1 scan/day
        assert cap.status_code == 429 and cap.json()["detail"]["code"] == "DAILY_SCAN_LIMIT"


# ── TC-V1-ENT-05 — subscription state machine: entitled states + legal moves ───
def test_state_machine_laws():
    # Non-entitled states collapse a paid plan value to Free.
    assert bs.effective_tier("none", "pro") == "free"
    assert bs.effective_tier("expired", "pro") == "free"
    # Entitled states keep the paid breadth.
    for st in ("trial", "active", "past_due", "cancelled"):
        assert bs.effective_tier(st, "pro") == "pro"
        assert bs.is_entitled(st) is True
    assert bs.is_entitled("none") is False and bs.is_entitled("expired") is False
    # A few legal / illegal transitions from the D-B4 matrix.
    assert bs.can_transition("none", "trial") and bs.can_transition("active", "expired")
    assert not bs.can_transition("none", "expired")
    assert not bs.can_transition("expired", "past_due")
    with pytest.raises(bs.IllegalTransition):
        bs.assert_transition("none", "past_due")


# ── TC-V1-ENT-06 — academy dual-gate: plan gate + trial=Pro access ─────────────
@pytest.mark.asyncio
async def test_academy_plan_gate_and_trial_access():
    with TestClient(app) as client:
        # Free user is locked out of a 'full'-tier lesson (content withheld, 403).
        _login(client, "ent_acad_free@example.com")
        await _set_user("ent_acad_free@example.com", tier="free", subscription_status="none")
        locked = client.get("/api/academy/smart_skip")
        assert locked.status_code == 403
        assert "body" not in locked.text and "video" not in locked.text.lower()
        # A trial user gets Pro-level access to the same lesson.
        _login(client, "ent_acad_trial@example.com")
        await _set_user("ent_acad_trial@example.com", tier="free", subscription_status="trial")
        assert client.get("/api/academy/smart_skip").status_code == 200


# ── TC-V1-ENT-09 — a SUSPENDED account cannot use protected endpoints ──────────
@pytest.mark.asyncio
async def test_suspended_account_is_blocked():
    """Admin 'suspend' sets suspended_at + active=0. A suspended session must lose access
    to protected endpoints — otherwise the moderation control is a silent no-op."""
    email = "ent_suspended@example.com"
    with TestClient(app) as user, TestClient(app) as admin:
        _login(user, email)
        assert user.get("/api/scan/entitlements").status_code == 200  # baseline access
        uid = await _uid(email)
        _login(admin, _ADMIN)
        assert admin.post(f"/api/admin/users/{uid}/override",
                          json={"action": "suspend", "value": "", "note": "abuse"}
                          ).status_code == 200
        # The suspended user's EXISTING session must stop passing.
        r = user.get("/api/scan/entitlements")
        assert r.status_code in (401, 403), (
            "SUSPENDED account still has access — suspend is a no-op (entitlement gap)")
