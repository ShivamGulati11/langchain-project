"""Dedupe schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DedupeRunRequest(BaseModel):
    lead_id: uuid.UUID
    idempotency_key: Optional[str] = None


class DedupeLogRead(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    nbfc_id: str
    outcome: str
    correlation_id: Optional[str] = None
    idempotency_key: str
    error_detail: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}
