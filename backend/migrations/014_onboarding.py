"""Migration 014 — onboarding_questions + onboarding_responses (editable survey; audit 019).

Admin-editable onboarding survey; user responses stored per question.
"""
import aiosqlite

MIGRATION_ID = "014_onboarding"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS onboarding_questions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            question_type TEXT NOT NULL DEFAULT 'text'
                          CHECK (question_type IN ('text','single_choice','multi_choice','scale')),
            options_json  TEXT,
            order_index   INTEGER NOT NULL DEFAULT 0,
            is_active     INTEGER NOT NULL DEFAULT 1,
            created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS onboarding_responses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(internal_id),
            question_id INTEGER NOT NULL REFERENCES onboarding_questions(id),
            answer_text TEXT,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, question_id)
        )
        """
    )
    await db.commit()
