from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from .controller import (
    CancelToken,
    ScanResult,
    SortPlan,
    SortReport,
    run_scan,
    plan_sort,
    execute_sort,
)
from ..utils.async_utils import run_blocking


async def run_scan_async(
    source_path: str,
    config: Optional[dict] = None,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    log_cb: Optional[Callable[[str], None]] = None,
    cancel_token: Optional[CancelToken] = None,
) -> ScanResult:
    return await run_blocking(
        run_scan,
        source_path,
        config,
        progress_cb,
        log_cb,
        cancel_token,
    )


async def plan_sort_async(
    scan_result: ScanResult,
    dest_path: str,
    config: Optional[dict] = None,
    mode: str = "copy",
    on_conflict: str = "rename",
    cancel_token: Optional[CancelToken] = None,
) -> SortPlan:
    return await run_blocking(
        plan_sort,
        scan_result,
        dest_path,
        config,
        mode,
        on_conflict,
        cancel_token,
    )


async def execute_sort_async(
    sort_plan: SortPlan,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    log_cb: Optional[Callable[[str], None]] = None,
    action_status_cb: Optional[Callable[[int, str], None]] = None,
    cancel_token: Optional[CancelToken] = None,
    dry_run: bool = False,
    resume_path: Optional[str] = None,
    start_index: int = 0,
    only_indices: Optional[list[int]] = None,
    conversion_mode: str = "all",
) -> SortReport:
    return await run_blocking(
        execute_sort,
        sort_plan,
        progress_cb,
        log_cb,
        action_status_cb,
        cancel_token,
        dry_run,
        resume_path,
        start_index,
        only_indices,
        conversion_mode,
    )
