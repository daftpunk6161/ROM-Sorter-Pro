"""UI state machine (minimal FSM)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Set


class UIState(str, Enum):
    IDLE = "idle"
    SCANNING = "scanning"
    PLANNING = "planning"
    EXECUTING = "executing"
    AUDITING = "auditing"
    ERROR = "error"


_ALLOWED: Dict[UIState, Set[UIState]] = {
    UIState.IDLE: {UIState.SCANNING, UIState.PLANNING, UIState.EXECUTING, UIState.AUDITING, UIState.ERROR},
    UIState.SCANNING: {UIState.IDLE, UIState.ERROR},
    UIState.PLANNING: {UIState.IDLE, UIState.ERROR},
    UIState.EXECUTING: {UIState.IDLE, UIState.ERROR},
    UIState.AUDITING: {UIState.IDLE, UIState.ERROR},
    UIState.ERROR: {UIState.IDLE},
}


@dataclass
class UIStateMachine:
    state: UIState = UIState.IDLE

    def can_transition(self, target: UIState) -> bool:
        return target in _ALLOWED.get(self.state, set())

    def transition(self, target: UIState) -> bool:
        if self.can_transition(target):
            self.state = target
            return True
        return False
