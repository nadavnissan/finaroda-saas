"""Migration 028 — Package B phase 2 spine: journal scenarios (F3/B4), ticket
replies (B7c), notifications log (B7f), user settings (B5), broadcast audience (B7d).

B4 "What Would Have Happened" needs a first-class scenario record derived from the
scan journal (score_log). Phase 1 deferred this: scans persisted to score_log +
decision_snapshots only. Here we add:

  journal_scenarios  one row per PASS setup (from a momentum score_log row) + one
                     no_setups_day discipline record per skip day. WATCH is NEVER a
                     scenario (PRD F3 AC2). Outcomes are computed server-side by the
                     resolution job and WITHHELD from the client until a new scan
                     reveals them (reveal-gating, PRD F3 AC5 / ALIGNMENT B3):
                       status      open|win|loss|save|expired|skip (server-only)
                       r_result    hypothetical R, never money (F3 AC4)
                       resolved_at when the market resolved it (server clock)
                       revealed_at set on the user's NEXT scan (the reveal event)
                       viewed_at   set when the user opens the revealed row (+25 XP)

  ticket_replies     admin<->user thread on a support_tickets row (B7c).
  notifications_log  the two decided system sends only: day-11 trial reminder +
                     journal-reveal teaser (B7f). Broadcasts stay in admin_broadcasts.
  user_settings      remembered Analysis Lens / Risk Style / coin prefs (B5, F5) —
                     display & geometry only, NEVER what counts as an opportunity.

Also extends admin_broadcasts (mig 013) with the B7d audience model (all / by plan /
trial-ending) + channel flags, and seeds the two admin-editable settings shown in the
B7e frame (trial reminder day, free journal-history window).
"""
import aiosqlite

MIGRATION_ID = "028_journal_scenarios_admin"


async def up(db: aiosqlite.Connection) -> None:
    # --- B4: journal scenarios (reveal-gated) --------------------------------
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS journal_scenarios (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL REFERENCES users(internal_id),
            scan_event_id  INTEGER REFERENCES scan_events(id),
            score_log_id   INTEGER REFERENCES score_log(id),
            scenario_type  TEXT NOT NULL
                           CHECK (scenario_type IN ('pass','no_setups_day')),
            scan_date      TEXT NOT NULL,               -- YYYY-MM-DD (UTC scan day)
            coin           TEXT,                        -- NULL for no_setups_day
            direction      TEXT
                           CHECK (direction IS NULL OR direction IN ('long','short')),
            score          REAL,
            entry          REAL,
            sl             REAL,
            tp             REAL,
            trailing_pct   REAL,
            created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            -- server-side resolution (NEVER serialized to the client until revealed)
            status         TEXT NOT NULL DEFAULT 'open'
                           CHECK (status IN ('open','win','loss','save','expired','skip')),
            r_result       REAL,
            resolved_at    DATETIME,
            -- reveal-gating: outcome withheld until the user's NEXT scan reveals it
            revealed_at    DATETIME,
            viewed_at      DATETIME
        )
        """
    )
    # Idempotent backfill guards: one PASS scenario per momentum score_log row,
    # one no_setups_day record per user per calendar day.
    await db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_journal_pass "
        "ON journal_scenarios(score_log_id) WHERE scenario_type = 'pass'"
    )
    await db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_journal_noset "
        "ON journal_scenarios(user_id, scan_date) WHERE scenario_type = 'no_setups_day'"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_journal_user "
        "ON journal_scenarios(user_id, created_at DESC)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_journal_open "
        "ON journal_scenarios(status) WHERE status = 'open'"
    )

    # --- B7c: support ticket reply thread ------------------------------------
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS ticket_replies (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id  INTEGER NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
            author_id  INTEGER NOT NULL REFERENCES users(internal_id),
            is_admin   INTEGER NOT NULL DEFAULT 0,
            body       TEXT NOT NULL,
            email_sent INTEGER NOT NULL DEFAULT 0,   -- email fan-out is a logged stub
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_ticket_replies "
        "ON ticket_replies(ticket_id, created_at)"
    )

    # --- B7f: notifications log (the two decided system sends only) -----------
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER REFERENCES users(internal_id),
            notif_type  TEXT NOT NULL
                        CHECK (notif_type IN ('trial_reminder_day11','journal_reveal_teaser','broadcast')),
            channel     TEXT NOT NULL DEFAULT 'in_app'
                        CHECK (channel IN ('in_app','email','email_in_app')),
            ref         TEXT,                          -- idempotency key (e.g. trial:<user>:<date>)
            status      TEXT NOT NULL DEFAULT 'sent'
                        CHECK (status IN ('sent','delivered','failed','pending_open')),
            detail      TEXT,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (notif_type, ref)
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_notiflog_type "
        "ON notifications_log(notif_type, created_at DESC)"
    )

    # --- B5: remembered scan settings (display & geometry only, F5) ----------
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id        INTEGER PRIMARY KEY REFERENCES users(internal_id),
            call_sign      TEXT,                        -- identity from onboarding S9
            analysis_lens  TEXT NOT NULL DEFAULT 'full'
                           CHECK (analysis_lens IN ('ema200','rsi','volume','full')),
            risk_style     TEXT NOT NULL DEFAULT 'balanced'
                           CHECK (risk_style IN ('conservative','balanced','aggressive')),
            coin_prefs     TEXT NOT NULL DEFAULT '[]',   -- JSON array of preferred symbols
            palette        TEXT NOT NULL DEFAULT 'terminal',
            updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --- B7d: broadcast audience model + channel flags (extend mig 013) ------
    # SQLite: ADD COLUMN is safe & non-locking. Guard for re-run.
    # PRAGMA rows are plain tuples here (the migration runner sets no Row factory);
    # column name is index 1: (cid, name, type, notnull, dflt_value, pk).
    cols = {
        r[1]
        for r in await db.execute_fetchall("PRAGMA table_info(admin_broadcasts)")
    }
    if "audience" not in cols:
        await db.execute(
            "ALTER TABLE admin_broadcasts ADD COLUMN audience TEXT NOT NULL DEFAULT 'all' "
            "CHECK (audience IN ('all','plan','trial_ending'))"
        )
    if "channel_in_app" not in cols:
        await db.execute(
            "ALTER TABLE admin_broadcasts ADD COLUMN channel_in_app INTEGER NOT NULL DEFAULT 1"
        )
    if "channel_email" not in cols:
        await db.execute(
            "ALTER TABLE admin_broadcasts ADD COLUMN channel_email INTEGER NOT NULL DEFAULT 0"
        )

    # --- B7e: admin-editable settings shown in the Settings frame ------------
    seeds = [
        ("trial_reminder_day", "11", "int", "Trial reminder fires on this day (F7 · D1)"),
        ("journal_history_days_free", "7", "int", "Free-plan journal history window (F3 · F7)"),
    ]
    for key, value, vtype, desc in seeds:
        await db.execute(
            """INSERT OR IGNORE INTO system_settings (key, value, value_type, description)
               VALUES (?, ?, ?, ?)""",
            (key, value, vtype, desc),
        )

    await db.commit()
