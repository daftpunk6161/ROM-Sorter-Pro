"""Sort controller facade (thin wrapper)."""

from __future__ import annotations

from typing import Optional, List

from .controller import (
    CancelToken,
    SortPlan,
    SortReport,
    ScanResult,
    SortMode,
    ConflictPolicy,
    ConversionMode,
    ProgressCallback,
    LogCallback,
    ActionStatusCallback,
    plan_sort as _plan_sort,
    plan_rebuild as _plan_rebuild,
    execute_sort as _execute_sort,
)
from ..config import Config


def plan_sort(
    scan_result: ScanResult,
    dest_path: str,
    config: Optional[Config] = None,
    mode: SortMode = "copy",
    on_conflict: ConflictPolicy = "rename",
    cancel_token: Optional[CancelToken] = None,
) -> SortPlan:
    return _plan_sort(
        scan_result=scan_result,
        dest_path=dest_path,
        config=config,
        mode=mode,
        on_conflict=on_conflict,
        cancel_token=cancel_token,
    )


def plan_rebuild(
    scan_result: ScanResult,
    dest_path: str,
    config: Optional[Config] = None,
    cancel_token: Optional[CancelToken] = None,
) -> SortPlan:
    return _plan_rebuild(
        scan_result=scan_result,
        dest_path=dest_path,
        config=config,
        cancel_token=cancel_token,
    )


def execute_sort(
    sort_plan: SortPlan,
    progress_cb: Optional[ProgressCallback] = None,
    log_cb: Optional[LogCallback] = None,
    action_status_cb: Optional[ActionStatusCallback] = None,
    cancel_token: Optional[CancelToken] = None,
    dry_run: bool = False,
    resume_path: Optional[str] = None,
    start_index: int = 0,
    only_indices: Optional[List[int]] = None,
    conversion_mode: ConversionMode = "all",
) -> SortReport:
    return _execute_sort(
        sort_plan=sort_plan,
        progress_cb=progress_cb,
        log_cb=log_cb,
        action_status_cb=action_status_cb,
        cancel_token=cancel_token,
        dry_run=dry_run,
        resume_path=resume_path,
        start_index=start_index,
        only_indices=only_indices,
        conversion_mode=conversion_mode,
    )
