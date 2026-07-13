"""Migration 031 — Stage 5: in-app notification feed + per-user notification prefs.

Distinct from `notifications_log` (mig 028), which is the system-send idempotency /
admin-audit ledger. This adds the USER-FACING pieces the bell reads:

  notifications       one row per bell item (newest-first feed). read_at nullable;
                      opening the bell panel stamps read_at on the visible rows.
                      Server-authoritative unread count (survives refresh).
  notification_prefs  cross-device prefs (D-N2): in-app on/off, sound, vibration,
                      product-email opt, broadcast-email opt (one-click unsub).

Also adds `teaser_sent_at` to journal_scenarios — the reveal-teaser sent-flag on the
reveal row (D-N5), so the teaser sweep is deduped per reveal and idempotent (a second
run sends zero). The teaser NEVER carries an outcome value; it only says a reveal is
waiting (pull-only red line).
"""
import aiosqlite

MIGRATION_ID = "031_notifications_prefs"


async def up(db: aiosqlite.Connection) -> None:
    # --- reconcile the dead legacy `notifications` outbox (mig 005) -----------
    # mig 005 created a `notifications` scheduled-outbox table that no application
    # code ever reads or writes (verified: the app uses notifications_log + broadcasts).
    # It collides with the D-N1 bell-feed name. Rename it aside (non-destructive:
    # preserves any rows) so the bell feed can own `notifications`. Idempotent: the
    # rename only runs while the old schema (no read_at column) is present.
    ncols = {r[1] for r in await db.execute_fetchall("PRAGMA table_info(notifications)")}
    if ncols and "read_at" not in ncols:
        await db.execute("DROP INDEX IF EXISTS idx_notif_scheduled")
        await db.execute("ALTER TABLE notifications RENAME TO notifications_legacy_outbox")

    # --- user-facing bell feed -----------------------------------------------
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(internal_id),
            type        TEXT NOT NULL,          -- trial_reminder|reveal_teaser|broadcast
            title       TEXT NOT NULL,
            body        TEXT NOT NULL,
            link_path   TEXT,                   -- in-app deep link, e.g. '/journal'
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            read_at     DATETIME                -- nullable; set when the bell shows it
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_notifications_user_read "
        "ON notifications(user_id, read_at)"
    )

    # --- per-user notification preferences (cross-device, DB not localStorage) -
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_prefs (
            user_id            INTEGER PRIMARY KEY REFERENCES users(internal_id),
            inapp_enabled      INTEGER NOT NULL DEFAULT 1,
            sound_enabled      INTEGER NOT NULL DEFAULT 1,
            vibration_enabled  INTEGER NOT NULL DEFAULT 1,
            email_product      INTEGER NOT NULL DEFAULT 1,  -- day-11 + reveal-teaser
            email_broadcast    INTEGER NOT NULL DEFAULT 1,  -- one-click unsub mandatory
            updated_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --- reveal-teaser sent-flag on the reveal row (D-N5 dedup) ---------------
    cols = {
        r[1]
        for r in await db.execute_fetchall("PRAGMA table_info(journal_scenarios)")
    }
    if "teaser_sent_at" not in cols:
        await db.execute(
            "ALTER TABLE journal_scenarios ADD COLUMN teaser_sent_at DATETIME"
        )

    await db.commit()
