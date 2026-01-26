from __future__ import annotations

from pathlib import Path
import sys

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_handle_worker_failure_logs_and_dialog() -> None:
    from src.ui.mvp.qt_app import handle_worker_failure

    logs: list[str] = []
    dialogs: list[tuple[str, str]] = []

    def _log(msg: str) -> None:
        logs.append(msg)

    def _dialog(msg: str, tb: str) -> None:
        dialogs.append((msg, tb))

    handle_worker_failure("boom", "trace", _log, _dialog)

    assert logs == ["boom", "trace"]
    assert dialogs == [("boom", "trace")]