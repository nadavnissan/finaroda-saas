"""Stage 7 — Admin v1.1 (columns/filters/CSV), churn survey, Sentry gating, breadcrumbs.

Red line under test: a ticket's breadcrumb trail can never carry a journal outcome value
(sanitizer allowlist). Sentry is disabled in tests (no DSN) → zero network.
"""
from urllib.parse import parse_qs, urlparse

import aiosqlite
import pytest
from fastapi.testclient import TestClient

import backend.config as cfg
from backend.core.breadcrumbs import sanitize_breadcrumbs
from backend.core.monitoring import init_sentry, scrub_event, sentry_enabled
from backend.core.ranks import rank_for
from backend.main import app


def _login(client: TestClient, email: str) -> None:
    r = client.post("/api/auth/magic-link", json={"email": email})
    token = parse_qs(urlparse(r.json()["dev_magic_link"]).query)["token"][0]
    client.get("/api/auth/verify", params={"token": token})


async def _set_user(email: str, **fields) -> None:
    sets = ", ".join(f"{k} = ?" for k in fields)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        await db.execute(f"UPDATE users SET {sets} WHERE email = ?", (*fields.values(), email))
        await db.commit()


async def _user_id(email: str) -> int:
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall("SELECT internal_id FROM users WHERE email = ?", (email,))
        return rows[0][0]


async def _add_scan(email: str, days_ago: int) -> None:
    uid = await _user_id(email)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        await db.execute(
            "INSERT INTO scan_events (user_id, scanned_at, coins_scanned, coins_passed) "
            "VALUES (?, datetime('now', ?), 2, 0)",
            (uid, f"-{days_ago} days"),
        )
        await db.commit()


def _admin_client(email: str) -> TestClient:
    c = TestClient(app)
    _login(c, email)
    return c


# ── rank ladder mirror ────────────────────────────────────────────────────────
def test_rank_for_matches_ladder():
    assert rank_for(0)["level"] == 1
    assert rank_for(999)["level"] == 1
    assert rank_for(1000)["level"] == 2
    assert rank_for(3000)["level"] == 3
    assert rank_for(8000)["level"] == 4 and rank_for(50000)["name"] == "Master Strategist"


# ── D-A3 filters: server-side, AND semantics ─────────────────────────────────
@pytest.mark.asyncio
async def test_user_filters_and_semantics():
    a, b, c = "s7a@example.com", "s7b@example.com", "s7c@example.com"
    with TestClient(app) as client:
        for e in (a, b, c):
            _login(client, e)
    await _set_user(a, tier="pro", subscription_status="active")
    await _set_user(b, tier="free", subscription_status="trial")
    await _set_user(c, tier="basic", subscription_status="expired")
    for _ in range(10):
        await _add_scan(c, 1)

    admin_email = "s7admin@example.com"
    with TestClient(app) as adm:
        _login(adm, admin_email)
    await _set_user(admin_email, is_admin=1)

    with _admin_client(admin_email) as adm:
        def emails(params):
            r = adm.get("/api/admin/users", params=params)
            assert r.status_code == 200
            return {u["email"] for u in r.json()["users"]}

        assert a in emails({"plan": "pro"}) and b not in emails({"plan": "pro"})
        assert b in emails({"status": "trial"}) and a not in emails({"status": "trial"})
        assert c in emails({"min_scans": 6}) and a not in emails({"min_scans": 6})
        # AND: pro AND min_scans>=6 → none of ours (A is pro but 0 scans)
        combined = emails({"plan": "pro", "min_scans": 6})
        assert a not in combined and c not in combined
        # combined plan+status
        assert emails({"plan": "basic", "status": "expired"}) >= {c}


