"""Base NBFC adapter interface and registry."""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.utils.rate_limiter import RateLimiter

logger = structlog.get_logger(__name__)
settings = get_settings()

# Global rate limiters per NBFC (keyed by nbfc_id)
_rate_limiters: dict[str, RateLimiter] = {}


def get_rate_limiter(nbfc_id: str, qps: int = 10) -> RateLimiter:
    if nbfc_id not in _rate_limiters:
        _rate_limiters[nbfc_id] = RateLimiter(rate=qps, burst=qps * 2)
    return _rate_limiters[nbfc_id]


class BaseNBFCAdapter(ABC):
    """Abstract base for all NBFC adapters."""

    nbfc_id: str
    base_url: str
    api_key: str
    timeout: int = 10
    qps: int = 10

    @abstractmethod
    async def check(self, lead_id: uuid.UUID) -> dict[str, Any]:
        """
        Perform the dedupe check.
        Returns dict with at minimum: {"outcome": "PASS"|"FAIL"|"ERROR"}
        """

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=0.5, max=8))
    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Transport-level POST with retry (separate from business fallback)."""
        limiter = get_rate_limiter(self.nbfc_id, self.qps)
        await limiter.acquire()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            return response.json()


# ── Registry ──────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, type[BaseNBFCAdapter]] = {}


def register_nbfc(cls: type[BaseNBFCAdapter]) -> type[BaseNBFCAdapter]:
    _REGISTRY[cls.nbfc_id] = cls
    return cls


def get_nbfc_adapter(nbfc_id: str) -> BaseNBFCAdapter:
    # Import implementations to trigger registration
    from app.integrations.nbfc import nbfc_a, nbfc_b, nbfc_c  # noqa: F401

    cls = _REGISTRY.get(nbfc_id)
    if not cls:
        raise ValueError(f"Unknown NBFC: {nbfc_id}")
    return cls()
