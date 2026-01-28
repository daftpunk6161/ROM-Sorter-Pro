import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_execute_sort_dry_run_skips_external_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.app.controller import SortAction, SortPlan, execute_sort
    import src.app.controller as controller

    src = tmp_path / "source.rom"
    src.write_text("data", encoding="utf-8")

    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    action = SortAction(
        input_path=str(src),
        detected_system="Unknown",
        planned_target_path=str(dest_root / "out.wud"),
        action="convert",
        status="planned",
        conversion_tool="wud2app",
        conversion_tool_key="wud2app",
        conversion_args=["--help"],
        error=None,
    )

    plan = SortPlan(
        dest_path=str(dest_root),
        mode="copy",
        on_conflict="rename",
        actions=[action],
    )

    def _fail(*_args, **_kwargs):
        raise AssertionError("External tool should not run during dry-run")

    monkeypatch.setattr(controller, "run_wud2app", _fail)
    monkeypatch.setattr(controller, "run_wudcompress", _fail)

    report = execute_sort(plan, dry_run=True)
    assert report.processed == 1
    assert report.cancelled is False
    assert not (dest_root / "out.wud").exists()


def test_dry_run_creates_no_dirs(tmp_path: Path) -> None:
    from src.app.controller import ScanItem, ScanResult, execute_sort, plan_sort

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "game.rom"
    rom.write_text("x", encoding="utf-8")

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
    report = execute_sort(plan, dry_run=True)

    assert report.processed == 1
    assert not (dest / "NES").exists()
