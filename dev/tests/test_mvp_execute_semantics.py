import sys
import pytest
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.integration


def test_execute_sort_dry_run_creates_no_files(tmp_path):
    # Mutation-proof: removing dry_run guard should fail this test.
    from src.app.controller import ScanItem, ScanResult, execute_sort, plan_sort

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "game.rom"
    rom.write_text("x")

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
    report = execute_sort(plan, dry_run=True)

    assert report.cancelled is False
    assert not (dest / "NES" / "game.rom").exists()


def test_execute_sort_move_deletes_source(tmp_path):
    # Mutation-proof: changing conflict policy to always overwrite should alter expectations in related tests.
    from src.app.controller import ScanItem, ScanResult, execute_sort, plan_sort

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "game.rom"
    rom.write_text("x")

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    plan = plan_sort(scan, str(dest), mode="move", on_conflict="overwrite")
    report = execute_sort(plan, dry_run=False)

    assert report.cancelled is False
    assert not rom.exists()
    assert (dest / "NES" / "game.rom").exists()


def test_execute_sort_conversion_requires_output(tmp_path):
    from src.app.controller import SortAction, SortPlan, execute_sort

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "game.rom"
    rom.write_text("x")

    target = dest / "NES" / "game.chd"

    plan = SortPlan(
        dest_path=str(dest),
        mode="copy",
        on_conflict="rename",
        actions=[
            SortAction(
                input_path=str(rom),
                detected_system="NES",
                planned_target_path=str(target),
                action="convert",
                status="planned (convert)",
                conversion_tool=sys.executable,
                conversion_tool_key="python",
                conversion_args=["-c", "print('ok')"],
                conversion_rule="test",
                conversion_output_extension=".chd",
            )
        ],
    )

    report = execute_sort(plan, dry_run=False)

    assert report.errors
    assert any("output missing" in msg for msg in report.errors)
    assert not target.exists()


def test_execute_sort_dry_run_skips_conversion_tool(tmp_path):
    from src.app.controller import SortAction, SortPlan, execute_sort

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "game.rom"
    rom.write_text("x")

    marker = tmp_path / "ran.txt"
    target = dest / "NES" / "game.chd"

    plan = SortPlan(
        dest_path=str(dest),
        mode="copy",
        on_conflict="rename",
        actions=[
            SortAction(
                input_path=str(rom),
                detected_system="NES",
                planned_target_path=str(target),
                action="convert",
                status="planned (convert)",
                conversion_tool=sys.executable,
                conversion_tool_key="python",
                conversion_args=["-c", f"open(r'{marker}', 'w').write('x')"],
                conversion_rule="test",
                conversion_output_extension=".chd",
            )
        ],
    )

    report = execute_sort(plan, dry_run=True)

    assert report.errors == []
    assert not marker.exists()


def test_execute_external_tools_dry_run_skips_missing_exe(tmp_path):
    from src.app.controller import SortAction, SortPlan, execute_external_tools

    source = tmp_path / "source"
    source.mkdir()

    rom = source / "game.wud"
    rom.write_text("x")

    out_dir = tmp_path / "out"

    plan = SortPlan(
        dest_path=str(tmp_path / "dest"),
        mode="copy",
        on_conflict="rename",
        actions=[
            SortAction(
                input_path=str(rom),
                detected_system="WiiU",
                planned_target_path=str(out_dir / "game"),
                action="convert",
                status="planned (convert)",
                conversion_tool=None,
                conversion_tool_key="wud2app",
                conversion_args=None,
                conversion_rule="test",
                conversion_output_extension=None,
            )
        ],
    )

    report = execute_external_tools(plan, output_dir=str(out_dir), temp_dir=None, dry_run=True)

    assert report.failed == 0
    assert report.succeeded == 1
    assert not report.errors
    assert not out_dir.exists()
