"""Discovers and runs all pending migrations (single clean schema, internal_id)."""
import importlib.util
import logging
from pathlib import Path

import aiosqlite

log = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent


async def apply_migrations(db_path: str) -> None:
    """Run all pending migrations against the given database path."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id TEXT PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()

        applied = {
            row[0]
            for row in await db.execute_fetchall("SELECT id FROM schema_migrations")
        }

        migration_files = sorted(
            f for f in MIGRATIONS_DIR.glob("0*.py") if f.name != "run_migrations.py"
        )

        for mf in migration_files:
            spec = importlib.util.spec_from_file_location(mf.stem, mf)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            migration_id = mod.MIGRATION_ID
            if migration_id in applied:
                log.debug(f"Migration already applied: {migration_id}")
                continue

            log.info(f"Applying migration: {migration_id}")
            await mod.up(db)
            await db.execute(
                "INSERT INTO schema_migrations (id) VALUES (?)", (migration_id,)
            )
            await db.commit()
            log.info(f"Migration applied: {migration_id}")
