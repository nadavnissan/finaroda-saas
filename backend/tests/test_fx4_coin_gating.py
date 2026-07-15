"""FX4 — per-plan coin-identity gating (TC-FX4-xx).

Server-authoritative: a scan of a MANAGED-universe coin outside the plan's allowlist is
rejected with 403 COIN_GATED. The founder seed (mig 037) is free=[LINK,AVAX],
basic=[LINK,AVAX,SOL,ADA,DOGE], pro=wildcard. Trial = Pro access. Symbols outside the
universe are out of scope for identity gating (count/daily gates still apply). Coin access
is BREADTH only — never a different verdict/score/threshold (RED LINE unchanged).
"""
from urllib.parse import parse_qs, urlparse

import aiosqlite
import pytest
from fastapi.testclient import TestClient

import backend.config as cfg
from backend.main import app


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


def _scan(*coins: str) -> dict:
    """A minimal one-momentum-row-per-coin scan payload."""
    rows = [
        {"coin": c, "direction": "long", "profile": "momentum", "score": None,
         "passed_threshold": 0}
        for c in coins
    ]
    return {"coins_scanned": len(coins), "coins_passed": 0, "threshold": 85, "coins": rows}


# ── TC-FX4-01 — free plan blocks a premium universe coin (BTC) ─────────────────
def test_free_blocks_premium_coin():
    with TestClient(app) as client:
        _login(client, "fx4_free_btc@example.com")
        r = client.post("/api/scan/events", json=_scan("BTCUSDT"))
        assert r.status_code == 403
        detail = r.json()["detail"]
        assert detail["code"] == "COIN_GATED"
        assert detail["blocked"] == ["BTC"]
        assert detail["plan"] == "free"


# ── TC-FX4-02 — free plan allows an allowlisted coin (LINK) ────────────────────
def test_free_allows_allowlisted_coin():
    with TestClient(app) as client:
        _login(client, "fx4_free_link@example.com")
        r = client.post("/api/scan/events", json=_scan("LINKUSDT"))
        assert r.status_code == 200


# ── TC-FX4-03 — non-universe (synthetic) symbols are NOT identity-gated ────────
def test_non_universe_symbol_passes_identity_gate():
    """A symbol outside the managed universe is out of scope for identity gating; the
    count/daily gates still apply. Guards the count-gate law's orthogonality."""
    with TestClient(app) as client:
        _login(client, "fx4_synth@example.com")
        r = client.post("/api/scan/events", json=_scan("C0USDT"))
        assert r.status_code == 200


# ── TC-FX4-04 — basic plan matrix (SOL allowed, BTC blocked) ───────────────────
@pytest.mark.asyncio
async def test_basic_plan_matrix():
    with TestClient(app) as client:
        _login(client, "fx4_basic@example.com")
        await _set_user("fx4_basic@example.com", tier="basic")
        assert client.post("/api/scan/events", json=_scan("SOLUSDT")).status_code == 200
        blocked = client.post("/api/scan/events", json=_scan("BTCUSDT"))
        assert blocked.status_code == 403
        assert blocked.json()["detail"]["code"] == "COIN_GATED"


# ── TC-FX4-05 — pro wildcard allows any universe coin ─────────────────────────
@pytest.mark.asyncio
async def test_pro_wildcard_allows_any_coin():
    with TestClient(app) as client:
        _login(client, "fx4_pro@example.com")
        await _set_user("fx4_pro@example.com", tier="pro")
        assert client.post("/api/scan/events", json=_scan("BTCUSDT")).status_code == 200


# ── TC-FX4-06 — trial = Pro coin access ───────────────────────────────────────
@pytest.mark.asyncio
async def test_trial_gets_pro_coin_access():
    with TestClient(app) as client:
        _login(client, "fx4_trial@example.com")
        await _set_user("fx4_trial@example.com", tier="free", subscription_status="trial")
        assert client.post("/api/scan/events", json=_scan("BTCUSDT")).status_code == 200


# ── TC-FX4-07 — coin-access endpoint (free): locked map names the unlock plan ──
def test_coin_access_endpoint_free():
    with TestClient(app) as client:
        _login(client, "fx4_access_free@example.com")
        r = client.get("/api/scan/coin-access")
        assert r.status_code == 200
        body = r.json()
        assert body["plan"] == "free"
        assert set(body["coins"]) == {"LINK", "AVAX"}
        assert body["wildcard"] is False
        assert len(body["universe"]) == 10
        # BTC is a Pro coin (only the wildcard includes it); SOL unlocks at Basic.
        assert body["locked"]["BTC"] == "Pro"
        assert body["locked"]["SOL"] == "Basic"
        assert "LINK" not in body["locked"]


