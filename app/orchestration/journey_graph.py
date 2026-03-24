"""LangGraph journey state machine."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class JourneyState(TypedDict):
    journey_id: str
    lead_id: str
    current_step_index: int
    steps: list[dict[str, Any]]
    state: str  # running | completed | stopped | failed
    error: str | None


def _build_journey_graph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError:
        return None

    graph = StateGraph(JourneyState)

    async def execute_step(state: JourneyState) -> JourneyState:
        steps = state["steps"]
        idx = state["current_step_index"]

        if idx >= len(steps):
            return {**state, "state": "completed"}

        step = steps[idx]
        channel = step.get("channel", "sms")
        partners = step.get("partners", [])
        lead_id = uuid.UUID(state["lead_id"])
        journey_id = uuid.UUID(state["journey_id"])

        success = False
        for partner in partners:
            try:
                from app.integrations.communication.base import get_comm_adapter

                adapter = get_comm_adapter(channel, partner)
                await adapter.send(
                    lead_id=lead_id,
                    comm_send_id=None,
                    template_id=step.get("template_id"),
                    params={},
                )
                success = True
                break
            except Exception as exc:
                logger.warning("Comm step partner failed", partner=partner, error=str(exc))

        if not success:
            logger.error("All partners failed for step", step_index=idx)
            return {**state, "state": "failed"}

        return {**state, "current_step_index": idx + 1}

    def route_after_step(state: JourneyState) -> str:
        if state["state"] in ("completed", "failed", "stopped"):
            return "done"
        if state["current_step_index"] >= len(state["steps"]):
            return "done"
        return "next_step"

    graph.add_node("execute_step", execute_step)
    graph.add_edge(START, "execute_step")
    graph.add_conditional_edges(
        "execute_step",
        route_after_step,
        {"next_step": "execute_step", "done": END},
    )

    return graph.compile()


_compiled_journey_graph = None


def _get_journey_graph():
    global _compiled_journey_graph
    if _compiled_journey_graph is None:
        _compiled_journey_graph = _build_journey_graph()
    return _compiled_journey_graph


async def run_journey_step(journey_id: uuid.UUID, db: AsyncSession) -> None:
    """Execute the next step of a journey instance."""
    from sqlalchemy import select

    from app.models.journey import JourneyInstance
    from app.services.config_manager import ConfigManagerService

    result = await db.execute(
        select(JourneyInstance).where(JourneyInstance.id == journey_id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        logger.error("Journey instance not found", journey_id=str(journey_id))
        return

    config_svc = ConfigManagerService(db)
    active_config = await config_svc.get_active_config()
    steps: list[dict] = []
    if active_config and active_config.comm_sequence:
        steps = json.loads(active_config.comm_sequence).get("sequence", [])

    if not steps:
        instance.state = "completed"
        await db.flush()
        return

    graph = _get_journey_graph()
    if graph is None:
        # Fallback – mark as running
        instance.state = "running"
        await db.flush()
        return

    initial: JourneyState = {
        "journey_id": str(journey_id),
        "lead_id": str(instance.lead_id),
        "current_step_index": instance.current_step_index,
        "steps": steps,
        "state": "running",
        "error": None,
    }

    final = await graph.ainvoke(initial)
    instance.current_step_index = final["current_step_index"]
    instance.state = final["state"]
    await db.flush()
    logger.info(
        "Journey step executed",
        journey_id=str(journey_id),
        final_state=final["state"],
        step_index=final["current_step_index"],
    )
