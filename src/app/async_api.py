"""Async wrappers for controller operations."""

from __future__ import annotations

import asyncio
from typing import Optional

from .dependencies import AppDependencies, get_default_dependencies
from .models import CancelToken, ConflictPolicy, ConversionMode, ScanResult, SortMode, SortPlan
from ..utils.result import Err, Ok, Result


async def async_run_scan(
    source_path: str,
    *,
    config: Optional[dict] = None,
    cancel_token: Optional[CancelToken] = None,
    deps: Optional[AppDependencies] = None,
) -> Result[ScanResult]:
    deps = deps or get_default_dependencies()
    try:
        result = await asyncio.to_thread(
            deps.run_scan,
            source_path,
            config,
            None,
            None,
            cancel_token,
        )
        return Ok(result)
    except Exception as exc:
        return Err(exc)


async def async_plan_sort(
    scan_result: ScanResult,
    dest_path: str,
    *,
    config: Optional[dict] = None,
    mode: SortMode = "copy",
    on_conflict: ConflictPolicy = "rename",
    cancel_token: Optional[CancelToken] = None,
    deps: Optional[AppDependencies] = None,
) -> Result[SortPlan]:
    deps = deps or get_default_dependencies()
    try:
        result = await asyncio.to_thread(
            deps.plan_sort,
            scan_result,
            dest_path,
            config,
            mode,
            on_conflict,
            cancel_token,
        )
        return Ok(result)
    except Exception as exc:
        return Err(exc)


async def async_execute_sort(
    sort_plan: SortPlan,
    *,
    cancel_token: Optional[CancelToken] = None,
    conversion_mode: ConversionMode = "skip",
    deps: Optional[AppDependencies] = None,
):
    deps = deps or get_default_dependencies()
    try:
        result = await asyncio.to_thread(
            deps.execute_sort,
            sort_plan,
            None,
            None,
            None,
            cancel_token,
            False,
            None,
            0,
            None,
            conversion_mode,
        )
        return Ok(result)
    except Exception as exc:
        return Err(exc)
