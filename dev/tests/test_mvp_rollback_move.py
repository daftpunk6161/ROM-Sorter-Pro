from __future__ import annotations

from pathlib import Path

import pytest

from src.app.controller import execute_sort
from src.app.rollback_controller import apply_rollback
from src.app.models import SortAction, SortPlan

pytestmark = pytest.mark.integration


def test_rollback_move_manifest(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()

    src_file = src_dir / "test.rom"
    src_file.write_bytes(b"DATA")

    planned_target = dst_dir / "test.rom"

    plan = SortPlan(
        dest_path=str(dst_dir),
        mode="move",
        on_conflict="rename",
        actions=[
            SortAction(
                input_path=str(src_file),
                detected_system="Unknown",
                planned_target_path=str(planned_target),
                action="move",
                status="planned",
            )
        ],
    )

    rollback_path = tmp_path / "rollback.json"

    report = execute_sort(plan, dry_run=False, rollback_path=str(rollback_path))
    assert report.moved == 1
    assert planned_target.exists()
    assert not src_file.exists()

    rollback_report = apply_rollback(str(rollback_path))
    assert rollback_report.restored == 1
    assert src_file.exists()
    assert not planned_target.exists()
