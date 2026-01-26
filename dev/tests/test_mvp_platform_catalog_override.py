import json
import sys
from typing import cast
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core import platform_heuristics  # noqa: E402

pytestmark = pytest.mark.integration


def test_platform_catalog_path_override(monkeypatch, tmp_path):
    catalog_path = tmp_path / "catalog.json"
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
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

    monkeypatch.delenv("ROM_SORTER_PLATFORM_CATALOG", raising=False)
    monkeypatch.setattr(platform_heuristics, "load_config", lambda _path=None: {"platform_catalog_path": str(catalog_path)})
    platform_heuristics._load_catalog.cache_clear()

    result = platform_heuristics.evaluate_platform_candidates("game.nes")

    candidates = cast(list[str], result.get("candidate_systems", []))
    assert "nes" in candidates
