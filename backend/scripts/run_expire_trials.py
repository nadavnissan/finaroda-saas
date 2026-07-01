"""Cron entrypoint: expire trials. Run: python -m backend.scripts.run_expire_trials"""
import asyncio

from backend.app.tasks.billing_tasks import expire_trials_task

if __name__ == "__main__":
    asyncio.run(expire_trials_task())
