from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.app.api import CancelToken, execute_sort, plan_sort, run_scan
from src.config.io import load_config


pytestmark = pytest.mark.integration


def test_performance_benchmark_smoke(tmp_path: Path) -> None:
    if os.environ.get("ROM_SORTER_PERF_BENCH") != "1":
        pytest.skip("Set ROM_SORTER_PERF_BENCH=1 to enable perf benchmark test.")

    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir(parents=True, exist_ok=True)
    dest_dir.mkdir(parents=True, exist_ok=True)

    for idx in range(1000):
        (source_dir / f"bench_{idx:05d}.bin").write_bytes(b"0" * 1024)

    cfg = load_config()
    cancel = CancelToken()

    scan = run_scan(str(source_dir), config=cfg, cancel_token=cancel)
    plan = plan_sort(scan, str(dest_dir), config=cfg, mode="copy", on_conflict="rename", cancel_token=cancel)
    report = execute_sort(plan, cancel_token=cancel, dry_run=True, conversion_mode="skip")

    assert scan.items
    assert plan.actions
    assert not report.cancelled
