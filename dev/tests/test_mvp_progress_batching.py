from __future__ import annotations

from pathlib import Path

import pytest

from src.app.controller import SortAction, SortPlan, execute_sort


@pytest.mark.integration
def test_execute_sort_progress_batching(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()

    actions = []
    for i in range(200):
        actions.append(
            SortAction(
                input_path=str(tmp_path / f"src_{i}.rom"),
                detected_system="Unknown",
                planned_target_path=str(dest / f"file_{i}.rom"),
                action="copy",
                status="planned",
                error=None,
            )
        )

    plan = SortPlan(
        dest_path=str(dest),
        mode="copy",
        on_conflict="rename",
        actions=actions,
    )

    calls = []

    def progress_cb(current: int, total: int) -> None:
        calls.append((current, total))

    report = execute_sort(plan, progress_cb=progress_cb, dry_run=True)
    assert report.processed == len(actions)
    assert len(calls) < len(actions)
