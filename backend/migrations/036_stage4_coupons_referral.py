"""Migration 036 — Stage 4: coupons + referral, redesigned Stripe-native.

Reshapes the dormant, superseded models (mig 003 coupons/coupon_applications, mig 004
referrals) into the Stripe-native Stage-4 schema and adds the referral banked-credit
ledger. The three legacy tables were confirmed EMPTY and dormant (no live reads/writes;
STOP S3 does not trigger), so each reshape copies any rows it finds (non-destructive) and
is safe to re-apply.

1. coupons              — REBUILT into a Stripe mirror row: stripe_coupon_id +
                          stripe_promotion_code_id, discount_type (percent|fixed),
                          percent_off / amount_off_agorot, duration ('once' = first charge
                          only, D-S1), plan_restriction, max_redemptions, redeemed_count,
                          expires_at, active. Legacy discount_pct/max_uses/uses_count/
                          is_active are carried over where they map.
2. coupon_applications  — REBUILT + RENAMED to coupon_redemptions: a redemption ledger
                          synced from webhooks (coupon_id, user_id, promotion_code,
                          transaction_id, amount_discounted_agorot). UNIQUE(coupon_id,
                          user_id) preserved.
3. referrals            — REBUILT into the binding + reward model (D-S6/D-S7): permanent
                          per-user code, referred bound once (UNIQUE referred_id), status
                          bound|rewarded|void, reward_type balance_credit|banked,
                          reward_amount_agorot, stripe_balance_transaction_id.
4. referral_credits     — NEW. Banked credit for trial/free referrers (D-S5): resolved to
                          one month of the plan they later buy; status banked|applied|void.
5. subscription_events  — CHECK rebuilt (SQLite cannot ALTER a CHECK) to allow the Stage-4
                          audit event types (referral reward/credit/void, coupon redeemed,
                          zero-amount invoice → no tax document, D-S8).

Money stays agorot ints (D-B10). No XP is touched anywhere (D / AC8).
"""
import aiosqlite

MIGRATION_ID = "036_stage4_coupons_referral"


async def _cols(db: aiosqlite.Connection, table: str) -> list[str]:
    return [r[1] for r in await db.execute_fetchall(f"PRAGMA table_info({table})")]


