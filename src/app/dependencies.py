"""Simple dependency container for controllers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .scan_controller import run_scan
from .sort_controller import execute_sort, plan_sort
from ..config.io import load_config


@dataclass(frozen=True)
class AppDependencies:
    run_scan: Callable
    plan_sort: Callable
    execute_sort: Callable
    load_config: Callable


def get_default_dependencies() -> AppDependencies:
    return AppDependencies(
        run_scan=run_scan,
        plan_sort=plan_sort,
        execute_sort=execute_sort,
        load_config=load_config,
    )
