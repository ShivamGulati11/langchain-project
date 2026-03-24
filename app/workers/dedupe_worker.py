"""Dedupe Celery worker implementation."""
from __future__ import annotations

import csv
import io
import uuid

import structlog

from app.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)


async def _process_batch(batch_id: uuid.UUID) -> None:
    """Load and process all rows of a CSV batch."""
    async with AsyncSessionLocal() as db:
        from app.models.lead import Batch
        from app.services.ingestion import IngestionService
        from sqlalchemy import select

        result = await db.execute(select(Batch).where(Batch.batch_id == batch_id))
        batch = result.scalar_one_or_none()
        if not batch:
            logger.error("Batch not found", batch_id=str(batch_id))
            return

        batch.status = "processing"
        await db.commit()

        # Assume raw CSV was stored temporarily; in production fetch from S3/Blob.
        # For P0, we simply trigger dedupe for each existing lead in this batch.
        from app.models.lead import Lead

        leads_result = await db.execute(
            select(Lead).where(Lead.batch_id == batch_id)
        )
        leads = list(leads_result.scalars().all())
        valid = 0
        for lead in leads:
            from app.workers.celery_app import run_dedupe_task

            run_dedupe_task.delay(str(lead.lead_id))
            valid += 1

        batch.status = "completed"
        batch.valid_rows = valid
        await db.commit()
        logger.info("Batch processed", batch_id=str(batch_id), leads=valid)


async def _run_dedupe(lead_id: uuid.UUID) -> None:
    """Execute NBFC waterfall for a single lead."""
    async with AsyncSessionLocal() as db:
        from app.services.dedupe import DedupeService

        svc = DedupeService(db)
        outcome = await svc.run_waterfall(lead_id)
        await db.commit()
        logger.info("Dedupe completed", lead_id=str(lead_id), outcome=outcome)