async def _table_exists(db: aiosqlite.Connection, table: str) -> bool:
    rows = await db.execute_fetchall(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return bool(rows)


async def up(db: aiosqlite.Connection) -> None:
    # FK enforcement is ON at the connection; rebuild parent (coupons) before its child
    # (coupon_redemptions) and drop children before parents. All legacy tables are empty.

    # ── 1. coupons: reshape into the Stripe mirror ────────────────────────────
    if "discount_type" not in await _cols(db, "coupons"):
        await db.execute(
            """
            CREATE TABLE coupons_new (
                id                        INTEGER PRIMARY KEY AUTOINCREMENT,
                code                      TEXT UNIQUE NOT NULL,       -- promotion code string
                stripe_coupon_id          TEXT,                       -- Stripe Coupon id
                stripe_promotion_code_id  TEXT,                       -- Stripe Promotion Code id
                discount_type             TEXT NOT NULL DEFAULT 'percent'
                                          CHECK (discount_type IN ('percent','fixed')),
                percent_off               INTEGER CHECK (percent_off IS NULL OR
                                                         (percent_off > 0 AND percent_off <= 100)),
                amount_off_agorot         INTEGER CHECK (amount_off_agorot IS NULL OR
                                                         amount_off_agorot > 0),
                duration                  TEXT NOT NULL DEFAULT 'once',  -- first charge only
                plan_restriction          TEXT CHECK (plan_restriction IS NULL OR
                                                      plan_restriction IN ('basic','pro')),
                max_redemptions           INTEGER,                    -- NULL = unlimited
                redeemed_count            INTEGER NOT NULL DEFAULT 0,
                expires_at                DATETIME,
                active                    INTEGER NOT NULL DEFAULT 1,
                description               TEXT,
                created_by                INTEGER REFERENCES users(internal_id),
                created_at                DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Carry legacy rows over where columns map (none exist today; safe if any do).
        legacy = await _cols(db, "coupons")
        if {"discount_pct", "max_uses", "uses_count", "is_active"} <= set(legacy):
            await db.execute(
                """INSERT INTO coupons_new
                       (id, code, discount_type, percent_off, duration, max_redemptions,
                        redeemed_count, expires_at, active, description, created_by, created_at)
                   SELECT id, code, 'percent', discount_pct, 'once', max_uses,
                          uses_count, expires_at, is_active, description, created_by, created_at
                     FROM coupons"""
            )
        await db.execute("DROP TABLE IF EXISTS coupon_applications")  # child, rebuilt below
        await db.execute("DROP TABLE coupons")
        await db.execute("ALTER TABLE coupons_new RENAME TO coupons")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_coupons_code ON coupons(code)")

    # ── 2. coupon_redemptions: redemption ledger (from coupon_applications) ────
    if not await _table_exists(db, "coupon_redemptions"):
        await db.execute(
            """
            CREATE TABLE coupon_redemptions (
                id                         INTEGER PRIMARY KEY AUTOINCREMENT,
                coupon_id                  INTEGER NOT NULL REFERENCES coupons(id),
                user_id                    INTEGER NOT NULL REFERENCES users(internal_id),
                promotion_code             TEXT,
                transaction_id             INTEGER REFERENCES payment_transactions(id),
                amount_discounted_agorot   INTEGER,
                redeemed_at                DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (coupon_id, user_id)
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_coupon_redemptions_coupon "
            "ON coupon_redemptions(coupon_id, redeemed_at DESC)"
        )
        # coupon_applications was dropped alongside the coupons rebuild above; if a partial
        # migration left it behind with rows, carry the mapping over.
        if await _table_exists(db, "coupon_applications"):
            await db.execute(
                """INSERT INTO coupon_redemptions (id, coupon_id, user_id, redeemed_at)
                   SELECT id, coupon_id, user_id, applied_at FROM coupon_applications"""
            )
            await db.execute("DROP TABLE coupon_applications")

    # ── 3. referrals: reshape into the binding + reward model ─────────────────
    if "reward_type" not in await _cols(db, "referrals"):
        await db.execute(
            """
            CREATE TABLE referrals_new (
                id                             INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id                    INTEGER NOT NULL REFERENCES users(internal_id),
                referred_id                    INTEGER NOT NULL REFERENCES users(internal_id),
                referral_code                  TEXT NOT NULL,
                status                         TEXT NOT NULL DEFAULT 'bound'
                                               CHECK (status IN ('bound','rewarded','void')),
                reward_type                    TEXT
                                               CHECK (reward_type IS NULL OR
                                                      reward_type IN ('balance_credit','banked')),
                reward_amount_agorot           INTEGER,
                reward_granted_at              DATETIME,
                stripe_balance_transaction_id  TEXT,
                created_at                     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (referred_id)
            )
            """
        )
        legacy_ref = await _cols(db, "referrals")
        if {"referrer_id", "referred_id", "referral_code"} <= set(legacy_ref):
            await db.execute(
                """INSERT INTO referrals_new
                       (id, referrer_id, referred_id, referral_code, status, created_at)
                   SELECT id, referrer_id, referred_id, referral_code, 'bound', created_at
                     FROM referrals"""
            )
        await db.execute("DROP TABLE referrals")
        await db.execute("ALTER TABLE referrals_new RENAME TO referrals")
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id, status)"
        )

    # ── 4. referral_credits: banked-credit ledger (D-S5) ──────────────────────
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS referral_credits (
            id                             INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id                    INTEGER NOT NULL REFERENCES users(internal_id),
            referral_id                    INTEGER REFERENCES referrals(id),
            status                         TEXT NOT NULL DEFAULT 'banked'
                                           CHECK (status IN ('banked','applied','void')),
            applied_amount_agorot          INTEGER,
            applied_at                     DATETIME,
            stripe_balance_transaction_id  TEXT,
            created_at                     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_referral_credits_referrer "
        "ON referral_credits(referrer_id, status)"
    )

    # ── 5. subscription_events: extend the event_type CHECK (Stage-4 audit) ───
    # Rebuild (SQLite cannot ALTER a CHECK), preserving all rows/columns/indexes.
    check_probe = await db.execute_fetchall(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='subscription_events'"
    )
    if check_probe and "referral_reward_earned" not in (check_probe[0][0] or ""):
        await db.execute(
            """
            CREATE TABLE subscription_events_new (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL REFERENCES users(internal_id),
                event_type     VARCHAR(48) NOT NULL CHECK (event_type IN (
                                   'trial_started','trial_ended_converted','trial_ended_expired',
                                   'trial_ended_to_free',
                                   'subscription_started','subscription_renewed',
                                   'subscription_cancelled_user',
                                   'subscription_cancelled_failed_payment',
                                   'subscription_reactivated',
                                   'plan_upgraded','plan_downgraded','refund_issued',
                                   'payment_document_issued',
                                   'subscription_past_due',
                                   'dunning_retry_scheduled',
                                   'subscription_expired_dunning',
                                   'subscription_dropped_to_free',
                                   -- Stage 4 (coupons + referral) additions:
                                   'referral_reward_earned',
                                   'referral_credit_banked',
                                   'referral_credit_applied',
                                   'referral_reward_voided',
                                   'coupon_redeemed',
                                   'zero_amount_invoice_no_document')),
                tier_before    TEXT,
                tier_after     TEXT,
                transaction_id INTEGER REFERENCES payment_transactions(id),
                metadata_json  TEXT,
                created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """INSERT INTO subscription_events_new
               SELECT id, user_id, event_type, tier_before, tier_after,
                      transaction_id, metadata_json, created_at
               FROM subscription_events"""
        )
        await db.execute("DROP TABLE subscription_events")
        await db.execute("ALTER TABLE subscription_events_new RENAME TO subscription_events")
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_sub_events_user "
            "ON subscription_events(user_id, created_at DESC)"
        )

    await db.commit()
