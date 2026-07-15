"""RED-LINE SUITE — Reveal-gating (ATP V1, TC-V1-RVL-xx).

Constitution (CLAUDE.md §8.4, F3, D-A7): a journal/scenario outcome computed
server-side (status / r_result / resolved_at) must NEVER be serialized into any
client-facing payload until the user's own next scan reveals it. This suite tests
that law across every serialization surface the reveal-map identified:

  - GET /api/journal (primary)            - the outcome value never appears in the blob
  - GET /api/journal/badge                - bare count, never content
  - POST /api/journal/scenarios/{id}/view - 409 while unrevealed
  - GET /api/scan/history/{id}            - stored rows carry setup geometry, no outcome
  - POST /api/scan/events response        - no outcome fields
  - support ticket breadcrumbs            - sanitizer strips outcome-shaped keys (belt-and-suspenders)
  - admin ticket detail                   - persisted breadcrumbs never carry an outcome
  - email renderers                       - teaser/reminder copy is content-free

These extend (do not duplicate) test_pkg_b_phase2.py: here we sweep ALL four
resolved statuses and assert the raw serialized text is clean, and we exercise the
ticket write->admin-read round trip end to end.
"""
from urllib.parse import parse_qs, urlparse

import aiosqlite
import pytest
from fastapi.testclient import TestClient

import backend.config as cfg
from backend.core import email as email_mod
from backend.core.breadcrumbs import (
    _ALLOWED_KEYS,
    _MAX_ITEMS,
    _MAX_STR,
    sanitize_breadcrumbs,
)
from backend.main import app

_ADMIN = "rodanis@gmail.com"  # ADMIN_BOOTSTRAP_EMAILS default -> is_admin=1

# Outcome-shaped tokens that must never surface in a client payload.
_FORBIDDEN_KEYS = ("status", "r_result", "resolved_at", "outcome", "pnl")


def _login(client: TestClient, email: str) -> None:
    r = client.post("/api/auth/magic-link", json={"email": email})
    token = parse_qs(urlparse(r.json()["dev_magic_link"]).query)["token"][0]
    client.get("/api/auth/verify", params={"token": token})


async def _uid(email: str) -> int:
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall("SELECT internal_id FROM users WHERE email=?", (email,))
        return rows[0][0]


async def _set_tier(email: str, tier: str) -> None:
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        await db.execute("UPDATE users SET tier=? WHERE email=?", (tier, email))
        await db.commit()


async def _resolve_latest_pass(email: str, status: str, r: float) -> int:
    uid = await _uid(email)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall(
            "SELECT id FROM journal_scenarios WHERE user_id=? AND scenario_type='pass' "
            "AND status='open' ORDER BY id DESC LIMIT 1", (uid,))
        sid = rows[0][0]
        await db.execute(
            "UPDATE journal_scenarios SET status=?, r_result=?, resolved_at=CURRENT_TIMESTAMP "
            "WHERE id=?", (status, r, sid))
        await db.commit()
    return sid


def _pass_scan(coin: str = "LINKUSDT") -> dict:
    return {"coins_scanned": 1, "coins_passed": 1, "threshold": 85, "coins": [
        {"coin": coin, "direction": "short", "profile": "momentum", "score": 86,
         "passed_threshold": 1, "entry": 100.0, "sl": 110.0, "tp": 74.0}]}


# ── TC-V1-RVL-01 — sanitizer: allowlist strips every outcome-shaped key ────────
def test_sanitizer_strips_outcome_keys():
    crumb = {
        "type": "click", "path": "/journal", "status_code": 200,  # allowed
        "status": "win", "r_result": 2.6, "outcome": "loss",       # forbidden
        "pnl": 500, "direction": "short", "entry": 100, "sl": 110, "tp": 74, "score": 86,
    }
    out = sanitize_breadcrumbs([crumb])
    assert out == [{"type": "click", "path": "/journal", "status_code": 200}]
    blob = str(out)
    for tok in ("win", "2.6", "loss", "short"):
        assert tok not in blob
    # Every surviving key is on the allowlist.
    assert set(out[0]) <= _ALLOWED_KEYS


# ── TC-V1-RVL-02 — sanitizer: caps, type-filtering, malformed input ────────────
def test_sanitizer_caps_and_malformed():
    assert sanitize_breadcrumbs("not-a-list") == []
    assert sanitize_breadcrumbs(None) == []
    assert sanitize_breadcrumbs([{"nope": 1}, "str", 5, None]) == []  # nothing allowlisted -> []
    # length cap on the number of crumbs
    many = [{"type": f"e{i}", "path": "/x"} for i in range(50)]
    assert len(sanitize_breadcrumbs(many)) == _MAX_ITEMS
    # per-string cap
    long = sanitize_breadcrumbs([{"type": "x" * 500}])
    assert len(long[0]["type"]) == _MAX_STR
    # dict/list values are dropped, primitives kept
    mixed = sanitize_breadcrumbs([{"type": "e", "label": {"x": 1}, "code": [1, 2], "status_code": 500}])
    assert mixed == [{"type": "e", "status_code": 500}]


