"""Cron entrypoint: resolve journal scenarios against real market data.
Run: python -m backend.scripts.run_resolve_scenarios

Note: the reveal-teaser + day-11 trial-reminder SENDS moved to the authoritative
POST /api/cron/notifications endpoint (Stage 5, D-N9). This script only computes market
resolutions now; run the notifications cron separately (see SESSION_HANDOFF)."""
import asyncio

from backend.app.tasks.journal_tasks import resolve_scenarios_task


async def _run() -> None:
    await resolve_scenarios_task()


if __name__ == "__main__":
    asyncio.run(_run())
