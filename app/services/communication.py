"""Communication orchestration service."""
from __future__ import annotations

import uuid
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication import CommunicationLog
from app.models.lead import Lead
from app.utils.idempotency import build_comm_idempotency_key

logger = structlog.get_logger(__name__)


class CommunicationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def send(
        self,
        lead_id: uuid.UUID,
        channel: str,
        partner: str,
        journey_instance_id: Optional[uuid.UUID] = None,
        template_id: Optional[str] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> CommunicationLog:
        """Idempotent send – logs the attempt and dispatches to partner adapter."""
        idempotency_key = build_comm_idempotency_key(lead_id, channel, partner, journey_instance_id)

        # Check for existing log (idempotency)
        existing = await self.db.execute(
            select(CommunicationLog).where(
                CommunicationLog.idempotency_key == idempotency_key
            )
        )
        existing_log = existing.scalar_one_or_none()
        if existing_log:
            logger.info(
                "Duplicate comm send skipped",
                idempotency_key=idempotency_key,
                status=existing_log.status,
            )
            return existing_log

        log = CommunicationLog(
            lead_id=lead_id,
            journey_instance_id=journey_instance_id,
            channel=channel,
            partner=partner,
            status="requested",
            idempotency_key=idempotency_key,
        )
        self.db.add(log)
        await self.db.flush()

        # Dispatch to partner via adapter
        try:
            adapter = self._get_adapter(channel, partner)
            response = await adapter.send(
                lead_id=lead_id,
                comm_send_id=log.comm_send_id,
                template_id=template_id,
                params=params or {},
            )
            log.partner_message_id = response.get("message_id")
            log.status = "accepted"
        except Exception as exc:
            log.status = "failed"
            log.error_detail = str(exc)
            logger.error(
                "Comm send failed",
                lead_id=str(lead_id),
                channel=channel,
                partner=partner,
                error=str(exc),
            )

        await self.db.flush()
        return log

    def _get_adapter(self, channel: str, partner: str):
        from app.integrations.communication.base import get_comm_adapter

        return get_comm_adapter(channel, partner)
