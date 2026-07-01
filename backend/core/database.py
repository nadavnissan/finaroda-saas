"""Clean DB access — FastAPI dependency yielding an aiosqlite connection.

Single-generation schema (backend/migrations/, internal_id key). Does NOT inherit
the legacy core/db.py (telegram_id bot schema was discarded in P0).
"""
import aiosqlite

from backend.config import DATABASE_URL


def _db_path() -> str:
    return DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")


async def get_db_connection():
    """FastAPI Depends: yields an aiosqlite connection with Row factory + FKs on."""
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
