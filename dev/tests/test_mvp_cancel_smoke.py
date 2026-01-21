from __future__ import annotations

from pathlib import Path

import pytest

from src.app.controller import CancelToken, SortAction, SortPlan, execute_sort


@pytest.mark.integration
def test_execute_sort_cancel_immediate(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()

    plan = SortPlan(
        dest_path=str(dest),
        mode="copy",
        on_conflict="rename",
        actions=[
            SortAction(
                input_path=str(tmp_path / "file.rom"),
                detected_system="Unknown",
                planned_target_path=str(dest / "file.rom"),
                action="copy",
                status="planned",
                error=None,
            )
        ],
    )

    token = CancelToken()
    token.cancel()

    report = execute_sort(plan, cancel_token=token, dry_run=True)
    assert report.cancelled is True
