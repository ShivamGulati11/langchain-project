"""LangGraph-based NBFC dedupe waterfall chain."""
from __future__ import annotations

import uuid
from typing import Any, TypedDict

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# ── State schema ──────────────────────────────────────────────────────────────


class DedupeState(TypedDict):
    lead_id: str
    nbfc_priority: list[str]
    current_index: int
    outcome: str  # PASS | FAIL | ERROR | PENDING
    winning_nbfc_id: str | None
    error: str | None


# ── Node functions ────────────────────────────────────────────────────────────


def _build_graph():
    """Build and compile the LangGraph dedupe waterfall graph."""
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError:
        return None

    graph = StateGraph(DedupeState)

    async def check_nbfc(state: DedupeState) -> DedupeState:
        """Call the current NBFC in the priority list."""
        idx = state["current_index"]
        nbfc_list = state["nbfc_priority"]

        if idx >= len(nbfc_list):
            return {**state, "outcome": "FAIL"}

        nbfc_id = nbfc_list[idx]
        lead_id = uuid.UUID(state["lead_id"])

        try:
            from app.integrations.nbfc.base import get_nbfc_adapter

            adapter = get_nbfc_adapter(nbfc_id)
            result = await adapter.check(lead_id=lead_id)
            outcome = result.get("outcome", "ERROR")
        except Exception as exc:
            logger.error("NBFC adapter error", nbfc_id=nbfc_id, error=str(exc))
            outcome = "ERROR"

        if outcome == "PASS":
            return {
                **state,
                "outcome": "PASS",
                "winning_nbfc_id": nbfc_id,
            }
        return {
            **state,
            "outcome": outcome,
            "current_index": idx + 1,
        }

    def route(state: DedupeState) -> str:
        if state["outcome"] == "PASS":
            return "done"
        if state["current_index"] >= len(state["nbfc_priority"]):
            return "done"
        return "check_nbfc"

    graph.add_node("check_nbfc", check_nbfc)
    graph.add_edge(START, "check_nbfc")
    graph.add_conditional_edges("check_nbfc", route, {"check_nbfc": "check_nbfc", "done": END})

    return graph.compile()


_compiled_graph = None


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph()
    return _compiled_graph


# ── Public entry point ────────────────────────────────────────────────────────


async def run_dedupe_chain(lead_id: uuid.UUID, db: AsyncSession) -> str:
    """
    Execute the full NBFC waterfall for a lead.
    Returns final outcome: PASS | FAIL | ERROR
    """
    from app.services.config_manager import ConfigManagerService
    from app.services.dedupe import DedupeService
    from app.services.qualification import QualificationService

    config_svc = ConfigManagerService(db)
    nbfc_priority = await config_svc.get_nbfc_priority()

    initial_state: DedupeState = {
        "lead_id": str(lead_id),
        "nbfc_priority": nbfc_priority,
        "current_index": 0,
        "outcome": "PENDING",
        "winning_nbfc_id": None,
        "error": None,
    }

    graph = _get_graph()
    if graph is None:
        # LangGraph not available – fall back to direct loop
        return await _fallback_waterfall(lead_id, nbfc_priority, db)

    final_state = await graph.ainvoke(initial_state)

    dedupe_svc = DedupeService(db)
    qual_svc = QualificationService(db)
    outcome = final_state["outcome"]

    # Record a summary log entry
    await dedupe_svc.record_attempt(
        lead_id=lead_id,
        nbfc_id=final_state.get("winning_nbfc_id") or "none",
        outcome=outcome,
    )

    if outcome == "PASS":
        await qual_svc.handle_pass(lead_id, final_state["winning_nbfc_id"])
    else:
        await qual_svc.handle_all_fail(lead_id)

    return outcome


async def _fallback_waterfall(
    lead_id: uuid.UUID, nbfc_priority: list[str], db: AsyncSession
) -> str:
    """Simple sequential fallback when LangGraph is unavailable."""
    from app.integrations.nbfc.base import get_nbfc_adapter
    from app.services.dedupe import DedupeService
    from app.services.qualification import QualificationService

    dedupe_svc = DedupeService(db)
    qual_svc = QualificationService(db)

    for nbfc_id in nbfc_priority:
        try:
            adapter = get_nbfc_adapter(nbfc_id)
            result = await adapter.check(lead_id=lead_id)
            outcome = result.get("outcome", "ERROR")
        except Exception as exc:
            outcome = "ERROR"
            await dedupe_svc.record_attempt(lead_id, nbfc_id, "ERROR", error_detail=str(exc))
            continue

        await dedupe_svc.record_attempt(lead_id, nbfc_id, outcome)
        if outcome == "PASS":
            await qual_svc.handle_pass(lead_id, nbfc_id)
            return "PASS"

    await qual_svc.handle_all_fail(lead_id)
    return "FAIL"
