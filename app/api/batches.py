"""Batch API endpoints."""
from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.lead import BatchRead
from app.services.ingestion import IngestionService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/{batch_id}", response_model=BatchRead)
async def get_batch(batch_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Return progress, counts, and error artifact links for a batch."""
    svc = IngestionService(db)
    batch = await svc.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch
