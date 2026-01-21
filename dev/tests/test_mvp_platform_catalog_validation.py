from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core import platform_heuristics as heuristics


@pytest.mark.integration
def test_invalid_platform_catalog_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    catalog_path = tmp_path / "catalog.yaml"
    payload = {"version": "1"}
    catalog_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setenv("ROM_SORTER_PLATFORM_CATALOG", str(catalog_path))
    heuristics._load_catalog.cache_clear()

    result = heuristics.evaluate_platform_candidates("C:/roms/nes/SuperMario.nes")
    assert result.get("reason") in {"catalog_invalid", "catalog_empty", "catalog_missing"}
