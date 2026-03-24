"""Analytics and funnel tracking service."""
from __future__ import annotations

import uuid
from typing import Any, Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication import CommunicationLog
from app.models.dedupe import DedupeLog
from app.models.event import EventLog
from app.models.lead import Batch, Lead

logger = structlog.get_logger(__name__)


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def funnel_report(
        self,
        batch_id: Optional[uuid.UUID] = None,
        config_version_id: Optional[uuid.UUID] = None,
    ) -> dict[str, Any]:
        # Total leads
        q = select(func.count()).select_from(Lead)
        if batch_id:
            q = q.where(Lead.batch_id == batch_id)
        total_leads = (await self.db.execute(q)).scalar() or 0

        # Qualified (NBFC pass)
        q2 = select(func.count()).select_from(Lead).where(Lead.status == "qualified")
        if batch_id:
            q2 = q2.where(Lead.batch_id == batch_id)
        qualified = (await self.db.execute(q2)).scalar() or 0

        # Rejected
        q3 = select(func.count()).select_from(Lead).where(Lead.status == "rejected")
        if batch_id:
            q3 = q3.where(Lead.batch_id == batch_id)
        rejected = (await self.db.execute(q3)).scalar() or 0

        # Comm sends
        q4 = select(func.count()).select_from(CommunicationLog)
        if batch_id:
            q4 = q4.join(Lead, CommunicationLog.lead_id == Lead.lead_id).where(
                Lead.batch_id == batch_id
            )
        sends = (await self.db.execute(q4)).scalar() or 0

        # Delivered events
        q5 = select(func.count()).select_from(EventLog).where(
            EventLog.event_type == "comm.delivered"
        )
        delivered = (await self.db.execute(q5)).scalar() or 0

        # Read / clicked
        q6 = select(func.count()).select_from(EventLog).where(
            EventLog.event_type.in_(["comm.read", "comm.clicked"])
        )
        engaged = (await self.db.execute(q6)).scalar() or 0

        return {
            "total_leads": total_leads,
            "qualified": qualified,
            "rejected": rejected,
            "comm_sends": sends,
            "delivered": delivered,
            "engaged": engaged,
        }

    async def nbfc_performance(
        self, batch_id: Optional[uuid.UUID] = None
    ) -> list[dict[str, Any]]:
        q = select(
            DedupeLog.nbfc_id,
            DedupeLog.outcome,
            func.count().label("count"),
        ).group_by(DedupeLog.nbfc_id, DedupeLog.outcome)

        rows = (await self.db.execute(q)).all()
        result: dict[str, dict] = {}
        for row in rows:
            nbfc_id, outcome, count = row
            if nbfc_id not in result:
                result[nbfc_id] = {"nbfc_id": nbfc_id}
            result[nbfc_id][outcome.lower()] = count
        return list(result.values())

    async def channel_performance(
        self, batch_id: Optional[uuid.UUID] = None
    ) -> list[dict[str, Any]]:
        q = select(
            CommunicationLog.channel,
            CommunicationLog.partner,
            CommunicationLog.status,
            func.count().label("count"),
        ).group_by(
            CommunicationLog.channel,
            CommunicationLog.partner,
            CommunicationLog.status,
        )
        rows = (await self.db.execute(q)).all()
        result: dict[tuple, dict] = {}
        for row in rows:
            channel, partner, status, count = row
            key = (channel, partner)
            if key not in result:
                result[key] = {"channel": channel, "partner": partner}
            result[key][status] = count
        return list(result.values())
