"""Helpers for computing plan statistics."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from .models import SortPlan


def compute_plan_stats(plan: SortPlan) -> Dict[str, int]:
    total_actions = 0
    total_bytes = 0
    for action in plan.actions:
        status = str(action.status or "").lower()
        if status.startswith("skipped") or status.startswith("error"):
            continue
        if not action.planned_target_path:
            continue
        total_actions += 1
        try:
            total_bytes += int(Path(action.input_path).stat().st_size)
        except Exception:
            continue
    return {"total_actions": total_actions, "total_bytes": total_bytes}
