from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core import normalization


def _write_invalid_converters(path: Path) -> None:
    payload = {"version": "1", "converters": [{"converter_id": "x"}]}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_invalid_formats(path: Path) -> None:
    payload = {"version": "1", "formats": [{"format_id": "x"}]}
    path.write_text(json.dumps(payload), encoding="utf-8")


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