# ── TC-FX4-08 — coin-access endpoint (pro): wildcard, nothing locked ──────────
@pytest.mark.asyncio
async def test_coin_access_endpoint_pro():
    with TestClient(app) as client:
        _login(client, "fx4_access_pro@example.com")
        await _set_user("fx4_access_pro@example.com", tier="pro")
        body = client.get("/api/scan/coin-access").json()
        assert body["wildcard"] is True
        assert body["locked"] == {}


# ── TC-FX4-09 — history renders a now-gated coin (gating is new-scans only) ────
@pytest.mark.asyncio
async def test_history_unaffected_by_gating():
    """A stored scan of a coin that is now gated for the plan still renders in history —
    gating applies to NEW scans only (A5). Simulated by inserting the rows directly."""
    email = "fx4_history@example.com"
    with TestClient(app) as client:
        _login(client, email)
        uid = await _uid(email)
        async with aiosqlite.connect(cfg.DATABASE_URL) as db:
            cur = await db.execute(
                "INSERT INTO scan_events (user_id, coins_scanned, coins_passed, threshold) "
                "VALUES (?, 1, 1, 85)",
                (uid,),
            )
            sid = cur.lastrowid
            await db.execute(
                "INSERT INTO score_log (scan_event_id, user_id, coin, direction, profile, "
                "score, passed_threshold, price) VALUES (?, ?, 'BTCUSDT', 'long', 'momentum', "
                "86, 1, 60000)",
                (sid, uid),
            )
            await db.commit()
        stored = client.get(f"/api/scan/history/{sid}")
        assert stored.status_code == 200
        assert stored.json()["rows"][0]["coin"] == "BTCUSDT"


_ADMIN = "rodanis@gmail.com"  # ADMIN_BOOTSTRAP_EMAILS default -> is_admin=1


# ── TC-FX4-10 — admin coin-access endpoints are admin-gated (403 for others) ──
def test_admin_coin_access_requires_admin():
    with TestClient(app) as client:
        _login(client, "fx4_notadmin@example.com")
        assert client.get("/api/admin/coin-access").status_code == 403
        assert client.put("/api/admin/coin-access/free",
                          json={"coins": ["BTC"], "wildcard": False}).status_code == 403


# ── TC-FX4-11 — admin edit takes effect without a restart (read per request) ──
@pytest.mark.asyncio
async def test_admin_edit_takes_effect_live():
    """Admin adds SOL to the free allowlist; a free user's scan of SOL then succeeds in the
    same process (no deploy). The change is audited to admin_events."""
    with TestClient(app) as admin, TestClient(app) as user:
        _login(user, "fx4_live@example.com")
        # Before: SOL is gated on free.
        assert user.post("/api/scan/events", json=_scan("SOLUSDT")).status_code == 403

        _login(admin, _ADMIN)
        r = admin.put("/api/admin/coin-access/free",
                      json={"coins": ["LINK", "AVAX", "SOL"], "wildcard": False,
                            "note": "add SOL to free"})
        assert r.status_code == 200 and set(r.json()["coins"]) == {"LINK", "AVAX", "SOL"}

        # After: the same free user can now scan SOL, no restart.
        assert user.post("/api/scan/events", json=_scan("SOLUSDT")).status_code == 200

        # Audited.
        async with aiosqlite.connect(cfg.DATABASE_URL) as db:
            rows = await db.execute_fetchall(
                "SELECT COUNT(*) FROM admin_events WHERE event_type='coin_access_update'")
        assert rows[0][0] >= 1

        # Restore the founder seed so later tests see the default free allowlist.
        assert admin.put("/api/admin/coin-access/free",
                         json={"coins": ["LINK", "AVAX"], "wildcard": False}).status_code == 200


# ── TC-FX4-12 — admin cannot add a coin outside the managed universe ──────────
def test_admin_rejects_non_universe_coin():
    with TestClient(app) as admin:
        _login(admin, _ADMIN)
        r = admin.put("/api/admin/coin-access/basic",
                      json={"coins": ["LINK", "NOTACOIN"], "wildcard": False})
        assert r.status_code == 400
