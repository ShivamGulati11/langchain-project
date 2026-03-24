"""Lead and Batch schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class LeadBase(BaseModel):
    external_ref: Optional[str] = None
    phone_e164: Optional[str] = Field(None, description="Phone in E.164 format, e.g. +919876543210")
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    consent_given: bool = False

    @field_validator("phone_e164")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.startswith("+"):
            raise ValueError("Phone must be in E.164 format (start with '+')")
        return v


class LeadCreate(LeadBase):
    pass


class LeadRead(LeadBase):
    lead_id: uuid.UUID
    batch_id: Optional[uuid.UUID] = None
    status: str
    winning_nbfc_id: Optional[str] = None
    dnd: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadStatusUpdate(BaseModel):
    status: str


# ── Batch ─────────────────────────────────────────────────────────────────────


class BatchRead(BaseModel):
    batch_id: uuid.UUID
    source: str
    status: str
    total_rows: Optional[int] = None
    valid_rows: Optional[int] = None
    invalid_rows: Optional[int] = None
    checksum: Optional[str] = None
    error_file_url: Optional[str] = None
    config_version_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    batch_id: uuid.UUID
    job_id: str
    message: str = "Batch ingestion accepted"
