import json
import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.scan_service import run_scan  # noqa: E402
from src.config import Config  # noqa: E402


pytestmark = pytest.mark.integration


def test_incremental_scan_seeds_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source"
    source.mkdir()
    rom = source / "game.rom"
    rom.write_text("data", encoding="utf-8")

    resume_path = tmp_path / "last_scan_resume.json"
    resume_payload = {
        "source_path": str(source),
        "stats": {},
        "cancelled": False,
        "items": [
            {
                "input_path": str(rom),
                "detected_system": "NES",
                "detection_source": "extension",
                "detection_confidence": 0.5,
                "raw": {
                    "path": str(rom),
                    "system": "NES",
                    "detection_confidence": 0.5,
                    "detection_source": "extension",
                },
            }
        ],
    }
    resume_path.write_text(json.dumps(resume_payload), encoding="utf-8")

    seeded = {"count": 0}

    def _fake_save(self, file_path, rom_info, file_stat=None):
        seeded["count"] += 1

    monkeypatch.setattr("src.scanning.high_performance_scanner.HighPerformanceScanner._save_to_cache", _fake_save)

    cfg = Config(
        {
            "features": {
                "scan": {"incremental": True},
                "progress_persistence": {"scan_resume_path": str(resume_path)},
            }
        }
    )

    result = run_scan(str(source), config=cfg)
    assert result["source"] == str(source)
    assert seeded["count"] >= 1
