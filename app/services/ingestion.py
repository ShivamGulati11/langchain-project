"""Lead ingestion service – CSV, API, and S3 inputs."""
from __future__ import annotations

import csv
import hashlib
import io
import uuid
from typing import Any, Optional

import structlog
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Batch, Lead
from app.schemas.lead import LeadCreate
from app.utils.phone_normalizer import normalize_phone
from app.utils.validators import validate_lead_row

logger = structlog.get_logger(__name__)


class IngestionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Batch creation ────────────────────────────────────────────────────────

    async def create_batch_from_upload(
        self, file: UploadFile, config_version_id: Optional[str] = None
    ) -> dict[str, Any]:
        content = await file.read()
        checksum = hashlib.sha256(content).hexdigest()

        batch = Batch(
            source="csv",
            status="pending",
            checksum=checksum,
            config_version_id=uuid.UUID(config_version_id) if config_version_id else None,
        )
        self.db.add(batch)
        await self.db.flush()

        # Count rows (without processing yet – deferred to worker)
        text = content.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        batch.total_rows = len(rows)
        await self.db.flush()

        logger.info("Batch created", batch_id=str(batch.batch_id), total_rows=batch.total_rows)
        return {
            "batch_id": batch.batch_id,
            "job_id": f"job-{batch.batch_id}",
            "message": "Batch ingestion accepted",
        }

    async def process_batch_async(self, batch_id: uuid.UUID) -> None:
        """Background processing of a CSV batch (called as BackgroundTask)."""
        try:
            from app.workers.celery_app import process_batch_task

            process_batch_task.delay(str(batch_id))
        except ImportError:
            pass  # Celery not available in test/dev mode without broker

    # ── Single lead creation ──────────────────────────────────────────────────

    async def ingest_single_lead(self, payload: LeadCreate) -> Lead:
        phone_e164 = None
        phone_hash = None
        email_hash = None

        if payload.phone_e164:
            phone_e164 = normalize_phone(payload.phone_e164)
            phone_hash = hashlib.sha256(phone_e164.encode()).hexdigest()

        if payload.email:
            email_hash = hashlib.sha256(str(payload.email).lower().encode()).hexdigest()

        lead = Lead(
            external_ref=payload.external_ref,
            phone_e164=phone_e164,
            phone_hash=phone_hash,
            email=str(payload.email) if payload.email else None,
            email_hash=email_hash,
            first_name=payload.first_name,
            last_name=payload.last_name,
            consent_given=payload.consent_given,
            status="new",
        )
        self.db.add(lead)
        await self.db.flush()
        logger.info("Lead ingested", lead_id=str(lead.lead_id))
        return lead

    # ── Reads ─────────────────────────────────────────────────────────────────

    async def get_lead(self, lead_id: uuid.UUID) -> Optional[Lead]:
        result = await self.db.execute(select(Lead).where(Lead.lead_id == lead_id))
        return result.scalar_one_or_none()

    async def get_batch(self, batch_id: uuid.UUID) -> Optional[Batch]:
        result = await self.db.execute(select(Batch).where(Batch.batch_id == batch_id))
        return result.scalar_one_or_none()

    # ── Row-level processing (called by Celery worker) ────────────────────────

    async def process_csv_row(
        self, row: dict[str, Any], batch_id: uuid.UUID, config_version_id: Optional[uuid.UUID]
    ) -> tuple[Optional[Lead], Optional[str]]:
        """Validate and persist a single CSV row. Returns (lead, error_message)."""
        error = validate_lead_row(row)
        if error:
            return None, error

        phone_raw = row.get("phone", "")
        phone_e164 = normalize_phone(phone_raw) if phone_raw else None
        phone_hash = hashlib.sha256(phone_e164.encode()).hexdigest() if phone_e164 else None
        email = row.get("email", "").strip() or None
        email_hash = hashlib.sha256(email.lower().encode()).hexdigest() if email else None

        lead = Lead(
            external_ref=row.get("external_ref") or None,
            batch_id=batch_id,
            phone_e164=phone_e164,
            phone_hash=phone_hash,
            email=email,
            email_hash=email_hash,
            first_name=row.get("first_name") or None,
            last_name=row.get("last_name") or None,
            consent_given=str(row.get("consent_given", "false")).lower() in ("1", "true", "yes"),
            config_version_id=config_version_id,
            status="new",
        )
        self.db.add(lead)
        await self.db.flush()
        return lead, None
