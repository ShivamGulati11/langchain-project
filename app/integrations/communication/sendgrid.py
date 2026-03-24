"""SendGrid Email adapter."""
from __future__ import annotations

import uuid
from typing import Any, Optional

import httpx
import structlog

from app.config import get_settings
from app.integrations.communication.base import BaseCommAdapter, register_comm

logger = structlog.get_logger(__name__)
settings = get_settings()

SENDGRID_SEND_URL = "https://api.sendgrid.com/v3/mail/send"


@register_comm
class SendGridEmailAdapter(BaseCommAdapter):
    channel = "email"
    partner = "sendgrid"

    async def send(
        self,
        lead_id: uuid.UUID,
        comm_send_id: Optional[uuid.UUID],
        template_id: Optional[str],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "from": {"email": params.get("from_email", "noreply@example.com")},
            "personalizations": [
                {
                    "to": [{"email": params.get("email", "")}],
                    "dynamic_template_data": params,
                }
            ],
            "template_id": template_id or "",
        }
        headers = {
            "Authorization": f"Bearer {settings.sendgrid_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(SENDGRID_SEND_URL, json=payload, headers=headers)
            response.raise_for_status()
        # SendGrid returns 202 with no body; X-Message-Id in headers
        message_id = response.headers.get("X-Message-Id", str(comm_send_id))
        return {"message_id": message_id}
