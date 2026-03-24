"""Journey Celery worker implementation."""
from __future__ import annotations

import uuid

import structlog

from app.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)


async def _start_journey(lead_id: uuid.UUID, winning_nbfc_id: str) -> None:
    async with AsyncSessionLocal() as db:
        from app.services.journey import JourneyService

        svc = JourneyService(db)
        await svc.start_journey(lead_id, winning_nbfc_id)
        await db.commit()
        logger.info("Journey started", lead_id=str(lead_id))


async def _advance_journey(journey_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        from app.services.journey import JourneyService

        svc = JourneyService(db)
        await svc.advance(journey_id)
        await db.commit()
        logger.info("Journey advanced", journey_id=str(journey_id))
