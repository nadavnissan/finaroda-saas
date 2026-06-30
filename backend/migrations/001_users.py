"""Migration 001 — users (clean schema, internal_id key).

Single-generation schema. No telegram_id, no career columns (cv/pitch/journey).
Auth + billing + referral + FINARODA-specific columns folded into one table.
Resolves the legacy db.py vs migrations `users` collision in favour of the modern row.
"""
import aiosqlite

MIGRATION_ID = "001_users"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            internal_id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email                  TEXT UNIQUE,
            email_verified_at      DATETIME,
            name                   TEXT,
            first_name             TEXT,
            last_name              TEXT,
            phone                  TEXT,

            -- ── Auth ──────────────────────────────────────────────────────
            auth_provider          TEXT NOT NULL DEFAULT 'email'
                                   CHECK (auth_provider IN ('email','google','apple')),
            magic_link_token       TEXT,
            magic_link_expires_at  DATETIME,
            is_admin               INTEGER NOT NULL DEFAULT 0,  -- SPEC §4: DB role (not env list)

            -- ── Billing / subscription (Cardcom v11) ──────────────────────
            tier                   TEXT NOT NULL DEFAULT 'free'
                                   CHECK (tier IN ('free','basic','advanced','pro')),
            subscription_status    TEXT NOT NULL DEFAULT 'none'
                                   CHECK (subscription_status IN
                                          ('none','trial','active','cancelled','past_due','expired')),
            trial_started_at       DATETIME,
            trial_ends_at          DATETIME,
            subscription_started_at DATETIME,
            subscription_paid_until DATETIME,
            cardcom_token          TEXT,
            last_payment_at        DATETIME,
            next_billing_at        DATETIME,
            subscription_cancelled_pending_at DATETIME,
            suspended_at           DATETIME,

            -- ── Referral (REST, monetary discount — not tokens; SPEC §3.2/§9) ─
            referral_code          TEXT UNIQUE,
            referred_by_user_id    INTEGER REFERENCES users(internal_id),
            discount_code_used     TEXT,

            -- ── FINARODA-specific (SPEC §3.2 ADAPT) ───────────────────────
            default_threshold      REAL,        -- per-user scan score threshold override
            last_scan_at           DATETIME,

            -- ── Lifecycle ─────────────────────────────────────────────────
            onboarding_completed_at DATETIME,
            last_login_at          DATETIME,
            active                 INTEGER NOT NULL DEFAULT 1,
            created_at             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_status, tier)"
    )
    await db.commit()