# ── TC-V1-RVL-03 — journal withholds every resolved status, blob is clean ──────
@pytest.mark.asyncio
@pytest.mark.parametrize("status,r,leak_num", [
    ("win", 2.60, "2.6"), ("loss", -1.00, "-1.0"),
    ("save", 0.00, None), ("expired", 0.40, "0.4")])
async def test_journal_withholds_all_statuses(status, r, leak_num):
    email = f"rvl_{status}@example.com"
    with TestClient(app) as client:
        _login(client, email)
        client.post("/api/scan/events", json=_pass_scan("LINKUSDT"))
        await _resolve_latest_pass(email, status, r)  # resolved server-side, NOT revealed

        resp = client.get("/api/journal")
        assert resp.status_code == 200
        # The withheld status string never appears as a serialized value. (Quoted form so
        # the 'save' status can't false-match the legitimate 'capital_saves' stat key.)
        assert f'"{status}"' not in resp.text
        # And a distinctive withheld R value never leaks (0.0 is skipped — it collides with
        # the legitimate cumulative_r_revealed=0.0 stat, and r_result=None is asserted below).
        if leak_num is not None:
            assert leak_num not in resp.text
        body = resp.json()
        s = next(x for x in body["scenarios"] if x["type"] == "pass")
        assert s["revealed"] is False
        assert s.get("status") is None and s.get("r_result") is None and s.get("resolved_at") is None
        assert body["stats"]["cumulative_r_revealed"] == 0.0
        # Badge is a bare count.
        assert client.get("/api/journal/badge").json() == {"unrevealed": 1}
        # Cannot view an unrevealed outcome.
        assert client.post(f"/api/journal/scenarios/{s['id']}/view").status_code == 409


# ── TC-V1-RVL-04 — stored scan detail carries no outcome fields ────────────────
@pytest.mark.asyncio
async def test_scan_history_detail_has_no_outcome():
    email = "rvl_hist@example.com"
    with TestClient(app) as client:
        _login(client, email)
        ev = client.post("/api/scan/events", json=_pass_scan("LINKUSDT"))
        # The scan-event response itself carries no outcome.
        for k in _FORBIDDEN_KEYS:
            assert k not in ev.text or k == "status"  # 'status' substring may appear in unrelated keys
        await _resolve_latest_pass(email, "win", 2.60)  # resolve but do not reveal
        sid = client.get("/api/scan/history").json()["scans"][0]["scan_event_id"]
        stored = client.get(f"/api/scan/history/{sid}")
        row = stored.json()["rows"][0]
        # Stored rows are setup geometry only — never the resolved outcome.
        assert "r_result" not in row and "resolved_at" not in row and "outcome" not in row
        assert "2.6" not in stored.text and "win" not in stored.text


# ── TC-V1-RVL-05 — ticket breadcrumbs: write->admin-read never carries outcome ─
def test_ticket_breadcrumbs_roundtrip_clean():
    with TestClient(app) as client:
        _login(client, "rvl_ticket@example.com")
        # A malicious client trail that tries to smuggle an outcome value.
        r = client.post("/api/support/tickets", json={
            "subject": "stuck", "body": "hangs", "category": "bug",
            "breadcrumbs": [
                {"type": "scan_submit", "path": "/scan"},
                {"type": "reveal", "status": "win", "r_result": 2.6, "outcome": "loss"},
            ]})
        assert r.status_code == 200
        tid = r.json()["id"]

        _login(client, _ADMIN)
        detail = client.get(f"/api/admin/tickets/{tid}")
        assert detail.status_code == 200
        blob = detail.text
        # The outcome value smuggled via breadcrumbs never reaches the admin payload.
        assert "2.6" not in blob
        assert "\"status\": \"win\"" not in blob and "r_result" not in blob and "outcome" not in blob


# ── TC-V1-RVL-06 — email renderers are content-free (no outcome tokens) ────────
def test_email_renderers_content_free():
    # Outcome WORDS/numbers must not appear anywhere (subject/html/text). Currency symbols
    # (%, $) are checked only against the plain-text body — the HTML carries CSS units.
    words = ("win", "loss", "profit", "pnl", "2.6")
    subj, html, text = email_mod.render_reveal_teaser("Sam")
    blob = f"{subj}\n{html}\n{text}".lower()
    for tok in words:
        assert tok not in blob, f"reveal teaser leaked {tok!r}"
    for sym in ("%", "$"):
        assert sym not in f"{subj}\n{text}", f"reveal teaser text leaked {sym!r}"
    # Trial reminder is metadata-only too.
    subj2, html2, text2 = email_mod.render_trial_reminder("Sam", 2)
    blob2 = f"{subj2}\n{html2}\n{text2}".lower()
    for tok in ("win", "loss", "r_result", "outcome"):
        assert tok not in blob2
