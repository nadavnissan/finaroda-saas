"""Migration 009 — academy / VOD (YouTube embeds; audit 013/014/016/030 consolidated).

Learning library: bundles → episodes (YouTube unlisted), view tracking, task uploads.
default_tier vocabulary aligned to FINARODA plans (free/basic/advanced/pro).
"""
import aiosqlite

MIGRATION_ID = "009_academy"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS academy_bundles (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL,
            description      TEXT,
            cover_image_url  TEXT,
            order_in_library INTEGER NOT NULL DEFAULT 0,
            default_tier     TEXT NOT NULL DEFAULT 'free'
                             CHECK (default_tier IN ('free','basic','advanced','pro')),
            created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at       DATETIME
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS academy_episodes (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            bundle_id         INTEGER NOT NULL REFERENCES academy_bundles(id) ON DELETE CASCADE,
            youtube_url       TEXT NOT NULL,
            youtube_id        TEXT NOT NULL,
            title             TEXT NOT NULL,
            description       TEXT,
            topic_tags        TEXT NOT NULL DEFAULT '[]',
            duration_seconds  INTEGER,
            order_in_bundle   INTEGER NOT NULL DEFAULT 0,
            is_premium        INTEGER NOT NULL DEFAULT 0,
            thumbnail_url     TEXT,
            transcript        TEXT,
            task_file_url     TEXT,
            task_description  TEXT,
            published_at      DATETIME,
            created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at        DATETIME
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS academy_episode_views (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(internal_id) ON DELETE CASCADE,
            episode_id      INTEGER NOT NULL REFERENCES academy_episodes(id) ON DELETE CASCADE,
            first_viewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_viewed_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            watch_count     INTEGER NOT NULL DEFAULT 1,
            UNIQUE (user_id, episode_id)
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS academy_task_uploads (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL REFERENCES users(internal_id) ON DELETE CASCADE,
            episode_id   INTEGER NOT NULL REFERENCES academy_episodes(id) ON DELETE CASCADE,
            file_url     TEXT NOT NULL,
            file_filename TEXT NOT NULL,
            uploaded_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status       TEXT NOT NULL DEFAULT 'pending_review'
                         CHECK (status IN ('pending_review','reviewed'))
        )
        """
    )
    await db.commit()
