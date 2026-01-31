import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ui.mvp.model_utils import format_system_badge  # noqa: E402


def test_format_system_badge_adds_icon() -> None:
    value = format_system_badge("SNES")
    assert value != "SNES"
    assert "SNES" in value


def test_format_system_badge_unknown_passes_through() -> None:
    value = format_system_badge("Unknown")
    assert value == "Unknown"
