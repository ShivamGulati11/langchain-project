"""NBFC-C adapter."""
from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.config import get_settings
from app.integrations.nbfc.base import BaseNBFCAdapter, register_nbfc

logger = structlog.get_logger(__name__)
settings = get_settings()


@register_nbfc
class NBFCCAdapter(BaseNBFCAdapter):
    nbfc_id = "NBFC_C"
    base_url = settings.nbfc_c_base_url
    api_key = settings.nbfc_c_api_key
    timeout = settings.nbfc_default_timeout_seconds
    qps = settings.nbfc_default_qps

    async def check(self, lead_id: uuid.UUID) -> dict[str, Any]:
        try:
            response = await self._post(
                "/api/v2/verify",
                {"id": str(lead_id), "channel": "LOCE"},
            )
            # NBFC_C returns {"status": "OK"} or {"status": "REJECT"}
            outcome = "PASS" if response.get("status") == "OK" else "FAIL"
            return {"outcome": outcome, "raw": response}
        except Exception as exc:
            logger.error("NBFC_C check failed", lead_id=str(lead_id), error=str(exc))
            return {"outcome": "ERROR", "error": str(exc)}
