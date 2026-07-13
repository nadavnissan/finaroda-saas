"""Stage 5 in-app notification bell + preferences (D-N3 / D-N2).

Server-authoritative: the unread badge and read-state live in the DB, so they survive a
refresh and stay consistent across devices. Opening the bell panel marks the items it
shows as read via POST /read. Prefs (in-app / sound / vibration / product-email /
broadcast-email) persist here and are respected everywhere sends originate.
"""
import aiosqlite
import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core import notifications as notif
from backend.core.auth import get_current_user
from backend.core.database import get_db_connection
from backend.models.auth import CurrentUser

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
log = structlog.get_logger(__name__)


class ReadRequest(BaseModel):
    ids: list[int] | None = None   # None => mark all unread read


class PrefsUpdate(BaseModel):
    inapp_enabled: bool | None = None
    sound_enabled: bool | None = None
    vibration_enabled: bool | None = None
    email_product: bool | None = None
    email_broadcast: bool | None = None


@router.get("")
async def list_feed(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Newest-first bell feed + server-authoritative unread count."""
    items = await notif.list_notifications(db, user.internal_id)
    unread = await notif.unread_count(db, user.internal_id)
    return {"notifications": items, "unread_count": unread}


@router.post("/read")
async def mark_read(
    body: ReadRequest,
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Mark the given ids read (or all unread when ids omitted). Idempotent."""
    marked = await notif.mark_read(db, user.internal_id, body.ids)
    unread = await notif.unread_count(db, user.internal_id)
    return {"marked": marked, "unread_count": unread}


@router.get("/prefs")
async def get_prefs(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Current notification preferences (lazily defaulted on first read)."""
    return await notif.get_prefs(db, user.internal_id)


@router.put("/prefs")
async def put_prefs(
    body: PrefsUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Persist a partial prefs patch. Returns the full prefs."""
    return await notif.update_prefs(db, user.internal_id, body.model_dump(exclude_none=True))
