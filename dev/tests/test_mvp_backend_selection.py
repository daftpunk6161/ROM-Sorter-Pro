import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_select_backend_prefers_tk_when_no_qt(monkeypatch):
    from src.ui import compat

    monkeypatch.setattr(compat, "_detect_qt_binding", lambda: None)
    assert compat.select_backend(None) == "tk"


def test_select_backend_honors_explicit(monkeypatch):
    from src.ui import compat

    monkeypatch.setattr(compat, "_detect_qt_binding", lambda: None)
    assert compat.select_backend("qt") == "qt"
    assert compat.select_backend("tk") == "tk"
