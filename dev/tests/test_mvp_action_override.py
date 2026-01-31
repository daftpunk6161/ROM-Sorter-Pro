import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.integration


def test_execute_sort_respects_action_override_copy(tmp_path):
    from src.app.controller import SortAction, SortPlan, execute_sort

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    src_file = source_dir / "game.rom"
    src_file.write_text("data", encoding="utf-8")
    dest_file = dest_root / "game.rom"

    action = SortAction(
        input_path=str(src_file),
        detected_system="NES",
        planned_target_path=str(dest_file),
        action="copy",
        status="planned",
    )

    plan = SortPlan(
        dest_path=str(dest_root),
        mode="move",
        on_conflict="rename",
        actions=[action],
    )

    report = execute_sort(plan, dry_run=False)

    assert dest_file.exists()
    assert src_file.exists()
    assert report.copied == 1
    assert report.moved == 0
