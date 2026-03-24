"""Webhook payload schemas for partner callbacks."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class WebhookEvent(BaseModel):
    """Normalised internal representation of a partner webhook event."""

    partner: str
    partner_message_id: str
    event_type: str  # delivered | read | clicked | failed | bounced
    payload: Optional[dict[str, Any]] = None
    raw: Optional[str] = None


class SMSWebhookPayload(BaseModel):
    """Generic SMS webhook payload (adapter-specific in services layer)."""

    message_id: str
    status: str
    to: Optional[str] = None
    error_code: Optional[str] = None
    extra: Optional[dict[str, Any]] = None


class WhatsAppWebhookPayload(BaseModel):
    message_id: str
    status: str
    timestamp: Optional[str] = None
    extra: Optional[dict[str, Any]] = None


class EmailWebhookPayload(BaseModel):
    message_id: str
    event: str
    email: Optional[str] = None
    timestamp: Optional[int] = None
    extra: Optional[dict[str, Any]] = None


class IVRWebhookPayload(BaseModel):
    call_sid: str
    status: str
    duration: Optional[int] = None
    extra: Optional[dict[str, Any]] = None
