"""Stage 5 — in-app notifications, prefs, real-Resend flows, cron, unsubscribe.

DEV email mode (no RESEND_API_KEY) → zero network calls (AC8). The reveal-teaser body
assertion is the pull-only red line: no outcome value may leave the server in an email.
"""
from urllib.parse import parse_qs, urlparse

import aiosqlite
import pytest
from fastapi.testclient import TestClient

import backend.config as cfg
from backend.app.tasks.billing_tasks import trial_ending_soon_task
from backend.app.tasks.journal_tasks import journal_reveal_teasers_task
from backend.core import notifications as notif
from backend.core.email import render_reveal_teaser, render_trial_reminder
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


def _register(client: TestClient, email: str) -> None:
    """Create a user by logging in once (magic-link signup)."""
    _login(client, email)


async def _make_trial(email: str, days: float, hours: float = 0) -> None:
    """Put a user on trial with trial_ends_at = now + days + hours (computed in Python
    to avoid SQLite multi-modifier composition pitfalls)."""
    from datetime import datetime, timedelta, timezone

    ends = (datetime.now(timezone.utc) + timedelta(days=days, hours=hours)).isoformat()
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        await db.execute(
            "UPDATE users SET subscription_status='trial', trial_ends_at=? WHERE email=?",
            (ends, email),
        )
        await db.commit()


# ── notifications feed CRUD + read-marking (AC1) ─────────────────────────────
@pytest.mark.asyncio
async def test_notifications_feed_and_read_marking():
    email = "notif_feed@example.com"
    with TestClient(app) as client:
        _register(client, email)
        uid = await _user_id(email)
        async with aiosqlite.connect(cfg.DATABASE_URL) as db:
            await notif.create_notification(db, uid, "broadcast", "Hello", "World", "/dashboard")

        r = client.get("/api/notifications")
        assert r.status_code == 200
        data = r.json()
        assert data["unread_count"] == 1
        assert data["notifications"][0]["title"] == "Hello"
        assert data["notifications"][0]["read_at"] is None
        nid = data["notifications"][0]["id"]

        r2 = client.post("/api/notifications/read", json={"ids": [nid]})
        assert r2.json()["unread_count"] == 0

        # Survives refresh (server state).
        r3 = client.get("/api/notifications")
        assert r3.json()["unread_count"] == 0
        assert r3.json()["notifications"][0]["read_at"] is not None


@pytest.mark.asyncio
async def test_read_all_when_ids_omitted():
    email = "notif_readall@example.com"
    with TestClient(app) as client:
        _register(client, email)
        uid = await _user_id(email)
        async with aiosqlite.connect(cfg.DATABASE_URL) as db:
            for i in range(3):
                await notif.create_notification(db, uid, "broadcast", f"n{i}", "b", None)
        assert client.get("/api/notifications").json()["unread_count"] == 3
        assert client.post("/api/notifications/read", json={}).json()["unread_count"] == 0


# ── prefs CRUD (AC2) + inapp gate (AC3) ──────────────────────────────────────
@pytest.mark.asyncio
async def test_prefs_crud_defaults_and_update():
    email = "notif_prefs@example.com"
    with TestClient(app) as client:
        _register(client, email)
        r = client.get("/api/notifications/prefs")
        assert r.json() == {
            "inapp_enabled": True, "sound_enabled": True, "vibration_enabled": True,
            "email_product": True, "email_broadcast": True,
        }
        r2 = client.put("/api/notifications/prefs", json={"sound_enabled": False})
        assert r2.json()["sound_enabled"] is False
        assert r2.json()["vibration_enabled"] is True  # untouched
        assert client.get("/api/notifications/prefs").json()["sound_enabled"] is False


@pytest.mark.asyncio
async def test_inapp_disabled_suppresses_bell_rows():
    email = "notif_inappoff@example.com"
    with TestClient(app) as client:
        _register(client, email)
        client.put("/api/notifications/prefs", json={"inapp_enabled": False})
        uid = await _user_id(email)
        async with aiosqlite.connect(cfg.DATABASE_URL) as db:
            nid = await notif.create_notification(db, uid, "broadcast", "x", "y", None)
        assert nid is None
        assert client.get("/api/notifications").json()["unread_count"] == 0


# ── day-11 boundary (AC4) ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_day11_boundary_only_fires_at_three_days_left():
    with TestClient(app) as client:
        _register(client, "d10@example.com")   # 4 days left → excluded
        _register(client, "d11@example.com")   # 3 days left → fires
        _register(client, "d12@example.com")   # 2 days left → excluded
    await _make_trial("d10@example.com", 4, 1)
    await _make_trial("d11@example.com", 3, 1)
    await _make_trial("d12@example.com", 2)

    result = await trial_ending_soon_task()
    assert result["notified"] == 1

    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            "SELECT u.email FROM notifications_log n JOIN users u ON u.internal_id=n.user_id "
            "WHERE n.notif_type='trial_reminder_day11'"
        )
        emails = {r["email"] for r in rows}
    assert "d11@example.com" in emails
    assert "d10@example.com" not in emails
    assert "d12@example.com" not in emails


