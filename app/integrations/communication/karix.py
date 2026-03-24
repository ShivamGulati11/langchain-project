"""Karix WhatsApp adapter."""
from __future__ import annotations

import uuid
from typing import Any, Optional

import structlog

from app.config import get_settings
from app.integrations.communication.base import BaseCommAdapter, register_comm

logger = structlog.get_logger(__name__)
settings = get_settings()

KARIX_BASE = "https://api.karix.io"


@register_comm
class KarixWhatsAppAdapter(BaseCommAdapter):
    channel = "whatsapp"
    partner = "karix"

    async def send(
        self,
        lead_id: uuid.UUID,
        comm_send_id: Optional[uuid.UUID],
        template_id: Optional[str],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "channel": "WHATSAPP",
            "source": params.get("from_number", ""),
            "destination": {"msisdn": [{"number": params.get("phone", "")}]},
            "message": {
                "channel": "WHATSAPP",
                "content": {
                    "preview_url": False,
                    "type": "template",
                    "template": {
                        "id": template_id or "",
                        "params": [v for v in params.values()],
                    },
                },
            },
        }
        headers = {
            "api_key": settings.karix_api_key,
            "api_secret": settings.karix_api_secret,
        }
        response = await self._post(f"{KARIX_BASE}/whatsapp/message", payload, headers)
        return {"message_id": response.get("uid", str(comm_send_id))}
