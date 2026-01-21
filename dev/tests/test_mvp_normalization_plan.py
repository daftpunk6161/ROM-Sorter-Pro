import json
from pathlib import Path

import pytest

from src.app.controller import normalize_input, plan_normalization, execute_normalization, CancelToken


def _write_converters(path: Path) -> None:
    payload = {
        "version": "1",
        "converters": [
            {
                "converter_id": "iso2chd",
                "name": "ISO to CHD",
                "enabled": True,
                "input_kinds": ["DiscImage"],
                "platform_ids": ["ps2"],
                "extensions": [".iso"],
                "output_extension": ".chd",
                "exe_path": "C:/tools/chdman.exe",
                "args_template": [
                    "createcd",
                    "-i",
                    "{input}",
                    "-o",
                    "{output}",
                ],
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_formats(path: Path) -> None:
    payload = {
        "version": "1",
        "formats": [
            {
                "platform_id": "ps2",
                "format_id": "ps2-iso",
                "description": "PlayStation 2 ISO",
                "input_kinds": ["DiscImage"],
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_plan_normalization_selects_converter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    converters_path = tmp_path / "converters.yaml"
    formats_path = tmp_path / "platform_formats.yaml"
    _write_converters(converters_path)
    _write_formats(formats_path)

    monkeypatch.setenv("ROM_SORTER_CONVERTERS", str(converters_path))
    monkeypatch.setenv("ROM_SORTER_PLATFORM_FORMATS", str(formats_path))

    iso_path = tmp_path / "game.iso"
    iso_path.write_text("dummy", encoding="utf-8")

    item = normalize_input(str(iso_path), platform_hint="ps2")
    plan = plan_normalization([item], output_root=str(tmp_path / "out"))

    assert len(plan.items) == 1
    planned = plan.items[0]
    assert planned.action == "convert"
    assert planned.output_path is not None
    assert planned.output_path.endswith(".chd")
    assert planned.tool_path is not None
    assert planned.args is not None


def test_execute_normalization_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    converters_path = tmp_path / "converters.yaml"
    formats_path = tmp_path / "platform_formats.yaml"
    _write_converters(converters_path)
    _write_formats(formats_path)

    monkeypatch.setenv("ROM_SORTER_CONVERTERS", str(converters_path))
    monkeypatch.setenv("ROM_SORTER_PLATFORM_FORMATS", str(formats_path))

    iso_path = tmp_path / "game.iso"
    iso_path.write_text("dummy", encoding="utf-8")

    item = normalize_input(str(iso_path), platform_hint="ps2")
    plan = plan_normalization([item], output_root=str(tmp_path / "out"))

    report = execute_normalization(plan, cancel_token=CancelToken(), dry_run=True)

    assert report.processed == 1
    assert report.succeeded == 1
    assert report.failed == 0
    assert not report.errors
