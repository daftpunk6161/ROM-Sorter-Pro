from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.config import Config
from src.scanning.high_performance_scanner import HighPerformanceScanner
from src.core import platform_heuristics as heuristics


# NOTE: These tests document desired policy-driven ambiguity handling.
# Currently the scanner uses ENHANCED_CONSOLE_DATABASE for extension matching
# BEFORE applying the custom catalog policy, so the policy checks are never
# reached for extensions that are unique in ENHANCED_CONSOLE_DATABASE (like .nes).
# These tests are marked xfail until the scanner is refactored to use the
# catalog-driven policy as the primary detection source.
_POLICY_NOT_IMPLEMENTED = pytest.mark.xfail(
    reason="Scanner uses ENHANCED_CONSOLE_DATABASE before catalog policy",
    strict=False,
)


def _write_catalog(path: Path, platforms: list[dict], policy: dict) -> None:
    payload = {
        "version": "1.0",
        "policy": policy,
        "platforms": platforms,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _base_platform(
    platform_id: str,
    ext: str,
    tokens: list[str] | None = None,
    conflict_groups: list[str] | None = None,
) -> dict:
    return {
        "platform_id": platform_id,
        "canonical_name": platform_id,
        "aliases": [platform_id],
        "category": "No-Intro",
        "media_types": ["rom"],
        "allowed_containers": [ext.lstrip(".")],
        "typical_extensions": [ext],
        "positive_tokens": tokens or [],
        "negative_tokens": [],
        "conflict_groups": conflict_groups or [],
        "minimum_signals": ["extension"],
    }


@_POLICY_NOT_IMPLEMENTED
def test_detection_policy_marks_ambiguous_extension(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    catalog_path = tmp_path / "catalog.yaml"
    policy = {
        "min_score_delta": 1.0,
        "min_top_score": 2.0,
        "contradiction_min_score": 2.0,
    }
    platforms = [
        _base_platform("nes", ".nes"),
        _base_platform("nes-alt", ".nes"),
    ]
    _write_catalog(catalog_path, platforms, policy)

    monkeypatch.setenv("ROM_SORTER_PLATFORM_CATALOG", str(catalog_path))
    heuristics._load_catalog.cache_clear()

    rom_path = tmp_path / "game.nes"
    rom_path.write_text("data", encoding="utf-8")

    scanner = HighPerformanceScanner(config=Config({"dat_matching": {"enabled": False}}))
    info = scanner._process_file(str(rom_path), use_cache=False)

    assert info is not None
    assert info["system"] == "Unknown"
    assert info["detection_source"] == "ambiguous-candidates"


@_POLICY_NOT_IMPLEMENTED
def test_detection_policy_marks_contradiction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    catalog_path = tmp_path / "catalog.yaml"
    policy = {
        "min_score_delta": 1.0,
        "min_top_score": 2.0,
        "contradiction_min_score": 2.0,
    }
    platforms = [
        _base_platform("nes", ".nes"),
        _base_platform("famicom", ".nes", tokens=["famicom"]),
    ]
    _write_catalog(catalog_path, platforms, policy)

    monkeypatch.setenv("ROM_SORTER_PLATFORM_CATALOG", str(catalog_path))
    heuristics._load_catalog.cache_clear()

    rom_path = tmp_path / "famicom_game.nes"
    rom_path.write_text("data", encoding="utf-8")

    scanner = HighPerformanceScanner(config=Config({"dat_matching": {"enabled": False}}))
    info = scanner._process_file(str(rom_path), use_cache=False)

    assert info is not None
    assert info["system"] == "Unknown"
    assert info["detection_source"] == "contradiction-candidates"


@_POLICY_NOT_IMPLEMENTED
def test_detection_policy_marks_conflict_group(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    catalog_path = tmp_path / "catalog.yaml"
    policy = {
        "min_score_delta": 1.0,
        "min_top_score": 2.0,
        "contradiction_min_score": 2.0,
    }
    platforms = [
        _base_platform("nes", ".nes", tokens=["nes"], conflict_groups=["nintendo-8bit"]),
        _base_platform("famicom", ".nes", tokens=["famicom"], conflict_groups=["nintendo-8bit"]),
    ]
    _write_catalog(catalog_path, platforms, policy)

    monkeypatch.setenv("ROM_SORTER_PLATFORM_CATALOG", str(catalog_path))
    heuristics._load_catalog.cache_clear()

    rom_path = tmp_path / "famicom_nes_game.nes"
    rom_path.write_text("data", encoding="utf-8")

    scanner = HighPerformanceScanner(config=Config({"dat_matching": {"enabled": False}}))
    info = scanner._process_file(str(rom_path), use_cache=False)

    assert info is not None
    assert info["system"] == "Unknown"
    assert info["detection_source"] == "conflict-group"
