import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_qt_legacy_stubs_import_without_qt(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force Qt imports to fail so stub modules must still import.
    import importlib

    real_import = importlib.import_module

    def fake_import(name: str, *args, **kwargs):
        if name.startswith("PySide6") or name.startswith("PyQt5"):
            raise ImportError("Qt not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", fake_import)

    import src.ui.qt.assets as assets
    import src.ui.qt.layouts as layouts
    import src.ui.qt.themes as themes
    import src.ui.qt.typography as typography

    assert assets.label("Scan", "scan") == "🔎 Scan"
    assert isinstance(layouts.LAYOUTS, dict)
    # Check that at least one layout is registered
    assert len(layouts.LAYOUTS) > 0
    assert "beginner_wizard" in layouts.LAYOUTS
    assert isinstance(themes.THEMES, dict)
    assert typography.try_load_font("missing.ttf") is None