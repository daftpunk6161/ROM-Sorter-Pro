from __future__ import annotations

import asyncio
from concurrent.futures import Executor
from typing import Any, Callable, Optional


def run_in_loop(loop: asyncio.AbstractEventLoop, func: Callable[..., Any], *args, **kwargs) -> asyncio.Future:
    return asyncio.run_coroutine_threadsafe(asyncio.to_thread(func, *args, **kwargs), loop)


async def run_blocking(func: Callable[..., Any], *args, executor: Optional[Executor] = None, **kwargs) -> Any:
    return await asyncio.get_running_loop().run_in_executor(executor, func, *args, **kwargs)
