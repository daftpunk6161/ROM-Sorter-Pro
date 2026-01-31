from pathlib import Path

from src.app.controller import ScanItem
from src.ui.mvp.model_utils import format_reason


def test_format_reason_low_confidence() -> None:
    item = ScanItem(
        input_path=str(Path("/tmp/game.rom")),
        detected_system="Unknown",
        detection_source="policy-low-confidence",
        detection_confidence=0.3,
        raw={},
    )

    reason = format_reason(item, min_confidence=0.95)

    assert reason == "low-confidence (<0.95)"


def test_format_reason_maps_signals() -> None:
    item = ScanItem(
        input_path=str(Path("/tmp/game.rom")),
        detected_system="Unknown",
        detection_source="",
        detection_confidence=None,
        raw={"signals": ["NO_DAT_MATCH", "EXTENSION_UNKNOWN"]},
    )

    reason = format_reason(item, min_confidence=0.95)

    assert "keine DAT-Übereinstimmung" in reason
    assert "Dateiendung unbekannt" in reason