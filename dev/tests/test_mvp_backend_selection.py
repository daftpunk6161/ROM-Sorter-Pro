import sys
import types
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


def test_launch_gui_raises_when_both_backends_fail(monkeypatch):
    from src.ui import compat

    def _raise_qt():
        raise RuntimeError("qt-fail")

    def _raise_tk():
        raise RuntimeError("tk-fail")

    qt_mod = types.SimpleNamespace(run=_raise_qt)
    tk_mod = types.SimpleNamespace(run=_raise_tk)

    monkeypatch.setitem(sys.modules, "src.ui.mvp.qt_app", qt_mod)
    monkeypatch.setitem(sys.modules, "src.ui.mvp.tk_app", tk_mod)
    monkeypatch.setattr(compat, "select_backend", lambda _backend=None: "qt")

    try:
        compat.launch_gui("qt")
        assert False, "Expected GUIBackendError"
    except compat.GUIBackendError as exc:
        assert "Qt error" in str(exc)
        assert "Tk error" in str(exc)
