"""Cron entrypoint: resolve journal scenarios + log reveal teasers / trial reminders.
Run: python -m backend.scripts.run_resolve_scenarios"""
import asyncio

from backend.app.tasks.journal_tasks import (
    journal_reveal_teasers_task,
    log_trial_reminders_task,
    resolve_scenarios_task,
)


async def _run() -> None:
    await resolve_scenarios_task()
    await journal_reveal_teasers_task()
    await log_trial_reminders_task()


if __name__ == "__main__":
    asyncio.run(_run())
