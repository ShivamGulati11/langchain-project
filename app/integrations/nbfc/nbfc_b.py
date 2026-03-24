"""NBFC-B adapter."""
from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.config import get_settings
from app.integrations.nbfc.base import BaseNBFCAdapter, register_nbfc

logger = structlog.get_logger(__name__)
settings = get_settings()


@register_nbfc
class NBFCBAdapter(BaseNBFCAdapter):
    nbfc_id = "NBFC_B"
    base_url = settings.nbfc_b_base_url
    api_key = settings.nbfc_b_api_key
    timeout = settings.nbfc_default_timeout_seconds
    qps = settings.nbfc_default_qps

    async def check(self, lead_id: uuid.UUID) -> dict[str, Any]:
        try:
            response = await self._post(
                "/dedupe",
                {"reference": str(lead_id)},
            )
            # NBFC_B returns {"result": "unique"} or {"result": "duplicate"}
            outcome = "PASS" if response.get("result") == "unique" else "FAIL"
            return {"outcome": outcome, "raw": response}
        except Exception as exc:
            logger.error("NBFC_B check failed", lead_id=str(lead_id), error=str(exc))
            return {"outcome": "ERROR", "error": str(exc)}
