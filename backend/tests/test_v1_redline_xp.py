"""RED-LINE SUITE — XP economy (ATP V1, TC-V1-XP-xx).

XP_ECONOMY.md v1.0 (locked) as law:
  - Closed source list ONLY: onboarding(+300 once), daily_first_scan(+50 once/day),
    academy_lesson(+100 once/lesson), journal_reveal_viewed(+25 once/scenario),
    admin_grant(variable, admin-only, not user-earnable).
  - NO spend path. XP is never a currency; it is never deducted, consumed or deleted.
  - NO new source outside the list. Forbidden forever: profit/outcome, scan count,
    streaks, invite-for-XP.
  - Every event is server-authoritative + idempotent per (user, source, ref).

This suite adds two things the per-feature tests do not: a STATIC guard over the whole
backend that proves (a) the only files that write xp_events are the five known award
sites and (b) no code path mutates or deletes an xp_events row (no spend), plus a
consolidated runtime assertion of the exact locked amounts and the rank ladder.
"""
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import aiosqlite
import pytest
from fastapi.testclient import TestClient

import backend.config as cfg
from backend.core.ranks import rank_for
from backend.main import app

BACKEND = Path(__file__).resolve().parents[1]
_ADMIN = "rodanis@gmail.com"

ALLOWED_SOURCES = {"onboarding", "daily_first_scan", "academy_lesson",
                   "journal_reveal_viewed", "admin_grant"}
LOCKED_AMOUNTS = {"onboarding": 300, "daily_first_scan": 50,
                  "academy_lesson": 100, "journal_reveal_viewed": 25}
# The only source files permitted to INSERT into xp_events (award sites).
KNOWN_WRITERS = {"api/onboarding.py", "api/scan.py", "api/academy.py",
                 "api/journal.py", "api/admin.py"}


def _login(client: TestClient, email: str) -> None:
    r = client.post("/api/auth/magic-link", json={"email": email})
    token = parse_qs(urlparse(r.json()["dev_magic_link"]).query)["token"][0]
    client.get("/api/auth/verify", params={"token": token})


async def _uid(email: str) -> int:
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall("SELECT internal_id FROM users WHERE email=?", (email,))
        return rows[0][0]


def _iter_backend_py():
    for p in BACKEND.rglob("*.py"):
        rel = p.relative_to(BACKEND).as_posix()
        if rel.startswith(("tests/", "migrations/")) or "__pycache__" in rel:
            continue
        yield rel, p.read_text(encoding="utf-8")


# ── TC-V1-XP-01 — STATIC: only the five known sites write xp_events ────────────
def test_only_known_files_write_xp_events():
    writers = set()
    for rel, text in _iter_backend_py():
        for line in text.splitlines():
            up = line.upper()
            if "INTO XP_EVENTS" in up and "INSERT" in up:
                writers.add(rel)
    assert writers == KNOWN_WRITERS, (
        f"unexpected xp_events writer(s): {writers ^ KNOWN_WRITERS}. A new writer means a "
        f"potential new XP source — update XP_ECONOMY.md and this guard deliberately.")


# ── TC-V1-XP-02 — STATIC: no spend path (no UPDATE/DELETE of xp_events) ─────────
def test_no_xp_spend_or_mutation_path():
    offenders = []
    for rel, text in _iter_backend_py():
        for i, line in enumerate(text.splitlines(), 1):
            up = line.upper()
            if "XP_EVENTS" in up and ("DELETE FROM XP_EVENTS" in up or "UPDATE XP_EVENTS" in up):
                offenders.append(f"{rel}:{i}")
    assert not offenders, f"XP is append-only; found mutation/spend path: {offenders}"


