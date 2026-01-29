from __future__ import annotations

import os
import tracemalloc
from pathlib import Path

import pytest

from src.app.api import CancelToken, execute_sort, plan_sort, run_scan
from src.config.io import load_config


pytestmark = pytest.mark.integration


def _run_cycle(source_dir: Path, dest_dir: Path) -> None:
    cfg = load_config()
    cancel = CancelToken()
    scan = run_scan(str(source_dir), config=cfg, cancel_token=cancel)
    plan = plan_sort(scan, str(dest_dir), config=cfg, mode="copy", on_conflict="rename", cancel_token=cancel)
    execute_sort(plan, cancel_token=cancel, dry_run=True, conversion_mode="skip")


def test_memory_leak_smoke(tmp_path: Path) -> None:
    if os.environ.get("ROM_SORTER_MEM_LEAK") != "1":
        pytest.skip("Set ROM_SORTER_MEM_LEAK=1 to enable memory leak smoke test.")

    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir(parents=True, exist_ok=True)
    dest_dir.mkdir(parents=True, exist_ok=True)

    for idx in range(200):
        (source_dir / f"mem_{idx:05d}.bin").write_bytes(b"0" * 1024)

    tracemalloc.start()
    _run_cycle(source_dir, dest_dir)
    snap1 = tracemalloc.take_snapshot()
    _run_cycle(source_dir, dest_dir)
    snap2 = tracemalloc.take_snapshot()

    stats = snap2.compare_to(snap1, "lineno")
    total_diff = sum(stat.size_diff for stat in stats)

    # Allow small fluctuations, fail on large growth.
    assert total_diff < 5 * 1024 * 1024
