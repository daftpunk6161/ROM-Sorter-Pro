import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_ui_state_machine_transitions():
    from src.ui.state_machine import UIStateMachine, UIState

    fsm = UIStateMachine()
    assert fsm.state == UIState.IDLE
    assert fsm.transition(UIState.SCANNING) is True
    assert fsm.state == UIState.SCANNING
    assert fsm.transition(UIState.IDLE) is True
