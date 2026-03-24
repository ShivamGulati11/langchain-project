"""Lead qualification service – routes lead after dedupe outcome."""
from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead

logger = structlog.get_logger(__name__)


class QualificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def handle_pass(self, lead_id: uuid.UUID, winning_nbfc_id: str) -> None:
        """On PASS: update lead, enqueue communication journey."""
        result = await self.db.execute(select(Lead).where(Lead.lead_id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            logger.error("Lead not found for qualification", lead_id=str(lead_id))
            return

        lead.winning_nbfc_id = winning_nbfc_id
        lead.status = "qualified"
        await self.db.flush()
        logger.info("Lead qualified", lead_id=str(lead_id), winning_nbfc=winning_nbfc_id)

        # Enqueue journey start
        from app.workers.celery_app import start_journey_task

        start_journey_task.delay(str(lead_id), winning_nbfc_id)

    async def handle_all_fail(self, lead_id: uuid.UUID) -> None:
        """On all FAIL: mark lead as rejected (terminal state)."""
        result = await self.db.execute(select(Lead).where(Lead.lead_id == lead_id))
        lead = result.scalar_one_or_none()
        if lead:
            lead.status = "rejected"
            await self.db.flush()
        logger.info("Lead rejected (all NBFCs failed)", lead_id=str(lead_id))
