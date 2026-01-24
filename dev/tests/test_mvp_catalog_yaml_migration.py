import json
import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core import platform_heuristics  # noqa: E402

pytestmark = pytest.mark.integration


def test_catalog_json_migrates_to_yaml(monkeypatch, tmp_path):
    yaml_path = tmp_path / "platform_catalog.yaml"
    json_path = tmp_path / "platform_catalog.json"

    catalog = {
        "version": "1.0",
        "platforms": [
            {
                "platform_id": "nes",
                "canonical_name": "Nintendo Entertainment System",
                "aliases": [],
                "category": "No-Intro",
                "media_types": [],
                "allowed_containers": ["raw"],
                "typical_extensions": [".nes"],
                "positive_tokens": [],
                "negative_tokens": [],
                "conflict_groups": [],
                "minimum_signals": []
            }
        ]
    }
    json_path.write_text(json.dumps(catalog), encoding="utf-8")

    monkeypatch.setattr(platform_heuristics, "_catalog_yaml_path", lambda: yaml_path)
    monkeypatch.setattr(platform_heuristics, "_catalog_json_path", lambda: json_path)
    platform_heuristics._load_catalog.cache_clear()

    result = platform_heuristics.evaluate_platform_candidates("game.nes")

    assert yaml_path.exists()
    assert "nes" in result.get("candidate_systems", [])
