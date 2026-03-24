"""NBFC Dedupe orchestration service – waterfall pattern."""
from __future__ import annotations

import uuid
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dedupe import DedupeLog
from app.models.lead import Lead
from app.services.config_manager import ConfigManagerService
from app.utils.idempotency import build_dedupe_idempotency_key

logger = structlog.get_logger(__name__)

TERMINAL_PASS = "PASS"
TERMINAL_FAIL = "FAIL"
OUTCOME_ERROR = "ERROR"
OUTCOME_TIMEOUT = "TIMEOUT"


class DedupeService:
    """Executes the NBFC waterfall per configured priority list."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run_waterfall(self, lead_id: uuid.UUID) -> str:
        """
        Run sequential NBFC dedupe for a lead.
        Returns the final outcome: PASS | FAIL | ERROR
        """
        from app.orchestration.dedupe_chain import run_dedupe_chain

        result = await run_dedupe_chain(lead_id=lead_id, db=self.db)
        return result

    async def get_dedupe_logs(self, lead_id: uuid.UUID) -> list[DedupeLog]:
        result = await self.db.execute(
            select(DedupeLog).where(DedupeLog.lead_id == lead_id)
        )
        return list(result.scalars().all())

    async def record_attempt(
        self,
        lead_id: uuid.UUID,
        nbfc_id: str,
        outcome: str,
        correlation_id: Optional[str] = None,
        raw_response_ref: Optional[str] = None,
        error_detail: Optional[str] = None,
    ) -> DedupeLog:
        idempotency_key = build_dedupe_idempotency_key(lead_id, nbfc_id)
        log = DedupeLog(
            lead_id=lead_id,
            nbfc_id=nbfc_id,
            outcome=outcome,
            correlation_id=correlation_id,
            raw_response_ref=raw_response_ref,
            idempotency_key=idempotency_key,
            error_detail=error_detail,
        )
        self.db.add(log)
        await self.db.flush()
        return log
