"""Tests for webhook processing."""
from __future__ import annotations

import hashlib
import hmac
import json
import pytest

from app.utils.idempotency import build_webhook_idempotency_key


def test_build_webhook_idempotency_key():
    key = build_webhook_idempotency_key("msg91", "msg-123", "comm.delivered")
    assert key == "webhook:msg91:msg-123:comm.delivered"


@pytest.mark.asyncio
async def test_sms_webhook_accepted(client):
    payload = {"message_id": "sms-test-001", "status": "delivered"}
    response = await client.post(
        "/webhooks/sms",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json", "x-partner": "msg91"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_whatsapp_webhook_accepted(client):
    payload = {"message_id": "wa-test-001", "status": "READ"}
    response = await client.post(
        "/webhooks/whatsapp",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json", "x-partner": "karix"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_email_webhook_accepted(client):
    payload = {"message_id": "em-test-001", "event": "delivered"}
    response = await client.post(
        "/webhooks/email",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json", "x-partner": "sendgrid"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_webhook_idempotency(client):
    """Same webhook delivered twice should succeed but second is a no-op."""
    payload = {"message_id": "idm-test-001", "status": "delivered"}
    headers = {"Content-Type": "application/json", "x-partner": "msg91"}

    r1 = await client.post(
        "/webhooks/sms", content=json.dumps(payload), headers=headers
    )
    r2 = await client.post(
        "/webhooks/sms", content=json.dumps(payload), headers=headers
    )
    assert r1.status_code == 200
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_event_processor_normalizes_status(db_session):
    from app.services.event_processor import EventProcessorService

    svc = EventProcessorService(db_session)
    raw = json.dumps({"message_id": "test-123", "status": "DELIVERED"}).encode()
    # Should not raise even without a matching comm_send
    await svc.process_partner_webhook(
        channel="whatsapp",
        partner="karix",
        raw_body=raw,
        payload={"message_id": "test-123", "status": "DELIVERED"},
    )
