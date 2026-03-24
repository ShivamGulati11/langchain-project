"""Analytics API endpoints."""
from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.analytics import AnalyticsService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/funnel")
async def funnel_report(
    batch_id: Optional[uuid.UUID] = Query(None),
    config_version_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Return funnel drop-off counts at each stage: upload → dedupe → sends → events."""
    svc = AnalyticsService(db)
    return await svc.funnel_report(batch_id=batch_id, config_version_id=config_version_id)


@router.get("/nbfc-performance")
async def nbfc_performance(
    batch_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """NBFC pass/fail/error rates."""
    svc = AnalyticsService(db)
    return await svc.nbfc_performance(batch_id=batch_id)


@router.get("/channel-performance")
async def channel_performance(
    batch_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Per-channel send/delivered/read/click rates."""
    svc = AnalyticsService(db)
    return await svc.channel_performance(batch_id=batch_id)
