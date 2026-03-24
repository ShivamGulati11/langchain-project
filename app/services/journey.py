"""Journey / state-machine service."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journey import JourneyInstance
from app.models.lead import Lead

logger = structlog.get_logger(__name__)


class JourneyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def start_journey(
        self, lead_id: uuid.UUID, winning_nbfc_id: str, definition_version: str = "v1"
    ) -> JourneyInstance:
        instance = JourneyInstance(
            lead_id=lead_id,
            definition_version=definition_version,
            state="started",
            current_step_index=0,
        )
        self.db.add(instance)
        await self.db.flush()
        logger.info(
            "Journey started",
            journey_id=str(instance.id),
            lead_id=str(lead_id),
        )
        # Advance to first step
        await self.advance(instance.id)
        return instance

    async def advance(self, journey_id: uuid.UUID) -> None:
        """Execute the current step and advance the state machine."""
        from app.orchestration.journey_graph import run_journey_step

        await run_journey_step(journey_id=journey_id, db=self.db)

    async def get_instance(self, journey_id: uuid.UUID) -> Optional[JourneyInstance]:
        result = await self.db.execute(
            select(JourneyInstance).where(JourneyInstance.id == journey_id)
        )
        return result.scalar_one_or_none()

    async def complete(self, journey_id: uuid.UUID) -> None:
        instance = await self.get_instance(journey_id)
        if instance:
            instance.state = "completed"
            await self.db.flush()
            logger.info("Journey completed", journey_id=str(journey_id))

    async def stop(self, journey_id: uuid.UUID, reason: str = "stopped") -> None:
        instance = await self.get_instance(journey_id)
        if instance:
            instance.state = "stopped"
            await self.db.flush()
            logger.info("Journey stopped", journey_id=str(journey_id), reason=reason)
