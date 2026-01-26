import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_gui_smoke_selects_backend():
    import start_rom_sorter

    selected = start_rom_sorter.gui_smoke(None)
    assert selected in ("qt", "tk")


def test_gui_smoke_rejects_unknown_backend(monkeypatch):
    import start_rom_sorter
    from src.ui import compat

    monkeypatch.setattr(compat, "select_backend", lambda _backend=None: "unknown")

    try:
        start_rom_sorter.gui_smoke(None)
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "Unsupported GUI backend" in str(exc)
