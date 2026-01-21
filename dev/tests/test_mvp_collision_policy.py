from __future__ import annotations

from pathlib import Path

import pytest

from src.app.controller import ScanItem, ScanResult, plan_sort


@pytest.mark.integration
def test_plan_sort_rename_conflict(tmp_path: Path) -> None:
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "game.nes"
    rom.write_text("data", encoding="utf-8")

    existing_dir = dest / "NES"
    existing_dir.mkdir()
    existing = existing_dir / "game.nes"
    existing.write_text("existing", encoding="utf-8")

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
    assert len(plan.actions) == 1
    target = plan.actions[0].planned_target_path
    assert target is not None
    assert target.endswith("NES\\game (1).nes") or target.endswith("NES/game (1).nes")


@pytest.mark.integration
def test_plan_sort_skip_conflict(tmp_path: Path) -> None:
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "game.nes"
    rom.write_text("data", encoding="utf-8")

    existing_dir = dest / "NES"
    existing_dir.mkdir()
    existing = existing_dir / "game.nes"
    existing.write_text("existing", encoding="utf-8")

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    plan = plan_sort(scan, str(dest), mode="copy", on_conflict="skip")
    assert len(plan.actions) == 1
    action = plan.actions[0]
    assert action.planned_target_path is None
    assert action.status.startswith("skipped")
