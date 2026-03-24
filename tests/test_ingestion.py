"""Tests for lead ingestion."""
from __future__ import annotations

import io
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_single_lead(client):
    payload = {
        "phone_e164": "+919876543210",
        "first_name": "Test",
        "last_name": "User",
        "consent_given": True,
    }
    response = await client.post("/leads/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "new"
    assert data["phone_e164"] == "+919876543210"
    assert "lead_id" in data


@pytest.mark.asyncio
async def test_create_lead_missing_phone_and_email(client):
    """A lead with no phone or email should still be created (validation at row level)."""
    payload = {"first_name": "No Contact"}
    response = await client.post("/leads/", json=payload)
    # FastAPI will accept but the lead will be created without contact info
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_get_lead_not_found(client):
    import uuid

    response = await client.get(f"/leads/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_lead(client):
    payload = {"phone_e164": "+918888888888", "consent_given": True}
    create_resp = await client.post("/leads/", json=payload)
    lead_id = create_resp.json()["lead_id"]

    response = await client.get(f"/leads/{lead_id}")
    assert response.status_code == 200
    assert response.json()["lead_id"] == lead_id


@pytest.mark.asyncio
async def test_upload_csv(client):
    csv_content = b"phone,email,first_name,last_name,consent_given\n+919999999999,,John,Doe,true\n"
    files = {"file": ("leads.csv", io.BytesIO(csv_content), "text/csv")}
    response = await client.post("/leads/upload", files=files)
    assert response.status_code == 202
    data = response.json()
    assert "batch_id" in data
    assert "job_id" in data
