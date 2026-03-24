"""Tests for journey state machine."""
from __future__ import annotations

import uuid
import pytest

from app.orchestration.state_machine import State, StateMachine, Transition


def test_journey_state_machine_flow():
    sm = StateMachine("started")
    sm.add_state(State("started"))
    sm.add_state(State("running"))
    sm.add_state(State("completed", is_terminal=True))
    sm.add_state(State("stopped", is_terminal=True))
    sm.add_transition(Transition("started", "begin", "running"))
    sm.add_transition(Transition("running", "complete", "completed"))
    sm.add_transition(Transition("running", "stop", "stopped"))

    sm.trigger("begin")
    assert sm.current_state == "running"
    assert not sm.is_terminal

    sm.trigger("complete")
    assert sm.current_state == "completed"
    assert sm.is_terminal


@pytest.mark.asyncio
async def test_journey_service_start(db_session):
    from app.models.lead import Lead
    from app.services.journey import JourneyService

    lead = Lead(phone_e164="+919999901234", status="qualified", winning_nbfc_id="NBFC_A")
    db_session.add(lead)
    await db_session.flush()

    svc = JourneyService(db_session)
    instance = await svc.start_journey(lead.lead_id, "NBFC_A")
    assert instance.lead_id == lead.lead_id
    assert instance.state in ("started", "running", "completed")


@pytest.mark.asyncio
async def test_journey_service_complete(db_session):
    from app.models.lead import Lead
    from app.models.journey import JourneyInstance
    from app.services.journey import JourneyService

    lead = Lead(phone_e164="+919999901235", status="qualified")
    db_session.add(lead)
    await db_session.flush()

    instance = JourneyInstance(
        lead_id=lead.lead_id, definition_version="v1", state="running", current_step_index=0
    )
    db_session.add(instance)
    await db_session.flush()

    svc = JourneyService(db_session)
    await svc.complete(instance.id)

    result = await svc.get_instance(instance.id)
    assert result.state == "completed"
