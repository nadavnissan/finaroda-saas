"""Academy 2.0 (Stage 6) — DB-backed lessons, dual gating (plan x rank), server-authoritative
gated content, video admin CRUD, archive/restore, migration completion-preservation.

The B6 behavior tests (12 modules, +100 once, stub=0, free 403 on a full lesson) live in
test_pkg_b_phase2.py and must stay green; this file adds the 2.0 surface.
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
    sets = ", ".join(f"{k} = ?" for k in fields)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        await db.execute(f"UPDATE users SET {sets} WHERE email = ?", (*fields.values(), email))
        await db.commit()


async def _user_id(email: str) -> int:
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall("SELECT internal_id FROM users WHERE email = ?", (email,))
        return rows[0][0]


async def _grant_xp(email: str, amount: int, ref: str) -> None:
    uid = await _user_id(email)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        await db.execute(
            "INSERT OR IGNORE INTO xp_events (user_id, source, ref, amount) VALUES (?, 'admin_grant', ?, ?)",
            (uid, ref, amount),
        )
        await db.commit()


async def _delete_lessons(*ids: int) -> None:
    """Remove test-created lessons so the shared DB returns to the 12-lesson seed set
    (keeps the B6 count==12 test green). xp_events rows are left intact."""
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        for i in ids:
            await db.execute("DELETE FROM academy_lessons WHERE id = ?", (i,))
        await db.commit()


# ── Migration / seed integrity ───────────────────────────────────────────────
def test_seed_has_twelve_lessons_and_backward_compat_shape():
    with TestClient(app) as client:
        _login(client, "acad_v2_seed@example.com")
        data = client.get("/api/academy").json()
        assert len(data["modules"]) == 12
        m = data["modules"][0]
        # Backward-compat aliases the B6 client relied on + the new 2.0 fields.
        for key in ("id", "slug", "title", "minutes", "duration_minutes", "content_type",
                    "description", "tags", "min_plan", "min_rank", "unlocked", "completed"):
            assert key in m, f"missing {key}"
        assert m["id"] == m["slug"]
        assert m["minutes"] == m["duration_minutes"]


@pytest.mark.asyncio
async def test_migration_preserves_prior_completion_by_slug():
    """A completion recorded under the OLD module id (== new slug) still reads as completed —
    the rebuild never orphans an xp_events row (S3 / AC7)."""
    email = "acad_v2_preserve@example.com"
    with TestClient(app) as client:
        _login(client, email)
        # Simulate a pre-existing B6 completion written directly to xp_events.
        uid = await _user_id(email)
        async with aiosqlite.connect(cfg.DATABASE_URL) as db:
            await db.execute(
                "INSERT OR IGNORE INTO xp_events (user_id, source, ref, amount) "
                "VALUES (?, 'academy_lesson', 'regime_ema200', 100)", (uid,))
            await db.commit()
        data = client.get("/api/academy").json()
        lesson = next(m for m in data["modules"] if m["slug"] == "regime_ema200")
        assert lesson["completed"] is True
        # Replaying complete awards nothing (idempotent, no double XP).
        again = client.post("/api/academy/regime_ema200/complete").json()
        assert again["xp_awarded"] == 0


# ── Dual gating matrix (plan x rank x lock state) ────────────────────────────
@pytest.mark.asyncio
async def test_gating_matrix_plan_and_rank():
    email = "acad_v2_gate@example.com"
    with TestClient(app) as client:
        _login(client, email)
        await _set_user(email, tier="free", subscription_status="none")

        data = client.get("/api/academy").json()["modules"]
        by = {m["slug"]: m for m in data}

        # free plan lesson, no rank gate -> unlocked for a free user.
        assert by["regime_ema200"]["unlocked"] is True
        assert by["regime_ema200"]["lock_reason"] is None
        # basic-plan lesson -> locked for free, plain-language plan reason.
        assert by["smart_skip"]["unlocked"] is False
        assert by["smart_skip"]["lock_reason"] == "Available on Basic plan"
        # rank-gated bonus (spike_anatomy min_rank 1000) -> locked, rank reason first.
        assert by["spike_anatomy"]["unlocked"] is False
        assert by["spike_anatomy"]["lock_reason"] == "Unlocks at Risk Manager"

        # Upgrade to basic: plan gate clears, rank gate still holds on the bonus.
        await _set_user(email, tier="basic")
        by = {m["slug"]: m for m in client.get("/api/academy").json()["modules"]}
        assert by["smart_skip"]["unlocked"] is True
        assert by["spike_anatomy"]["unlocked"] is False  # still needs 1000 XP

        # Grant 1000 XP: the rank gate clears too (STATUS-based, not spent).
        await _grant_xp(email, 1000, "rank_boost")
        by = {m["slug"]: m for m in client.get("/api/academy").json()["modules"]}
        assert by["spike_anatomy"]["unlocked"] is True


@pytest.mark.asyncio
async def test_trial_gets_full_library():
    email = "acad_v2_trial@example.com"
    with TestClient(app) as client:
        _login(client, email)
        await _set_user(email, tier="free", subscription_status="trial")
        by = {m["slug"]: m for m in client.get("/api/academy").json()["modules"]}
        assert by["smart_skip"]["unlocked"] is True  # trial == Pro-level plan access


# ── Server-authoritative gated content (D-AC7) ───────────────────────────────
@pytest.mark.asyncio
async def test_locked_lesson_content_is_403_and_withheld():
    email = "acad_v2_content@example.com"
    with TestClient(app) as client:
        _login(client, email)
        await _set_user(email, tier="free", subscription_status="none")
        # Unlocked lesson: full content served.
        ok = client.get("/api/academy/regime_ema200")
        assert ok.status_code == 200
        assert "body" in ok.json()
        # Locked lesson: 403, and NO body/video anywhere in the payload.
        locked = client.get("/api/academy/smart_skip")
        assert locked.status_code == 403
        assert "body" not in locked.text and "video_url" not in locked.text


# ── Completion XP uniqueness ─────────────────────────────────────────────────
def test_completion_awards_once_only():
    with TestClient(app) as client:
        _login(client, "acad_v2_complete@example.com")
        first = client.post("/api/academy/ema7_timing/complete").json()
        assert first == {"xp_awarded": 100, "completed": True}
        again = client.post("/api/academy/ema7_timing/complete").json()
        assert again["xp_awarded"] == 0


def test_seed_stub_lesson_awards_nothing():
    with TestClient(app) as client:
        _login(client, "acad_v2_stub@example.com")
        r = client.post("/api/academy/volume_basics/complete").json()  # awards_xp=0 seed stub
        assert r == {"xp_awarded": 0, "completed": False}


# ── Admin auth on every mutation endpoint ────────────────────────────────────
def test_admin_academy_requires_admin():
    with TestClient(app) as client:
        _login(client, "acad_v2_plain@example.com")
        assert client.get("/api/admin/academy/lessons").status_code == 403
        assert client.post("/api/admin/academy/lessons", json={"title": "x"}).status_code == 403
        assert client.put("/api/admin/academy/lessons/1", json={"title": "x"}).status_code == 403
        assert client.post("/api/admin/academy/lessons/1/archive").status_code == 403
        assert client.post("/api/admin/academy/lessons/1/restore").status_code == 403
        assert client.post("/api/admin/academy/lessons/reorder", json={"ordered_ids": []}).status_code == 403


# ── Admin CRUD + video validation + archive/restore ──────────────────────────
@pytest.mark.asyncio
async def test_admin_create_video_lesson_and_invalid_url_rejected():
    email = "acad_v2_admin@example.com"
    with TestClient(app) as client:
        _login(client, email)
        await _set_user(email, is_admin=1)

        # A valid YouTube URL is accepted and normalized to an embed URL.
        good = client.post("/api/admin/academy/lessons", json={
            "title": "How to read a card", "content_type": "video",
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "min_plan": "free", "min_rank": 0,
        })
        assert good.status_code == 200
        assert good.json()["video_url"] == "https://www.youtube.com/embed/dQw4w9WgXcQ"

        # An invalid / non-YouTube-Vimeo URL is rejected with a clear error.
        bad = client.post("/api/admin/academy/lessons", json={
            "title": "Broken", "content_type": "video", "video_url": "https://example.com/x",
        })
        assert bad.status_code == 400
        assert bad.json()["detail"]["code"] == "INVALID_VIDEO_URL"
        await _delete_lessons(good.json()["id"])


@pytest.mark.asyncio
async def test_admin_archive_hides_from_users_and_restore_returns_it():
    email = "acad_v2_arch@example.com"
    with TestClient(app) as client:
        _login(client, email)
        await _set_user(email, is_admin=1)

        created = client.post("/api/admin/academy/lessons", json={
            "title": "Temporary lesson", "content_type": "text", "body": "hi", "min_plan": "free"}).json()
        lid = created["id"]

        # Visible to a user before archive.
        slugs = {m["slug"] for m in client.get("/api/academy").json()["modules"]}
        assert created["slug"] in slugs

        client.post(f"/api/admin/academy/lessons/{lid}/archive")
        slugs = {m["slug"] for m in client.get("/api/academy").json()["modules"]}
        assert created["slug"] not in slugs  # hidden from the user library
        # Still present in admin (archived flag).
        admin_rows = client.get("/api/admin/academy/lessons").json()
        assert any(r["id"] == lid and r["archived"] for r in admin_rows)

        client.post(f"/api/admin/academy/lessons/{lid}/restore")
        slugs = {m["slug"] for m in client.get("/api/academy").json()["modules"]}
        assert created["slug"] in slugs
        await _delete_lessons(lid)


@pytest.mark.asyncio
async def test_admin_archived_lesson_completion_xp_never_revoked():
    """D-AC6: archiving never revokes XP a user already earned."""
    admin_email = "acad_v2_arch_admin@example.com"
    user_email = "acad_v2_arch_user@example.com"
    with TestClient(app) as client:
        _login(client, user_email)
        _login(client, admin_email)
        await _set_user(admin_email, is_admin=1)
        created = client.post("/api/admin/academy/lessons", json={
            "title": "Earnable lesson", "content_type": "text", "body": "x",
            "min_plan": "free", "awards_xp": True}).json()
        lid, slug = created["id"], created["slug"]

        # User completes it (+100), then admin archives it.
        client_u = TestClient(app)
        _login(client_u, user_email)
        assert client_u.post(f"/api/academy/{slug}/complete").json()["xp_awarded"] == 100
        client.post(f"/api/admin/academy/lessons/{lid}/archive")

        # The xp_events row survives (XP not revoked).
        uid = await _user_id(user_email)
        async with aiosqlite.connect(cfg.DATABASE_URL) as db:
            rows = await db.execute_fetchall(
                "SELECT amount FROM xp_events WHERE user_id=? AND source='academy_lesson' AND ref=?",
                (uid, slug))
        assert rows and rows[0][0] == 100
        await _delete_lessons(lid)


@pytest.mark.asyncio
async def test_admin_reorder_sets_sort_index():
    email = "acad_v2_reorder@example.com"
    with TestClient(app) as client:
        _login(client, email)
        await _set_user(email, is_admin=1)
        rows = client.get("/api/admin/academy/lessons").json()
        ids = [r["id"] for r in rows]
        reversed_ids = list(reversed(ids))
        out = client.post("/api/admin/academy/lessons/reorder", json={"ordered_ids": reversed_ids}).json()
        assert [r["id"] for r in out] == reversed_ids
        # Restore the original seed order so the shared DB stays deterministic.
        client.post("/api/admin/academy/lessons/reorder", json={"ordered_ids": ids})