@pytest.mark.asyncio
async def test_day11_cron_idempotent_second_run_zero():
    email = "d11_idem@example.com"
    with TestClient(app) as client:
        _register(client, email)
    await _make_trial(email, 3, 2)

    first = await trial_ending_soon_task()
    second = await trial_ending_soon_task()
    assert first["notified"] == 1
    assert second["notified"] == 0

    # And the user has exactly one trial_reminder bell row.
    uid = await _user_id(email)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND type='trial_reminder'", (uid,)
        )
    assert rows[0][0] == 1


@pytest.mark.asyncio
async def test_day11_respects_email_product_optout_but_still_logs():
    email = "d11_noemail@example.com"
    with TestClient(app) as client:
        _register(client, email)
        client.put("/api/notifications/prefs", json={"email_product": False})
    await _make_trial(email, 3, 1)
    # Opted out of product email, but the in-app reminder + audit log still happen.
    result = await trial_ending_soon_task()
    assert result["notified"] == 1
    uid = await _user_id(email)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND type='trial_reminder'", (uid,)
        )
    assert rows[0][0] == 1


# ── reveal-teaser: no outcome values, deduped (AC5) ──────────────────────────
def test_reveal_teaser_body_contains_no_outcome():
    subject, html, text = render_reveal_teaser("Nadav")
    # Assert on the human-readable copy (subject + text). The HTML wrapper carries CSS
    # (border-radius etc.) that would false-positive substring checks; the red line is
    # that no OUTCOME VALUE reaches the reader, which lives in the copy.
    blob = (subject + " " + text).lower()
    for forbidden in ("win", "loss", "profit", "gain", "target", "r-multiple", "%", "$"):
        assert forbidden not in blob, f"outcome token leaked: {forbidden!r}"
    assert "next scan" in blob
    # The fixed pull-only copy (D-N5) — no outcome value can appear because the copy
    # is a constant that never interpolates any scenario field.
    assert "a journal reveal is waiting" in blob
    assert "run your next scan to unlock it" in blob


async def _insert_resolved_scenario(email: str, status: str = "win", r: float = 2.6) -> int:
    uid = await _user_id(email)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        cur = await db.execute(
            """INSERT INTO journal_scenarios
               (user_id, scenario_type, scan_date, coin, direction, entry, sl, tp,
                status, r_result, resolved_at)
               VALUES (?, 'pass', '2026-07-01', 'BTCUSDT', 'short', 100, 110, 74,
                       ?, ?, CURRENT_TIMESTAMP)""",
            (uid, status, r),
        )
        await db.commit()
        return cur.lastrowid


@pytest.mark.asyncio
async def test_reveal_teaser_sweep_deduped_and_content_free():
    # User-scoped assertions: the sweep is a GLOBAL job, so other tests' scenarios may
    # also be teased in the same session DB. We verify dedup + content for THIS user.
    email = "teaser@example.com"
    with TestClient(app) as client:
        _register(client, email)
    sid = await _insert_resolved_scenario(email)
    uid = await _user_id(email)

    async def my_teaser_rows():
        async with aiosqlite.connect(cfg.DATABASE_URL) as db:
            db.row_factory = aiosqlite.Row
            return await db.execute_fetchall(
                "SELECT title, body FROM notifications WHERE user_id=? AND type='reveal_teaser'", (uid,))

    await journal_reveal_teasers_task()
    rows_after_first = await my_teaser_rows()
    assert len(rows_after_first) == 1  # one teaser for this user's pending reveal

    # Idempotent: a second sweep adds nothing for this user (teaser_sent_at is set).
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        r = await db.execute_fetchall(
            "SELECT teaser_sent_at FROM journal_scenarios WHERE id=?", (sid,))
    assert r[0][0] is not None
    await journal_reveal_teasers_task()
    assert len(await my_teaser_rows()) == 1

    blob = (rows_after_first[0]["title"] + rows_after_first[0]["body"]).lower()
    assert "win" not in blob and "2.6" not in blob and "%" not in blob


