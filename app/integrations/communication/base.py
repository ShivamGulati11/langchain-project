"""Base communication adapter interface and registry."""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)

# Registry keyed by (channel, partner)
_COMM_REGISTRY: dict[tuple[str, str], type[BaseCommAdapter]] = {}


class BaseCommAdapter(ABC):
    """Abstract base for all communication partner adapters."""

    channel: str  # whatsapp | sms | email | ivr
    partner: str

    @abstractmethod
    async def send(
        self,
        lead_id: uuid.UUID,
        comm_send_id: Optional[uuid.UUID],
        template_id: Optional[str],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Send a message.
        Must return dict with at minimum: {"message_id": "<partner_message_id>"}
        Raise on unrecoverable failure.
        """

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=0.5, max=8))
    async def _post(
        self,
        url: str,
        payload: dict[str, Any],
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload, headers=headers or {})
            response.raise_for_status()
            return response.json()


def register_comm(cls: type[BaseCommAdapter]) -> type[BaseCommAdapter]:
    _COMM_REGISTRY[(cls.channel, cls.partner)] = cls
    return cls


def get_comm_adapter(channel: str, partner: str) -> BaseCommAdapter:
    # Import implementations to trigger registration
    from app.integrations.communication import (  # noqa: F401
        exotel,
        karix,
        msg91,
        sendgrid,
    )

    cls = _COMM_REGISTRY.get((channel, partner))
    if not cls:
        raise ValueError(f"Unknown comm adapter: channel={channel}, partner={partner}")
    return cls()