# ── TC-V1-XP-03 — award constants are the locked POSITIVE amounts ──────────────
def test_award_constants_are_locked_positives():
    """Each fixed XP source awards exactly its locked, positive amount. A drift here (or a
    sign flip) would be a covert re-pricing or spend of the non-currency."""
    from backend.api import academy, onboarding, scan
    from backend.core import journal
    assert scan.DAILY_FIRST_SCAN_XP == 50
    assert academy.ACADEMY_LESSON_XP == 100
    assert journal.JOURNAL_VIEW_XP == 25
    assert onboarding.ONBOARDING_TOTAL == 300
    for amt in (scan.DAILY_FIRST_SCAN_XP, academy.ACADEMY_LESSON_XP,
                journal.JOURNAL_VIEW_XP, onboarding.ONBOARDING_TOTAL):
        assert amt > 0
    # And no award site inserts a negated amount variable (covert deduction).
    for rel in KNOWN_WRITERS:
        assert "amount=-" not in (BACKEND / rel).read_text(encoding="utf-8").replace(" ", "")


# ── TC-V1-XP-04 — schema: composite unique + onboarding partial index ──────────
@pytest.mark.asyncio
async def test_xp_events_idempotency_schema():
    from backend.migrations.run_migrations import apply_migrations
    await apply_migrations(cfg.DATABASE_URL)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        idx = await db.execute_fetchall("PRAGMA index_list(xp_events)")
        names = {r[1] for r in idx}
        assert "ux_xp_onboarding_once" in names
        # The composite unique (user_id, source, ref) backs per-source idempotency.
        found_composite = False
        for r in idx:
            cols = await db.execute_fetchall(f"PRAGMA index_info({r[1]})")
            colnames = [c[2] for c in cols]
            if colnames == ["user_id", "source", "ref"]:
                found_composite = True
        assert found_composite, "missing UNIQUE(user_id, source, ref) on xp_events"


# ── TC-V1-XP-05 — runtime: distinct sources stay within the closed list ────────
@pytest.mark.asyncio
async def test_closed_source_list_and_exact_amounts():
    with TestClient(app) as client:
        email = "xp_closed@example.com"
        _login(client, email)
        # onboarding +300
        assert client.post("/api/onboarding/complete").status_code == 200
        # daily_first_scan +50 (first scan of day)
        scan = client.post("/api/scan/events", json={
            "coins_scanned": 1, "coins_passed": 0, "threshold": 85,
            "coins": [{"coin": "LINKUSDT", "direction": "long", "score": None,
                       "passed_threshold": 0}]}).json()
        assert scan["xp_awarded"] == 50
        # academy_lesson +100 (a real basic lesson)
        assert client.post("/api/academy/regime_ema200/complete").json()["xp_awarded"] == 100
        # admin_grant (variable, admin-only)
        uid = await _uid(email)
        _login(client, _ADMIN)
        client.post(f"/api/admin/users/{uid}/override",
                    json={"action": "grant_xp", "value": "70", "note": "goodwill"})

    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall(
            "SELECT source, amount FROM xp_events WHERE user_id=?", (uid,))
    got = {src for src, _ in rows}
    assert got <= ALLOWED_SOURCES, f"source outside the closed list: {got - ALLOWED_SOURCES}"
    by_source = {src: amt for src, amt in rows}
    for src, amt in LOCKED_AMOUNTS.items():
        if src in by_source:
            assert by_source[src] == amt, f"{src} amount drifted: {by_source[src]} != {amt}"
    assert by_source.get("admin_grant") == 70


# ── TC-V1-XP-06 — global invariant: every xp_events row is in the closed list ──
@pytest.mark.asyncio
async def test_global_sources_all_in_closed_list():
    """Across the entire shared test DB (all suites' writes), no row exists whose source
    is outside the locked list — a live guard against any stray award path."""
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall("SELECT DISTINCT source FROM xp_events")
    seen = {r[0] for r in rows}
    assert seen <= ALLOWED_SOURCES, f"stray XP source(s) in DB: {seen - ALLOWED_SOURCES}"


# ── TC-V1-XP-07 — rank ladder thresholds are the locked 0/1000/3000/8000 ───────
def test_rank_ladder_thresholds():
    assert rank_for(0)["name"] == "Strategy Apprentice"
    assert rank_for(999)["level"] == 1
    assert rank_for(1000)["name"] == "Risk Manager"
    assert rank_for(2999)["level"] == 2
    assert rank_for(3000)["name"] == "Regime Reader"
    assert rank_for(8000)["name"] == "Master Strategist"
    assert rank_for(999999)["level"] == 4
