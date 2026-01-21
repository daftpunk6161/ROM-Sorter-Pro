import sys
import pytest
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.integration


def test_run_scan_with_real_files(tmp_path):
    from src.app.controller import run_scan

    source = tmp_path / "source"
    source.mkdir()

    rom = source / "game.nes"
    rom.write_text("data")

    result = run_scan(str(source))

    assert result.items, "Expected at least one ROM"
    assert any(Path(item.input_path).name == "game.nes" for item in result.items)


def test_execute_sort_overwrite_policy(tmp_path):
    from src.app.controller import ScanItem, ScanResult, execute_sort, plan_sort

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "game.rom"
    rom.write_text("new")

    existing = dest / "NES" / "game.rom"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("old")

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    plan = plan_sort(scan, str(dest), mode="copy", on_conflict="overwrite")
    report = execute_sort(plan, dry_run=False)

    assert report.cancelled is False
    assert existing.read_text() == "new"