@pytest.mark.asyncio
async def test_user_row_has_all_columns_and_rank():
    email = "s7cols@example.com"
    with TestClient(app) as client:
        _login(client, email)
    await _set_user(email, tier="pro")
    admin_email = "s7admin2@example.com"
    with TestClient(app) as adm:
        _login(adm, admin_email)
    await _set_user(admin_email, is_admin=1)
    with _admin_client(admin_email) as adm:
        row = next(u for u in adm.get("/api/admin/users").json()["users"] if u["email"] == email)
    for key in ("signup_at", "last_active", "xp", "rank_level", "rank_name", "scans_total",
                "scans_week", "active_days_7d", "active_days_30d", "referrals", "churn_survey"):
        assert key in row
    assert row["referrals"] == 0  # placeholder (Stage 4 blocked)


# ── D-A1/AC4: active-days boundary + never user-facing ────────────────────────
@pytest.mark.asyncio
async def test_active_days_boundary():
    email = "s7active@example.com"
    with TestClient(app) as client:
        _login(client, email)
    admin_email = "s7admin3@example.com"
    with TestClient(app) as adm:
        _login(adm, admin_email)
    await _set_user(admin_email, is_admin=1)

    # Distinct days: today, -3, -6 (inside 7d window), -7 and -10 (outside 7d, inside 30d).
    for d in (0, 3, 6, 7, 10):
        await _add_scan(email, d)

    with _admin_client(admin_email) as adm:
        row = next(u for u in adm.get("/api/admin/users").json()["users"] if u["email"] == email)
    assert row["active_days_7d"] == 3   # today, -3, -6
    assert row["active_days_30d"] == 5  # all five distinct days
    assert row["scans_total"] == 5


def test_active_days_never_in_user_facing_profile():
    """AC4: the metric must not leak into any user-facing route payload."""
    email = "s7leak@example.com"
    with TestClient(app) as client:
        _login(client, email)
        prof = client.get("/api/profile").json()
    blob = str(prof).lower()
    assert "active_days" not in blob and "active_day" not in blob


# ── CSV export (D-A4 / AC3) ───────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_csv_export_auth_and_content_match():
    a, b = "s7csv_a@example.com", "s7csv_b@example.com"
    with TestClient(app) as client:
        _login(client, a)
        _login(client, b)
    await _set_user(a, tier="pro")
    await _set_user(b, tier="pro")
    admin_email = "s7csvadmin@example.com"
    with TestClient(app) as adm:
        _login(adm, admin_email)
    await _set_user(admin_email, is_admin=1)

    # Non-admin → 403.
    with TestClient(app) as nonadmin:
        _login(nonadmin, a)
        assert nonadmin.get("/api/admin/users/export.csv").status_code == 403

    with _admin_client(admin_email) as adm:
        json_emails = {u["email"] for u in adm.get("/api/admin/users", params={"plan": "pro"}).json()["users"]}
        r = adm.get("/api/admin/users/export.csv", params={"plan": "pro"})
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "attachment" in r.headers.get("content-disposition", "")
        lines = [ln for ln in r.text.splitlines() if ln.strip()]
        header = lines[0]
        assert "email" in header and "active_days_7d" in header and "rank_name" in header
        csv_emails = {ln.split(",")[1] for ln in lines[1:]}
        # CSV filtered view matches the JSON filtered view exactly.
        assert csv_emails == json_emails
        assert a in csv_emails and b in csv_emails


# ── Churn survey (D-A5 / AC5) ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_churn_survey_capture_and_admin_view():
    email = "s7churn@example.com"
    with TestClient(app) as client:
        _login(client, email)
        r = client.post("/api/churn/survey", json={
            "reason_category": "too_expensive",
            "reason_free_text": "price",
            "would_return": True,
        })
        assert r.status_code == 200 and r.json()["ok"] is True

    admin_email = "s7churnadmin@example.com"
    with TestClient(app) as adm:
        _login(adm, admin_email)
    await _set_user(admin_email, is_admin=1)

    with _admin_client(admin_email) as adm:
        # Appears in admin churn list.
        responses = adm.get("/api/admin/churn").json()["responses"]
        assert any(x["email"] == email and x["reason_category"] == "too_expensive" for x in responses)
        # Flag set on the user row + churned filter includes them.
        row = next(u for u in adm.get("/api/admin/users").json()["users"] if u["email"] == email)
        assert row["churn_survey"] is True
        churned = {u["email"] for u in adm.get("/api/admin/users", params={"status": "churned"}).json()["users"]}
        assert email in churned


