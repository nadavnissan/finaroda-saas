"""Migration 005 — notifications (scheduled outbox) + consent_log (append-only).

From audit migration 001. consent_log is append-only (GDPR-style audit trail).
Resolves the legacy `user_consents` collision in favour of consent_log.
"""
import aiosqlite

MIGRATION_ID = "005_notifications_consent"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id           INTEGER NOT NULL REFERENCES users(internal_id),
            channel           TEXT NOT NULL,
            notification_type TEXT NOT NULL,
            payload           TEXT NOT NULL,
            scheduled_for     DATETIME NOT NULL,
            sent_at           DATETIME,
            delivered_at      DATETIME,
            opened_at         DATETIME,
            status            TEXT NOT NULL DEFAULT 'pending',
            error_message     TEXT
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_notif_scheduled ON notifications(status, scheduled_for)"
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS consent_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(internal_id),
            consent_type    TEXT NOT NULL,
            consent_version TEXT NOT NULL,
            granted         INTEGER NOT NULL,
            timestamp       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ip_address      TEXT,
            user_agent      TEXT
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_consent_user ON consent_log(user_id, timestamp DESC)"
    )
    await db.commit()
