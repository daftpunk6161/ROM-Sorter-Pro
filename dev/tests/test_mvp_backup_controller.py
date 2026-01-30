from __future__ import annotations

from pathlib import Path

import pytest

from src.app.backup_controller import backup_sort_report
from src.app.models import SortAction, SortPlan, SortReport

pytestmark = pytest.mark.integration


def test_backup_sort_report_local_only(tmp_path: Path) -> None:
    plan = SortPlan(
        dest_path=str(tmp_path / "dest"),
        mode="copy",
        on_conflict="rename",
        actions=[
            SortAction(
                input_path=str(tmp_path / "src.rom"),
                detected_system="Unknown",
                planned_target_path=str(tmp_path / "dest" / "src.rom"),
                action="copy",
                status="planned",
            )
        ],
    )
    report = SortReport(
        dest_path=plan.dest_path,
        mode=plan.mode,
        on_conflict=plan.on_conflict,
        processed=1,
        copied=1,
        moved=0,
        overwritten=0,
        renamed=0,
        skipped=0,
        errors=[],
        cancelled=False,
    )

    cfg = {
        "features": {
            "backup": {
                "enabled": True,
                "local_dir": str(tmp_path / "backups"),
                "onedrive_enabled": False,
            }
        }
    }

    path = backup_sort_report(plan, report, cfg=cfg)
    assert path is not None
    assert Path(path).exists()
