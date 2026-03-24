"""Generic state machine helpers (used by journey and dedupe)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class State:
    name: str
    is_terminal: bool = False


@dataclass
class Transition:
    from_state: str
    event: str
    to_state: str
    action: Optional[Callable] = None


class StateMachine:
    """Simple finite state machine used as a fallback / standalone utility."""

    def __init__(self, initial_state: str) -> None:
        self.current_state = initial_state
        self._states: dict[str, State] = {}
        self._transitions: dict[tuple[str, str], Transition] = {}

    def add_state(self, state: State) -> "StateMachine":
        self._states[state.name] = state
        return self

    def add_transition(self, transition: Transition) -> "StateMachine":
        key = (transition.from_state, transition.event)
        self._transitions[key] = transition
        return self

    def trigger(self, event: str, **kwargs: Any) -> Optional[str]:
        key = (self.current_state, event)
        transition = self._transitions.get(key)
        if not transition:
            raise ValueError(
                f"No transition from state '{self.current_state}' on event '{event}'"
            )
        if transition.action:
            transition.action(**kwargs)
        self.current_state = transition.to_state
        return self.current_state

    @property
    def is_terminal(self) -> bool:
        state = self._states.get(self.current_state)
        return state.is_terminal if state else False
