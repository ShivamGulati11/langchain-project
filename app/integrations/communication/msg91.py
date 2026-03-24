"""MSG91 SMS adapter."""
from __future__ import annotations

import uuid
from typing import Any, Optional

import structlog

from app.config import get_settings
from app.integrations.communication.base import BaseCommAdapter, register_comm

logger = structlog.get_logger(__name__)
settings = get_settings()

MSG91_SEND_URL = "https://api.msg91.com/api/v5/flow/"


@register_comm
class MSG91SMSAdapter(BaseCommAdapter):
    channel = "sms"
    partner = "msg91"

    async def send(
        self,
        lead_id: uuid.UUID,
        comm_send_id: Optional[uuid.UUID],
        template_id: Optional[str],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "template_id": template_id or "",
            "short_url": "0",
            "recipients": [
                {
                    "mobiles": params.get("phone", ""),
                    **{k: v for k, v in params.items() if k != "phone"},
                }
            ],
        }
        headers = {"authkey": settings.msg91_auth_key, "Content-Type": "application/json"}
        response = await self._post(MSG91_SEND_URL, payload, headers)
        return {"message_id": response.get("request_id", str(comm_send_id))}
