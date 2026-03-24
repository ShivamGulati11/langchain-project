"""Event and webhook processor service."""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.communication import CommunicationLog
from app.models.event import EventLog

logger = structlog.get_logger(__name__)
settings = get_settings()

# Map partner status strings to internal event types
PARTNER_STATUS_MAP: dict[str, dict[str, str]] = {
    "msg91": {"delivered": "comm.delivered", "failed": "comm.failed"},
    "karix": {
        "DELIVERED": "comm.delivered",
        "READ": "comm.read",
        "FAILED": "comm.failed",
        "CLICKED": "comm.clicked",
    },
    "sendgrid": {
        "delivered": "comm.delivered",
        "open": "comm.read",
        "click": "comm.clicked",
        "bounce": "comm.failed",
        "unsubscribe": "comm.failed",
    },
    "exotel": {"completed": "comm.delivered", "failed": "comm.failed"},
    "netcore": {"delivered": "comm.delivered", "read": "comm.read", "clicked": "comm.clicked"},
}


class EventProcessorService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def process_partner_webhook(
        self,
        channel: str,
        partner: str,
        raw_body: bytes,
        payload: dict[str, Any],
        signature: Optional[str] = None,
    ) -> None:
        # 1. Verify HMAC signature
        if not self._verify_signature(partner, raw_body, signature):
            logger.warning("Webhook HMAC verification failed", partner=partner)
            return

        # 2. Normalise event
        partner_message_id = (
            payload.get("message_id")
            or payload.get("messageId")
            or payload.get("call_sid")
            or "unknown"
        )
        raw_status = (
            payload.get("status") or payload.get("event") or payload.get("Status") or "unknown"
        )
        event_type = (
            PARTNER_STATUS_MAP.get(partner, {}).get(raw_status)
            or f"comm.{raw_status.lower()}"
        )

        idempotency_key = f"{partner}:{partner_message_id}:{event_type}"

        # 3. Idempotency check
        existing = await self.db.execute(
            select(EventLog).where(EventLog.idempotency_key == idempotency_key)
        )
        if existing.scalar_one_or_none():
            logger.info("Duplicate webhook event skipped", idempotency_key=idempotency_key)
            return

        # 4. Look up comm_send
        comm_log = None
        if partner_message_id != "unknown":
            result = await self.db.execute(
                select(CommunicationLog).where(
                    CommunicationLog.partner_message_id == partner_message_id
                )
            )
            comm_log = result.scalar_one_or_none()

        # 5. Persist event
        event = EventLog(
            comm_send_id=comm_log.comm_send_id if comm_log else None,
            event_type=event_type,
            partner=partner,
            partner_message_id=partner_message_id,
            idempotency_key=idempotency_key,
            payload_ref=json.dumps(payload),
            lead_id=comm_log.lead_id if comm_log else None,
        )
        self.db.add(event)

        # 6. Update comm_log status
        if comm_log:
            status_map = {
                "comm.delivered": "delivered",
                "comm.read": "read",
                "comm.clicked": "clicked",
                "comm.failed": "failed",
            }
            new_status = status_map.get(event_type)
            if new_status:
                comm_log.status = new_status

        await self.db.flush()
        logger.info(
            "Webhook event processed",
            event_type=event_type,
            partner=partner,
            message_id=partner_message_id,
        )

    def _verify_signature(
        self, partner: str, body: bytes, signature: Optional[str]
    ) -> bool:
        """HMAC-SHA256 signature verification. Returns True if valid or no secret configured."""
        secret = settings.webhook_secret_for(partner)
        if not secret or secret.startswith("changeme"):
            import structlog as _sl
            _sl.get_logger(__name__).warning(
                "Webhook HMAC secret not configured for partner; skipping signature check (dev mode only)",
                partner=partner,
            )
            return True  # No secret configured – allow (dev mode)
        if not signature:
            return False
        expected = hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature.lower().removeprefix("sha256="))
