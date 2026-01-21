from __future__ import annotations

from pathlib import Path

import pytest

from src.config import Config
from src.app import controller


@pytest.mark.integration
def test_run_scan_enforces_unknown_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_core_run_scan(*_args, **_kwargs):
        return {
            "source": str(tmp_path),
            "roms": [
                {
                    "path": str(tmp_path / "game.nes"),
                    "system": "NES",
                    "detection_confidence": 0.4,
                    "detection_source": "extension",
                }
            ],
            "stats": {},
            "cancelled": False,
        }

    monkeypatch.setattr(controller, "_core_run_scan", fake_core_run_scan)

    cfg = Config({"features": {"sorting": {"confidence_threshold": 0.9}}})
    result = controller.run_scan(str(tmp_path), config=cfg)
    assert len(result.items) == 1
    item = result.items[0]
    assert item.detected_system == "Unknown"
    assert item.detection_source == "policy-low-confidence"
