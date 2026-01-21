"""Shared export helpers for MVP UI (Qt/Tk)."""

from __future__ import annotations

import csv
import json
from typing import Any

from ...app.api import ConversionAuditReport, ScanResult, SortPlan


def audit_report_to_dict(report: ConversionAuditReport) -> dict[str, Any]:
    return {
        "source_path": report.source_path,
        "totals": report.totals,
        "cancelled": report.cancelled,
        "items": [
            {
                "input_path": item.input_path,
                "detected_system": item.detected_system,
                "current_extension": item.current_extension,
                "recommended_extension": item.recommended_extension,
                "rule_name": item.rule_name,
                "tool_key": item.tool_key,
                "status": item.status,
                "reason": item.reason,
            }
            for item in report.items
        ],
    }


def scan_report_to_dict(scan: ScanResult) -> dict[str, Any]:
    return {
        "source_path": scan.source_path,
        "stats": scan.stats,
        "cancelled": scan.cancelled,
        "items": [
            {
                "input_path": item.input_path,
                "detected_system": item.detected_system,
                "detection_source": item.detection_source,
                "detection_confidence": item.detection_confidence,
                "is_exact": getattr(item, "is_exact", False),
                "signals": (item.raw or {}).get("signals") if item.raw else None,
                "candidates": (item.raw or {}).get("candidates") if item.raw else None,
            }
            for item in scan.items
        ],
    }


def plan_report_to_dict(plan: SortPlan) -> dict[str, Any]:
    return {
        "dest_path": plan.dest_path,
        "mode": plan.mode,
        "on_conflict": plan.on_conflict,
        "actions": [
            {
                "input_path": action.input_path,
                "detected_system": action.detected_system,
                "planned_target_path": action.planned_target_path,
                "action": action.action,
                "status": action.status,
                "error": action.error,
                "conversion_rule": action.conversion_rule,
                "conversion_tool": action.conversion_tool_key,
                "conversion_output_extension": action.conversion_output_extension,
            }
            for action in plan.actions
        ],
    }


def write_json(payload: dict[str, Any], filename: str) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def write_scan_csv(scan: ScanResult, filename: str) -> None:
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "input_path",
                "detected_system",
                "detection_source",
                "detection_confidence",
                "is_exact",
                "signals",
                "candidates",
            ]
        )
        for item in scan.items:
            raw = item.raw or {}
            signals = raw.get("signals") or []
            candidates = raw.get("candidates") or []
            writer.writerow(
                [
                    item.input_path,
                    item.detected_system,
                    item.detection_source,
                    item.detection_confidence,
                    getattr(item, "is_exact", False),
                    ", ".join(str(s) for s in signals[:10]),
                    ", ".join(str(c) for c in candidates[:10]),
                ]
            )


def write_plan_csv(plan: SortPlan, filename: str) -> None:
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "input_path",
                "detected_system",
                "planned_target_path",
                "action",
                "status",
                "error",
                "conversion_rule",
                "conversion_tool",
                "conversion_output_extension",
            ]
        )
        for action in plan.actions:
            writer.writerow(
                [
                    action.input_path,
                    action.detected_system,
                    action.planned_target_path,
                    action.action,
                    action.status,
                    action.error,
                    action.conversion_rule,
                    action.conversion_tool_key,
                    action.conversion_output_extension,
                ]
            )


def write_audit_csv(report: ConversionAuditReport, filename: str) -> None:
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "input_path",
                "detected_system",
                "current_extension",
                "recommended_extension",
                "rule_name",
                "tool_key",
                "status",
                "reason",
            ]
        )
        for item in report.items:
            writer.writerow(
                [
                    item.input_path,
                    item.detected_system,
                    item.current_extension,
                    item.recommended_extension,
                    item.rule_name,
                    item.tool_key,
                    item.status,
                    item.reason,
                ]
            )
