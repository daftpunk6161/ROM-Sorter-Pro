from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

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


@dataclass(frozen=True)
class ProgressEvent:
    kind: str
    current: int = 0
    total: int = 0
    message: Optional[str] = None
    result: Optional[Any] = None


def _queue_progress(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue, current: int, total: int) -> None:
    loop.call_soon_threadsafe(queue.put_nowait, ProgressEvent(kind="progress", current=int(current), total=int(total)))


def _queue_log(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue, message: str) -> None:
    loop.call_soon_threadsafe(queue.put_nowait, ProgressEvent(kind="log", message=str(message)))


async def run_scan_stream(
    source_path: str,
    config: Optional[dict] = None,
    cancel_token: Optional[CancelToken] = None,
) -> AsyncIterator[ProgressEvent]:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def progress_cb(c: int, t: int) -> None:
        _queue_progress(loop, queue, c, t)

    def log_cb(msg: str) -> None:
        _queue_log(loop, queue, msg)

    task = asyncio.create_task(
        run_blocking(run_scan, source_path, config, progress_cb, log_cb, cancel_token)
    )

    while True:
        if task.done() and queue.empty():
            break
        try:
            event = await asyncio.wait_for(queue.get(), timeout=0.05)
            yield event
        except asyncio.TimeoutError:
            continue

    result: ScanResult = task.result()
    yield ProgressEvent(kind="result", result=result)


async def plan_sort_stream(
    scan_result: ScanResult,
    dest_path: str,
    config: Optional[dict] = None,
    mode: str = "copy",
    on_conflict: str = "rename",
    cancel_token: Optional[CancelToken] = None,
) -> AsyncIterator[ProgressEvent]:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def progress_cb(c: int, t: int) -> None:
        _queue_progress(loop, queue, c, t)

    def log_cb(msg: str) -> None:
        _queue_log(loop, queue, msg)

    task = asyncio.create_task(
        run_blocking(plan_sort, scan_result, dest_path, config, mode, on_conflict, cancel_token)
    )

    while True:
        if task.done() and queue.empty():
            break
        try:
            event = await asyncio.wait_for(queue.get(), timeout=0.05)
            yield event
        except asyncio.TimeoutError:
            continue

    result: SortPlan = task.result()
    yield ProgressEvent(kind="result", result=result)


async def execute_sort_stream(
    sort_plan: SortPlan,
    config: Optional[dict] = None,
    cancel_token: Optional[CancelToken] = None,
    dry_run: bool = False,
    resume_path: Optional[str] = None,
    start_index: int = 0,
    only_indices: Optional[list[int]] = None,
    conversion_mode: str = "all",
) -> AsyncIterator[ProgressEvent]:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def progress_cb(c: int, t: int) -> None:
        _queue_progress(loop, queue, c, t)

    def log_cb(msg: str) -> None:
        _queue_log(loop, queue, msg)

    def action_status_cb(i: int, status: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, ProgressEvent(kind="action", current=int(i), message=str(status)))

    task = asyncio.create_task(
        run_blocking(
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
    )

    while True:
        if task.done() and queue.empty():
            break
        try:
            event = await asyncio.wait_for(queue.get(), timeout=0.05)
            yield event
        except asyncio.TimeoutError:
            continue

    result: SortReport = task.result()
    yield ProgressEvent(kind="result", result=result)
