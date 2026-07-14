"""User-facing referral API (Stage 4). The invite card reads the permanent code, share
link, and the referrer's referral/reward counts. Auth-protected."""
import aiosqlite
import structlog
from fastapi import APIRouter, Depends

from backend.core import referral_service
from backend.core.auth import get_current_user
from backend.core.database import get_db_connection
from backend.models.auth import CurrentUser

router = APIRouter(prefix="/api/referral", tags=["referral"])
log = structlog.get_logger(__name__)


@router.get("")
async def get_referral(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Permanent code + share link + referred/rewarded/banked counts for the invite card."""
    return await referral_service.get_summary(db, user.internal_id)
