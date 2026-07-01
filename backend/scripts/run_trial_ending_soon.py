"""Cron entrypoint: trial-ending reminder. Run: python -m backend.scripts.run_trial_ending_soon"""
import asyncio

from backend.app.tasks.billing_tasks import trial_ending_soon_task

if __name__ == "__main__":
    asyncio.run(trial_ending_soon_task())
