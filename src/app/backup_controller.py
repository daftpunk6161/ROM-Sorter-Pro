"""Backup facade for sort reports and rollback manifests."""

from __future__ import annotations

from typing import Optional

from .models import SortPlan, SortReport
from ..utils.backup_utils import backup_json


def backup_sort_report(
    sort_plan: SortPlan,
    report: SortReport,
    *,
    cfg: Optional[dict] = None,
    log_cb=None,
) -> Optional[str]:
    payload = {
        "kind": "sort_report",
        "dest_path": report.dest_path,
        "mode": report.mode,
        "on_conflict": report.on_conflict,
        "processed": report.processed,
        "copied": report.copied,
        "moved": report.moved,
        "overwritten": report.overwritten,
        "renamed": report.renamed,
        "skipped": report.skipped,
        "errors": report.errors,
        "cancelled": report.cancelled,
        "actions": [
            {
                "input_path": action.input_path,
                "detected_system": action.detected_system,
                "planned_target_path": action.planned_target_path,
                "action": action.action,
                "status": action.status,
                "error": action.error,
            }
            for action in sort_plan.actions
        ],
    }

    result = backup_json(payload, prefix="sort_report", cfg=cfg, log_cb=log_cb)
    return str(result) if result else None
