import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_gui_smoke_selects_backend():
    import start_rom_sorter

    selected = start_rom_sorter.gui_smoke("qt")
    assert selected == "qt"
