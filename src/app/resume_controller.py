"""Resume state helpers for scan/sort."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from ..security.security_utils import validate_file_operation
from .models import ScanItem, ScanResult, SortAction, SortPlan, SortResumeState


def _serialize_sort_plan(sort_plan: SortPlan) -> Dict[str, Any]:
    return {
        "dest_path": sort_plan.dest_path,
        "mode": sort_plan.mode,
        "on_conflict": sort_plan.on_conflict,
        "actions": [action.__dict__ for action in sort_plan.actions],
    }


def save_sort_resume(sort_plan: SortPlan, start_index: int, path: str) -> None:
    payload = _serialize_sort_plan(sort_plan)
    payload["resume_from_index"] = int(start_index)
    target = Path(path)
    validate_file_operation(target, base_dir=None, allow_read=True, allow_write=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_sort_resume(path: str) -> SortPlan:
    return load_sort_resume_state(path).sort_plan


def load_sort_resume_state(path: str) -> SortResumeState:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    actions = [SortAction(**action) for action in payload.get("actions", [])]
    resume_from_index = int(payload.get("resume_from_index") or 0)
    if resume_from_index < 0:
        resume_from_index = 0
    if resume_from_index > len(actions):
        resume_from_index = len(actions)
    plan = SortPlan(
        dest_path=payload.get("dest_path", ""),
        mode=payload.get("mode", "copy"),
        on_conflict=payload.get("on_conflict", "rename"),
        actions=actions,
    )
    return SortResumeState(sort_plan=plan, resume_from_index=resume_from_index)


def save_scan_resume(scan_result: ScanResult, path: str) -> None:
    payload = {
        "source_path": scan_result.source_path,
        "stats": scan_result.stats,
        "cancelled": scan_result.cancelled,
        "items": [item.__dict__ for item in scan_result.items],
    }
    target = Path(path)
    validate_file_operation(target, base_dir=None, allow_read=True, allow_write=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_scan_resume(path: str) -> ScanResult:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    items = [ScanItem(**item) for item in payload.get("items", [])]
    return ScanResult(
        source_path=payload.get("source_path", ""),
        stats=payload.get("stats") or {},
        cancelled=bool(payload.get("cancelled")),
        items=items,
    )
