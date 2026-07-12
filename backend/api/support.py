"""Support tickets (B3 'Report a problem'). Files straight into the B7 admin queue.

Phase 1 builds only the filing endpoint (auth-required); the admin-side queue/reply
UI is B7 (phase 2). Every ticket carries the reporter's user_id so B7 can show plan
/ trial context inline.
"""
import aiosqlite
import structlog
from fastapi import APIRouter, Depends

from backend.core.auth import get_current_user
from backend.core.database import get_db_connection
from backend.models.auth import CurrentUser
from backend.models.support import TicketCreate, TicketResponse

router = APIRouter(prefix="/api/support", tags=["support"])
log = structlog.get_logger(__name__)


@router.post("/tickets", response_model=TicketResponse)
async def create_ticket(
    body: TicketCreate,
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> TicketResponse:
    """File a support ticket (status 'open') for the current user."""
    cursor = await db.execute(
        """INSERT INTO support_tickets (user_id, subject, body, category, status)
           VALUES (?, ?, ?, ?, 'open')""",
        (user.internal_id, body.subject, body.body, body.category),
    )
    await db.commit()
    log.info("support_ticket_created", ticket_id=cursor.lastrowid, category=body.category)
    return TicketResponse(id=cursor.lastrowid, status="open")
