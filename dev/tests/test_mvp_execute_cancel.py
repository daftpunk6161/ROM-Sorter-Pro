import sys
import pytest
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.integration


def test_execute_sort_cancelled_before_start_creates_no_files(tmp_path):
    # Mutation-proof: ignoring cancel_token should fail this test.
    from src.app.controller import CancelToken, ScanItem, ScanResult, execute_sort, plan_sort

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

    token = CancelToken()
    token.cancel()

    report = execute_sort(plan, cancel_token=token, dry_run=False)

    assert report.cancelled is True
    # No destination subdir/file should be created when cancelled up-front.
    assert not (dest / "NES").exists()
