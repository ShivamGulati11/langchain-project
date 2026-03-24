"""Exotel IVR adapter."""
from __future__ import annotations

import uuid
from typing import Any, Optional

import httpx
import structlog

from app.config import get_settings
from app.integrations.communication.base import BaseCommAdapter, register_comm

logger = structlog.get_logger(__name__)
settings = get_settings()

EXOTEL_BASE = "https://api.exotel.com/v1"


@register_comm
class ExotelIVRAdapter(BaseCommAdapter):
    channel = "ivr"
    partner = "exotel"

    async def send(
        self,
        lead_id: uuid.UUID,
        comm_send_id: Optional[uuid.UUID],
        template_id: Optional[str],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        url = (
            f"{EXOTEL_BASE}/Accounts/{settings.exotel_sid}/Calls/connect.json"
        )
        payload = {
            "From": params.get("phone", ""),
            "To": params.get("agent_number", ""),
            "CallerId": params.get("caller_id", ""),
            "StatusCallback": params.get("callback_url", ""),
        }
        headers = {"Content-Type": "application/json"}
        # Exotel uses HTTP Basic Auth
        async with httpx.AsyncClient(
            auth=(settings.exotel_sid, settings.exotel_token), timeout=15
        ) as client:
            response = await client.post(url, data=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return {"message_id": data.get("Call", {}).get("Sid", str(comm_send_id))}
