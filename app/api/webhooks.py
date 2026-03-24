"""Partner webhook endpoints (SMS, WhatsApp, Email, IVR)."""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.event_processor import EventProcessorService
from app.utils.observability import meter

logger = structlog.get_logger(__name__)
router = APIRouter()


async def _process_webhook(
    channel: str,
    partner: str,
    raw_body: bytes,
    payload: dict[str, Any],
    db: AsyncSession,
    signature: str | None = None,
):
    svc = EventProcessorService(db)
    await svc.process_partner_webhook(
        channel=channel,
        partner=partner,
        raw_body=raw_body,
        payload=payload,
        signature=signature,
    )


@router.post("/sms", status_code=status.HTTP_200_OK)
async def sms_webhook(
    request: Request,
    x_partner: str = Header(default="msg91"),
    x_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Ingest SMS delivery/status callbacks from partners."""
    raw_body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    await _process_webhook("sms", x_partner, raw_body, payload, db, x_signature)
    return {"status": "accepted"}


@router.post("/whatsapp", status_code=status.HTTP_200_OK)
async def whatsapp_webhook(
    request: Request,
    x_partner: str = Header(default="karix"),
    x_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Ingest WhatsApp delivery/read/click callbacks."""
    raw_body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    await _process_webhook("whatsapp", x_partner, raw_body, payload, db, x_signature)
    return {"status": "accepted"}


@router.post("/email", status_code=status.HTTP_200_OK)
async def email_webhook(
    request: Request,
    x_partner: str = Header(default="sendgrid"),
    x_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Ingest email event callbacks (bounce, open, click, etc.)."""
    raw_body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    await _process_webhook("email", x_partner, raw_body, payload, db, x_signature)
    return {"status": "accepted"}


@router.post("/ivr", status_code=status.HTTP_200_OK)
async def ivr_webhook(
    request: Request,
    x_partner: str = Header(default="exotel"),
    x_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Ingest IVR call status callbacks."""
    raw_body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    await _process_webhook("ivr", x_partner, raw_body, payload, db, x_signature)
    return {"status": "accepted"}
