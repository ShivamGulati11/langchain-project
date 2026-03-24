"""Token bucket rate limiter for NBFC/partner API calls."""
from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """Async token bucket rate limiter."""

    def __init__(self, rate: float, burst: int) -> None:
        self._rate = rate  # tokens per second
        self._burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        async with self._lock:
            await self._refill()
            if self._tokens < tokens:
                wait = (tokens - self._tokens) / self._rate
                await asyncio.sleep(wait)
                await self._refill()
            self._tokens -= tokens

    async def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
        self._last_refill = now
