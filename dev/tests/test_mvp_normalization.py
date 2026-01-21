from pathlib import Path

import pytest

from src.app.controller import normalize_input


def test_normalize_trackset_missing_files(tmp_path: Path) -> None:
    cue_path = tmp_path / "game.cue"
    cue_path.write_text(
        "FILE \"track01.bin\" BINARY\n  TRACK 01 MODE1/2352\n",
        encoding="utf-8",
    )

    item = normalize_input(str(cue_path))

    assert item.status == "failed"
    assert any(issue.code == "missing-track-file" for issue in item.issues)


def test_normalize_folderset_missing_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    formats_path = tmp_path / "platform_formats.yaml"
    formats_path.write_text(
        """
version: "1"
formats:
  - platform_id: "ps3"
    format_id: "ps3-folder"
    description: "PlayStation 3 folder structure"
    input_kinds: ["GameFolderSet"]
    required_manifests:
      - "PS3_GAME/PARAM.SFO"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("ROM_SORTER_PLATFORM_FORMATS", str(formats_path))

    root = tmp_path / "MyGame"
    (root / "PS3_GAME").mkdir(parents=True)

    item = normalize_input(str(root), platform_hint="ps3")

    assert item.status == "failed"
    assert any(issue.code == "missing-manifest" for issue in item.issues)
