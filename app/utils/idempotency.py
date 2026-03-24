"""Idempotency key builders."""
from __future__ import annotations

import uuid
from typing import Optional


def build_dedupe_idempotency_key(lead_id: uuid.UUID, nbfc_id: str) -> str:
    return f"dedupe:{lead_id}:{nbfc_id}"


def build_comm_idempotency_key(
    lead_id: uuid.UUID,
    channel: str,
    partner: str,
    journey_instance_id: Optional[uuid.UUID] = None,
) -> str:
    suffix = str(journey_instance_id) if journey_instance_id else "no-journey"
    return f"comm:{lead_id}:{channel}:{partner}:{suffix}"


def build_webhook_idempotency_key(partner: str, message_id: str, event_type: str) -> str:
    return f"webhook:{partner}:{message_id}:{event_type}"
