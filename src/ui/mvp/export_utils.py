"""Shared export helpers for MVP UI (Qt/Tk)."""

from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from defusedxml import ElementTree as ET  # type: ignore[reportMissingImports]
else:
    try:
        from defusedxml import ElementTree as ET  # type: ignore
    except Exception:
        import xml.etree.ElementTree as ET  # nosec B405

ET_ANY = cast(Any, ET)
from pathlib import Path
from typing import Any, Iterable

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


def _iter_planned_actions(plan: SortPlan) -> Iterable[Any]:
    for action in plan.actions:
        if not action.planned_target_path:
            continue
        status = str(action.status or "").lower()
        if status in {"skipped", "error"}:
            continue
        yield action


def _format_plan_path(plan: SortPlan, target_path: str, *, prefer_relative: bool) -> str:
    if not target_path:
        return ""
    raw = Path(target_path)
    try:
        resolved = raw.resolve()
    except Exception:
        resolved = raw
    if prefer_relative:
        try:
            dest_root = Path(plan.dest_path).resolve()
            rel = resolved.relative_to(dest_root)
            return f"./{rel.as_posix()}"
        except Exception:
            return resolved.as_posix()
    return resolved.as_posix()


def write_emulationstation_gamelist(plan: SortPlan, filename: str) -> None:
    """Write a minimal EmulationStation gamelist.xml mapping from a SortPlan."""
    root = ET_ANY.Element("gameList")
    for action in _iter_planned_actions(plan):
        target_path = _format_plan_path(plan, str(action.planned_target_path), prefer_relative=True)
        if not target_path:
            continue
        entry = ET_ANY.SubElement(root, "game")
        ET_ANY.SubElement(entry, "path").text = target_path
        name = Path(str(action.planned_target_path)).stem or Path(str(action.input_path)).stem
        ET_ANY.SubElement(entry, "name").text = name
        ET_ANY.SubElement(entry, "platform").text = str(action.detected_system or "Unknown")
        try:
            from ...app.api import infer_region_from_name, infer_languages_and_version_from_name

            region = infer_region_from_name(str(action.input_path))
            languages, _version = infer_languages_and_version_from_name(str(action.input_path))
            if region:
                ET_ANY.SubElement(entry, "region").text = str(region)
            if languages:
                ET_ANY.SubElement(entry, "lang").text = ",".join(languages)
        except Exception:
            pass

    tree = ET_ANY.ElementTree(root)
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    tree.write(filename, encoding="utf-8", xml_declaration=True)


def write_launchbox_csv(plan: SortPlan, filename: str) -> None:
    """Write a minimal LaunchBox CSV mapping from a SortPlan."""
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "ApplicationPath", "Platform", "Region", "Language"])
        for action in _iter_planned_actions(plan):
            target_path = _format_plan_path(plan, str(action.planned_target_path), prefer_relative=False)
            if not target_path:
                continue
            title = Path(str(action.planned_target_path)).stem or Path(str(action.input_path)).stem
            region = ""
            language = ""
            try:
                from ...app.api import infer_region_from_name, infer_languages_and_version_from_name

                region = infer_region_from_name(str(action.input_path)) or ""
                languages, _version = infer_languages_and_version_from_name(str(action.input_path))
                if languages:
                    language = ",".join(languages)
            except Exception:
                region = ""
                language = ""
            writer.writerow([title, target_path, str(action.detected_system or "Unknown"), region, language])


def write_retroarch_playlist(
    plan: SortPlan,
    filename: str,
    *,
    core_path: str = "DETECT",
    core_name: str = "DETECT",
    db_name: str = "",
) -> None:
    """Write a RetroArch .lpl playlist from a SortPlan."""
    items: list[dict[str, Any]] = []
    for action in _iter_planned_actions(plan):
        target_path = _format_plan_path(plan, str(action.planned_target_path), prefer_relative=False)
        if not target_path:
            continue
        label = Path(str(action.planned_target_path)).stem or Path(str(action.input_path)).stem
        items.append(
            {
                "path": target_path,
                "label": label,
                "core_path": core_path,
                "core_name": core_name,
                "crc32": "00000000",
                "db_name": db_name,
            }
        )

    payload = {
        "version": "1.5",
        "default_core_path": core_path,
        "default_core_name": core_name,
        "label": Path(plan.dest_path or "ROMs").name,
        "items": items,
    }

    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    write_json(payload, filename)
