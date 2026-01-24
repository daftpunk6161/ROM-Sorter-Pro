from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from src.core import normalization
from src.app.controller import normalize_input, plan_normalization, execute_normalization, CancelToken


def _write_formats_with_preferred_outputs(path: Path) -> None:
    payload = {
        "version": "1.0",
        "formats": [
            {
                "platform_id": "ps2",
                "format_id": "ps2-disc",
                "input_kinds": ["DiscImage"],
                "preferred_outputs": [".cso"],
            }
        ],
    }
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")


def _write_converters_with_preferred_outputs(path: Path) -> None:
    payload = {
        "version": "1.0",
        "converters": [
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
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")


def test_execute_normalization_returns_item_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    formats_path = tmp_path / "platform_formats.yaml"
    converters_path = tmp_path / "converters.yaml"
    _write_formats_with_preferred_outputs(formats_path)
    _write_converters_with_preferred_outputs(converters_path)
    monkeypatch.setenv("ROM_SORTER_PLATFORM_FORMATS", str(formats_path))
    monkeypatch.setenv("ROM_SORTER_CONVERTERS", str(converters_path))

    rom = tmp_path / "game.iso"
    rom.write_text("data", encoding="utf-8")

    item = normalization.normalize_input(str(rom), platform_hint="ps2")
    plan = normalization.plan_normalization([item])

    report = normalization.execute_normalization(plan, dry_run=True)

    assert report.items
    entry = report.items[0]
    assert entry.input_path == str(rom)
    assert entry.status == "dry-run"
    assert entry.output_path and entry.output_path.lower().endswith(".cso")
    assert report.processed == 1
    assert report.succeeded == 1
    assert report.failed == 0


def _write_converters(path: Path, script_path: Path) -> None:
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
                "exe_path": sys.executable,
                "args_template": [
                    str(script_path),
                    "{input}",
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


@pytest.mark.integration
def test_execute_normalization_runs_converter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = tmp_path / "fake_converter.py"
    script.write_text(
        "import sys, pathlib\n"
        "inp = pathlib.Path(sys.argv[1])\n"
        "outp = pathlib.Path(sys.argv[2])\n"
        "outp.parent.mkdir(parents=True, exist_ok=True)\n"
        "outp.write_bytes(inp.read_bytes())\n",
        encoding="utf-8",
    )

    converters_path = tmp_path / "converters.yaml"
    formats_path = tmp_path / "platform_formats.yaml"
    _write_converters(converters_path, script)
    _write_formats(formats_path)

    monkeypatch.setenv("ROM_SORTER_CONVERTERS", str(converters_path))
    monkeypatch.setenv("ROM_SORTER_PLATFORM_FORMATS", str(formats_path))

    iso_path = tmp_path / "game.iso"
    iso_path.write_text("dummy", encoding="utf-8")

    item = normalize_input(str(iso_path), platform_hint="ps2")
    plan = plan_normalization([item], output_root=str(tmp_path / "out"))

    report = execute_normalization(plan, cancel_token=CancelToken(), dry_run=False)

    assert report.processed == 1
    assert report.succeeded == 1
    assert report.failed == 0
    assert not report.errors

    out_path = Path(plan.items[0].output_path or "")
    assert out_path.exists()
