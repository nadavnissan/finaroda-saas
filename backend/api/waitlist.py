"""Public waitlist endpoint — closed-beta signups (INSERT OR IGNORE)."""
import aiosqlite
from fastapi import APIRouter, Depends

from backend.core.database import get_db_connection
from backend.models.auth import WaitlistRequest

router = APIRouter(prefix="/api/waitlist", tags=["waitlist"])


@router.post("")
async def join_waitlist(
    body: WaitlistRequest,
    db: aiosqlite.Connection = Depends(get_db_connection),
):
    """Add an email to the waitlist. Idempotent; always returns success."""
    email = body.email.lower().strip()
    await db.execute(
        """INSERT OR IGNORE INTO waitlist (email, name, source, utm_source)
           VALUES (?, ?, ?, ?)""",
        (email, body.name, body.source, body.utm_source),
    )
    await db.commit()
    return {"message": "You're on the waitlist.", "email": email}
