"""Timer worker – scans for journeys with elapsed next_action_at and advances them."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog

from app.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)


async def tick() -> None:
    """Check for overdue journey steps and enqueue advance tasks."""
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        from app.models.journey import JourneyInstance
        from app.workers.celery_app import advance_journey_task

        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(JourneyInstance).where(
                JourneyInstance.state == "running",
                JourneyInstance.next_action_at <= now,
            )
        )
        instances = list(result.scalars().all())
        for instance in instances:
            advance_journey_task.delay(str(instance.id))
            logger.info("Timer tick: advancing journey", journey_id=str(instance.id))


async def run_timer_loop(interval_seconds: int = 60) -> None:
    """Infinite loop for the timer worker (run as a separate process)."""
    logger.info("Timer worker started", interval=interval_seconds)
    while True:
        try:
            await tick()
        except Exception as exc:
            logger.error("Timer tick error", error=str(exc))
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_timer_loop())
