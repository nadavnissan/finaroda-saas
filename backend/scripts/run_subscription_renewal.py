"""Cron entrypoint: renewal batch. Run: python -m backend.scripts.run_subscription_renewal"""
import asyncio

from backend.app.tasks.billing_tasks import subscription_renewal_task

if __name__ == "__main__":
    asyncio.run(subscription_renewal_task())
