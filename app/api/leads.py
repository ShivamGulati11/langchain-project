"""Lead API endpoints."""
from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.lead import LeadCreate, LeadRead, UploadResponse
from app.services.ingestion import IngestionService

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_leads(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    config_version_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Async CSV upload.  Returns batch_id and job_id immediately (202 Accepted)."""
    if file.content_type not in ("text/csv", "application/csv", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    svc = IngestionService(db)
    result = await svc.create_batch_from_upload(file, config_version_id)
    background_tasks.add_task(svc.process_batch_async, result["batch_id"])
    return UploadResponse(**result)


@router.post("/", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(payload: LeadCreate, db: AsyncSession = Depends(get_db)):
    """Single lead creation via HTTP API."""
    svc = IngestionService(db)
    lead = await svc.ingest_single_lead(payload)
    return lead


@router.get("/{lead_id}", response_model=LeadRead)
async def get_lead(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve lead profile with status and journey summary."""
    svc = IngestionService(db)
    lead = await svc.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