def test_churn_survey_requires_auth():
    with TestClient(app) as client:
        assert client.post("/api/churn/survey", json={"reason_category": "x"}).status_code == 401


# ── Sentry gating + PII scrub (D-A6 / AC6) ───────────────────────────────────
def test_sentry_disabled_in_test_zero_network():
    assert sentry_enabled() is False   # no DSN in test env
    assert init_sentry() is False      # never initializes → no network


def test_scrub_event_removes_pii():
    event = {
        "user": {"id": 5, "email": "x@y.com", "ip_address": "1.2.3.4", "username": "bob"},
        "request": {
            "cookies": {"access_token": "secret"},
            "headers": {"Cookie": "c", "Authorization": "Bearer t", "User-Agent": "ua"},
        },
        "email": "leak@z.com",
    }
    out = scrub_event(event)
    assert out["user"] == {"id": 5}
    assert "cookies" not in out["request"]
    assert "Cookie" not in out["request"]["headers"] and "Authorization" not in out["request"]["headers"]
    assert out["request"]["headers"]["User-Agent"] == "ua"
    assert "email" not in out


# ── Breadcrumbs red line (D-A7 / AC7 / S2) ───────────────────────────────────
def test_sanitize_breadcrumbs_strips_outcome_values():
    raw = [
        {"event_type": "scan_submit", "path": "/scan", "r_result": 2.6, "status": "win", "coin": "BTC"},
        {"type": "route_change", "route": "/dashboard"},
        "not-a-dict",
        {"nested": {"x": 1}},        # only disallowed keys → dropped
        {"event_type": "api_error", "code": 500},
    ]
    out = sanitize_breadcrumbs(raw)
    blob = str(out).lower()
    for forbidden in ("r_result", "status", "win", "coin", "nested"):
        assert forbidden not in blob
    assert out[0] == {"event_type": "scan_submit", "path": "/scan"}
    assert {"type": "route_change", "route": "/dashboard"} in out
    assert {"event_type": "api_error", "code": 500} in out


def test_sanitize_breadcrumbs_caps_length():
    raw = [{"event_type": f"e{i}", "path": "/x"} for i in range(50)]
    assert len(sanitize_breadcrumbs(raw)) == 20


@pytest.mark.asyncio
async def test_ticket_breadcrumbs_stored_and_rendered_without_outcomes():
    email = "s7ticket@example.com"
    with TestClient(app) as client:
        _login(client, email)
        # A malicious client tries to smuggle an outcome value into a breadcrumb.
        client.post("/api/support/tickets", json={
            "subject": "help", "body": "broken", "category": "bug",
            "breadcrumbs": [
                {"event_type": "scan_submit", "path": "/scan", "r_result": 3.1, "status": "loss"},
                {"type": "notif_open"},
            ],
        })

    admin_email = "s7ticketadmin@example.com"
    with TestClient(app) as adm:
        _login(adm, admin_email)
    await _set_user(admin_email, is_admin=1)

    with _admin_client(admin_email) as adm:
        tickets = adm.get("/api/admin/tickets").json()["tickets"]
        tid = next(t["id"] for t in tickets if t["email"] == email)
        detail = adm.get(f"/api/admin/tickets/{tid}").json()
        crumbs = detail["ticket"]["breadcrumbs"]
        assert len(crumbs) == 2
        blob = str(crumbs).lower()
        assert "r_result" not in blob and "status" not in blob and "loss" not in blob
        assert crumbs[0] == {"event_type": "scan_submit", "path": "/scan"}


def test_admin_ticket_endpoints_403_for_non_admin():
    email = "s7nonadmin@example.com"
    with TestClient(app) as client:
        _login(client, email)
        assert client.get("/api/admin/tickets").status_code == 403
        assert client.get("/api/admin/churn").status_code == 403
        assert client.get("/api/admin/users/export.csv").status_code == 403
