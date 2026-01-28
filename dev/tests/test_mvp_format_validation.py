from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core import normalization
from src.config.schema import JSONSCHEMA_AVAILABLE, validate_config_schema


def _write_invalid_converters(path: Path) -> None:
    payload = {"version": "1", "converters": [{"converter_id": "x"}]}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_invalid_formats(path: Path) -> None:
    payload = {"version": "1", "formats": [{"format_id": "x"}]}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_valid_formats(path: Path) -> None:
    payload = {
        "version": "1.0",
        "formats": [
            {
                "platform_id": "ps3",
                "format_id": "ps3-folder",
                "input_kinds": ["GameFolderSet"],
                "required_manifests": ["PS3_DISC.SFB", "PS3_GAME/PARAM.SFO"],
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_formats_with_preferred_outputs(path: Path) -> None:
    payload = {
        "version": "1.0",
        "formats": [
            {
                "platform_id": "ps2",
                "format_id": "ps2-disc",
                "input_kinds": ["DiscImage"],
                "preferred_outputs": [".cso", ".chd"],
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_converters_with_multiple_outputs(path: Path) -> None:
    payload = {
        "version": "1.0",
        "converters": [
            {
                "converter_id": "iso_to_chd",
                "name": "iso_to_chd",
                "tool_key": "chdman",
                "exe_path": "C:/tools/chdman.exe",
                "enabled": True,
                "platform_ids": ["ps2"],
                "extensions": [".iso"],
                "input_kinds": ["DiscImage"],
                "output_extension": ".chd",
                "args_template": ["createcd", "-i", "{input}", "-o", "{output}"]
            },
            {
                "converter_id": "iso_to_cso",
                "name": "iso_to_cso",
                "tool_key": "maxcso",
                "exe_path": "C:/tools/maxcso.exe",
                "enabled": True,
                "platform_ids": ["ps2"],
                "extensions": [".iso"],
                "input_kinds": ["DiscImage"],
                "output_extension": ".cso",
                "args_template": ["{input}", "{output}"]
            }
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_validate_trackset_reports_missing_bin(tmp_path: Path) -> None:
    cue_path = tmp_path / "disc.cue"
    cue_path.write_text(
        "FILE \"track01.bin\" BINARY\n  TRACK 01 MODE1/2352\n  INDEX 01 00:00:00\n",
        encoding="utf-8",
    )

    missing = normalization.validate_trackset(str(cue_path))
    assert "track01.bin" in missing


def _write_cue(path: Path, files: list[str]) -> None:
    lines = []
    for name in files:
        lines.append(f'FILE "{name}" BINARY')
        lines.append("  TRACK 01 MODE1/2352")
    path.write_text("\n".join(lines), encoding="utf-8")


@pytest.mark.integration
def test_invalid_converters_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    converters_path = tmp_path / "converters.yaml"
    _write_invalid_converters(converters_path)
    monkeypatch.setenv("ROM_SORTER_CONVERTERS", str(converters_path))

    converters = normalization.load_converters()
    assert converters == []


@pytest.mark.integration
def test_invalid_formats_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    formats_path = tmp_path / "platform_formats.yaml"
    _write_invalid_formats(formats_path)
    monkeypatch.setenv("ROM_SORTER_PLATFORM_FORMATS", str(formats_path))

    formats = normalization.load_platform_formats()
    assert formats == []


def test_folderset_missing_manifests_are_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    formats_path = tmp_path / "platform_formats.yaml"
    _write_valid_formats(formats_path)
    monkeypatch.setenv("ROM_SORTER_PLATFORM_FORMATS", str(formats_path))

    game_root = tmp_path / "PS3_GAME_SET"
    game_root.mkdir()
    (game_root / "PS3_GAME").mkdir()

    missing = normalization.validate_folderset(str(game_root), "ps3", normalization.load_platform_formats())
    assert "PS3_DISC.SFB" in missing
    assert "PS3_GAME/PARAM.SFO" in missing


def test_folderset_passes_with_required_manifests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    formats_path = tmp_path / "platform_formats.yaml"
    _write_valid_formats(formats_path)
    monkeypatch.setenv("ROM_SORTER_PLATFORM_FORMATS", str(formats_path))

    game_root = tmp_path / "PS3_GAME_SET"
    game_root.mkdir()
    (game_root / "PS3_DISC.SFB").write_text("stub", encoding="utf-8")
    (game_root / "PS3_GAME").mkdir()
    (game_root / "PS3_GAME" / "PARAM.SFO").write_text("stub", encoding="utf-8")

    missing = normalization.validate_folderset(str(game_root), "ps3", normalization.load_platform_formats())
    assert missing == []


def test_trackset_reports_missing_files(tmp_path: Path) -> None:
    cue = tmp_path / "disc.cue"
    _write_cue(cue, ["track01.bin", "track02.bin"])
    (tmp_path / "track01.bin").write_text("stub", encoding="utf-8")

    missing = normalization.validate_trackset(str(cue))
    assert "track02.bin" in missing
    assert "track01.bin" not in missing


def test_trackset_reports_invalid_paths(tmp_path: Path) -> None:
    cue = tmp_path / "disc.cue"
    _write_cue(cue, ["..\\secret.bin"])

    missing = normalization.validate_trackset(str(cue))
    assert any("invalid-path" in entry for entry in missing)


def test_trackset_reports_empty_entries(tmp_path: Path) -> None:
    cue = tmp_path / "empty.cue"
    cue.write_text("REM EMPTY", encoding="utf-8")

    missing = normalization.validate_trackset(str(cue))
    assert any("no-track-entries" in entry for entry in missing)


def test_plan_normalization_prefers_platform_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    formats_path = tmp_path / "platform_formats.yaml"
    converters_path = tmp_path / "converters.yaml"
    _write_formats_with_preferred_outputs(formats_path)
    _write_converters_with_multiple_outputs(converters_path)
    monkeypatch.setenv("ROM_SORTER_PLATFORM_FORMATS", str(formats_path))
    monkeypatch.setenv("ROM_SORTER_CONVERTERS", str(converters_path))

    rom = tmp_path / "game.iso"
    rom.write_text("data", encoding="utf-8")

    item = normalization.normalize_input(str(rom), platform_hint="ps2")
    plan = normalization.plan_normalization([item])

    assert plan.items
    planned = plan.items[0]
    assert planned.action == "convert"
    assert planned.converter_id == "iso_to_cso"
    assert planned.output_path is not None
    assert planned.output_path.lower().endswith(".cso")


def test_config_schema_validation() -> None:
    if not JSONSCHEMA_AVAILABLE:
        pytest.skip("jsonschema not available")
    ok, error = validate_config_schema({"features": "invalid"})
    assert ok is False
    assert error
