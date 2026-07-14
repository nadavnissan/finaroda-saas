"""Scheduled notification sweeps (D-N9). Protected by a shared CRON_SECRET header,
idempotent (safe to run twice — a second run sends zero). Same shape as the existing
resolve-scenarios cron. Railway wiring is a manual step (see SESSION_HANDOFF)."""
import structlog
from fastapi import APIRouter, Header, HTTPException

from backend.app.tasks.billing_tasks import billing_batch_task, trial_ending_soon_task
from backend.app.tasks.journal_tasks import journal_reveal_teasers_task
from backend.config import CRON_SECRET

router = APIRouter(prefix="/api/cron", tags=["cron"])
log = structlog.get_logger(__name__)


def _authorize(secret: str | None) -> None:
    """503 when unconfigured (fail closed), 403 on mismatch."""
    if not CRON_SECRET:
        raise HTTPException(503, detail={"code": "CRON_DISABLED", "message": "CRON_SECRET not configured"})
    if secret != CRON_SECRET:
        raise HTTPException(403, detail={"code": "FORBIDDEN", "message": "Bad cron secret"})


@router.post("/notifications")
async def run_notification_sweeps(
    x_cron_secret: str | None = Header(default=None),
) -> dict:
    """Day-11 trial reminder + journal-reveal teaser sweeps. Idempotent."""
    _authorize(x_cron_secret)
    trial = await trial_ending_soon_task()
    teaser = await journal_reveal_teasers_task()
    log.info("cron_notifications", trial=trial, teaser=teaser)
    return {"trial_reminder": trial, "reveal_teaser": teaser}


@router.post("/billing")
async def run_billing_batch(
    x_cron_secret: str | None = Header(default=None),
) -> dict:
    """Stage-3 billing cron (D-B9): expire trials, drop cancelled-at-period-end subs,
    and charge/renew + dunning. Idempotent; safe to run twice. Railway wiring is a
    manual step (see SESSION_HANDOFF)."""
    _authorize(x_cron_secret)
    result = await billing_batch_task()
    log.info("cron_billing", **result)
    return result
