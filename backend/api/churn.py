"""Churn / exit survey capture (Stage 7, D-A5).

No cancel/downgrade UI existed (Stage 3 payments blocked), so this is a decoupled,
auth'd endpoint the client posts when a user chooses to leave or cancel — surfaced from
Settings ("Cancel plan / leave") and reusable at the trial→Free decision. One required
question + optional free text; skippable (the client simply never calls it). Stored in
`churn_reasons` (mig 006); admin sees the aggregate in /overview and the list in
/api/admin/churn, plus a per-user flag in the user table.
"""
import aiosqlite
import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.core.auth import get_current_user
from backend.core.database import get_db_connection
from backend.models.auth import CurrentUser

router = APIRouter(prefix="/api/churn", tags=["churn"])
log = structlog.get_logger(__name__)


class ChurnSurveyCreate(BaseModel):
    reason_category: str = Field(min_length=1, max_length=60)   # the one required question
    reason_free_text: str | None = Field(default=None, max_length=2000)
    improvement_text: str | None = Field(default=None, max_length=2000)
    would_return: bool | None = None


@router.post("/survey")
async def submit_survey(
    body: ChurnSurveyCreate,
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Record an exit-survey response for the current user. total_spent stays NULL until
    Stage 3 (payments) ships; days_as_customer is derived from signup."""
    urows = await db.execute_fetchall(
        "SELECT tier, created_at FROM users WHERE internal_id=?", (user.internal_id,)
    )
    tier = urows[0][0] if urows else None
    days_rows = await db.execute_fetchall(
        "SELECT CAST(julianday('now') - julianday(created_at) AS INTEGER) FROM users WHERE internal_id=?",
        (user.internal_id,),
    )
    days = days_rows[0][0] if days_rows and days_rows[0][0] is not None else None
    cur = await db.execute(
        """INSERT INTO churn_reasons
           (user_id, reason_category, reason_free_text, improvement_text,
            days_as_customer, subscription_plan, would_return)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user.internal_id, body.reason_category, body.reason_free_text, body.improvement_text,
         days, tier, 1 if body.would_return else (0 if body.would_return is False else None)),
    )
    await db.commit()
    log.info("churn_survey_submitted", user_id=user.internal_id, reason=body.reason_category)
    return {"ok": True, "id": cur.lastrowid}
