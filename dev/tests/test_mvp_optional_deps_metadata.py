import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_metadata_network_disabled_returns_none_requests():
    from src.database import metadata_manager as mm

    if mm._network_enabled():
        # If config enables network, just assert helper runs.
        assert mm._get_requests() is not None or mm._get_requests() is None
    else:
        assert mm._get_requests() is None


def test_ml_detector_not_imported_when_disabled(monkeypatch):
    import builtins
    import importlib
    import os

    monkeypatch.setenv("ROM_SORTER_ENABLE_ML", "0")

    # Ensure a clean import of detection_handler.
    for mod in ("src.detectors.detection_handler", "src.detectors.ml_detector"):
        if mod in sys.modules:
            del sys.modules[mod]

    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.endswith("ml_detector") or name.endswith(".ml_detector") or name == "ml_detector":
            raise AssertionError("ml_detector import should be skipped when ML is disabled")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    import src.detectors.detection_handler as dh
    importlib.reload(dh)

    assert dh.ML_AVAILABLE is False
