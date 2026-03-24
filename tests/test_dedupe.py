"""Tests for NBFC dedupe."""
from __future__ import annotations

import uuid
import pytest

from app.utils.idempotency import build_dedupe_idempotency_key
from app.orchestration.state_machine import State, StateMachine, Transition


def test_build_dedupe_idempotency_key():
    lead_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
    key = build_dedupe_idempotency_key(lead_id, "NBFC_A")
    assert key == f"dedupe:{lead_id}:NBFC_A"


def test_state_machine_basic():
    sm = StateMachine("new")
    sm.add_state(State("new"))
    sm.add_state(State("deduping"))
    sm.add_state(State("qualified", is_terminal=True))
    sm.add_state(State("rejected", is_terminal=True))
    sm.add_transition(Transition("new", "start_dedupe", "deduping"))
    sm.add_transition(Transition("deduping", "pass", "qualified"))
    sm.add_transition(Transition("deduping", "all_fail", "rejected"))

    sm.trigger("start_dedupe")
    assert sm.current_state == "deduping"
    sm.trigger("pass")
    assert sm.current_state == "qualified"
    assert sm.is_terminal


def test_state_machine_invalid_transition():
    sm = StateMachine("new")
    sm.add_state(State("new"))
    with pytest.raises(ValueError):
        sm.trigger("invalid_event")


@pytest.mark.asyncio
async def test_dedupe_service_record_attempt(db_session):
    from app.models.lead import Lead
    from app.services.dedupe import DedupeService

    # Create a lead first
    lead = Lead(phone_e164="+911234567890", status="new")
    db_session.add(lead)
    await db_session.flush()

    svc = DedupeService(db_session)
    log = await svc.record_attempt(lead.lead_id, "NBFC_A", "PASS")
    assert log.outcome == "PASS"
    assert log.nbfc_id == "NBFC_A"
    assert log.lead_id == lead.lead_id
