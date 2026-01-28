"""Library report helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .models import ScanResult, SortPlan


def build_library_report(
    scan_result: Optional[ScanResult],
    sort_plan: Optional[SortPlan],
) -> Dict[str, Any]:
    report: Dict[str, Any] = {}

    if scan_result is not None:
        total_items = len(scan_result.items)
        unknown_items = 0
        system_counts: Dict[str, int] = {}
        region_counts: Dict[str, int] = {}
        for item in scan_result.items:
            system = (item.detected_system or "Unknown").strip() or "Unknown"
            system_counts[system] = system_counts.get(system, 0) + 1
            if system == "Unknown":
                unknown_items += 1
            region = (item.region or "Unknown").strip() or "Unknown"
            region_counts[region] = region_counts.get(region, 0) + 1
        report["scan"] = {
            "source_path": scan_result.source_path,
            "total_items": total_items,
            "unknown_items": unknown_items,
            "systems": dict(sorted(system_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
            "regions": dict(sorted(region_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
            "cancelled": bool(scan_result.cancelled),
        }

    if sort_plan is not None:
        action_counts: Dict[str, int] = {}
        status_counts: Dict[str, int] = {}
        for action in sort_plan.actions:
            action_label = str(action.action or "unknown")
            action_counts[action_label] = action_counts.get(action_label, 0) + 1
            status_label = str(action.status or "unknown")
            status_counts[status_label] = status_counts.get(status_label, 0) + 1
        report["plan"] = {
            "dest_path": sort_plan.dest_path,
            "mode": sort_plan.mode,
            "on_conflict": sort_plan.on_conflict,
            "total_actions": len(sort_plan.actions),
            "actions": dict(sorted(action_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
            "statuses": dict(sorted(status_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        }

    return report