# ── broadcast: 403 + recipient filtering + unsubscribe link (AC6) ────────────
@pytest.mark.asyncio
async def test_broadcast_requires_admin():
    email = "notadmin@example.com"
    with TestClient(app) as client:
        _register(client, email)
        r = client.post("/api/admin/broadcasts", json={"title": "T", "body": "B", "audience": "all"})
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_broadcast_recipient_filtering_excludes_email_optout():
    a, b = "bcast_a@example.com", "bcast_b@example.com"
    with TestClient(app) as client:
        _register(client, a)
        _register(client, b)
    await _set_user(a, tier="pro")
    await _set_user(b, tier="pro")
    # b opts out of broadcast email.
    with TestClient(app) as client:
        _login(client, b)
        client.put("/api/notifications/prefs", json={"email_broadcast": False})

    from backend.api.admin import _broadcast_recipients
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        all_emails = {r["email"] for r in await _broadcast_recipients(db, "plan", "pro", False)}
        optin_emails = {r["email"] for r in await _broadcast_recipients(db, "plan", "pro", True)}
    assert a in all_emails and b in all_emails
    assert a in optin_emails
    assert b not in optin_emails  # excluded from email fan-out


@pytest.mark.asyncio
async def test_broadcast_send_counts_and_preview_delta():
    admin_email = "bcast_admin@example.com"
    u1, u2 = "bcast_basic1@example.com", "bcast_basic2@example.com"
    with TestClient(app) as client:
        _register(client, admin_email)
        _register(client, u1)
        _register(client, u2)
    await _set_user(admin_email, is_admin=1)
    await _set_user(u1, tier="basic")
    await _set_user(u2, tier="basic")

    with TestClient(app) as admin:
        _login(admin, admin_email)
        pre = admin.get("/api/admin/broadcasts/preview", params={"audience": "plan", "target_tier": "basic"}).json()
        assert pre["email_optin"] == pre["recipients"] >= 2

        # Opt one out, preview email_optin drops by one, audience size unchanged.
        with TestClient(app) as c2:
            _login(c2, u2)
            c2.put("/api/notifications/prefs", json={"email_broadcast": False})
        post = admin.get("/api/admin/broadcasts/preview", params={"audience": "plan", "target_tier": "basic"}).json()
        assert post["recipients"] == pre["recipients"]
        assert post["email_optin"] == pre["email_optin"] - 1

        # Send both channels; delivered_email matches opted-in count.
        r = admin.post("/api/admin/broadcasts", json={
            "title": "News", "body": "Line one\nLine two",
            "audience": "plan", "target_tier": "basic",
            "channel_in_app": True, "channel_email": True,
        })
        body = r.json()
        assert body["ok"] is True
        assert body["delivered_email"] == post["email_optin"]

    # Opted-out user still gets an in-app bell row (channel_in_app), just no email.
    uid2 = await _user_id(u2)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND type='broadcast'", (uid2,))
    assert rows[0][0] == 1


# ── unsubscribe token: valid / tampered / repeat (AC7) ───────────────────────
@pytest.mark.asyncio
async def test_unsubscribe_valid_tampered_repeat():
    email = "unsub@example.com"
    with TestClient(app) as client:
        _register(client, email)
        uid = await _user_id(email)
        token = notif.make_unsubscribe_token(uid, "email_broadcast")

        # Tampered token → rejected (400), no state change.
        bad = client.get("/api/email/unsubscribe", params={"token": token + "x"})
        assert bad.status_code == 400

        # Valid token flips the flag off, no login needed.
        ok = client.get("/api/email/unsubscribe", params={"token": token})
        assert ok.status_code == 200
        async with aiosqlite.connect(cfg.DATABASE_URL) as db:
            rows = await db.execute_fetchall(
                "SELECT email_broadcast FROM notification_prefs WHERE user_id=?", (uid,))
        assert rows[0][0] == 0

        # Idempotent: repeat is still 200, still off.
        again = client.get("/api/email/unsubscribe", params={"token": token})
        assert again.status_code == 200
        async with aiosqlite.connect(cfg.DATABASE_URL) as db:
            rows = await db.execute_fetchall(
                "SELECT email_broadcast FROM notification_prefs WHERE user_id=?", (uid,))
        assert rows[0][0] == 0


# ── cron endpoint auth (D-N9) ────────────────────────────────────────────────
def test_cron_requires_secret():
    with TestClient(app) as client:
        assert client.post("/api/cron/notifications").status_code == 403
        assert client.post("/api/cron/notifications",
                           headers={"X-Cron-Secret": "wrong"}).status_code == 403
        r = client.post("/api/cron/notifications",
                        headers={"X-Cron-Secret": cfg.CRON_SECRET})
        assert r.status_code == 200
        assert "trial_reminder" in r.json() and "reveal_teaser" in r.json()


def test_trial_reminder_email_render_no_emdash():
    subject, html, text = render_trial_reminder("Nadav", 3)
    assert "—" not in (subject + html + text)  # em-dash lint (D-N10)
    assert "no automatic charge" in text.lower()
