import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_backend_worker_handle_cancel_calls_token():
    from src.app.controller import CancelToken
    from src.ui.backend_worker import BackendWorkerHandle

    token = CancelToken()

    class DummyThread:
        def is_alive(self):
            return True

    handle = BackendWorkerHandle(DummyThread(), token)
    assert token.is_cancelled() is False
    handle.cancel()
    assert token.is_cancelled() is True
