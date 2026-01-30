"""Performance benchmark for scan/plan/execute (dry-run)."""

from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

from src.app.api import CancelToken, execute_sort, plan_sort, run_scan
from src.config.io import load_config


def _generate_files(root: Path, count: int, size_kb: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    payload = (b"0" * 1024) * max(1, size_kb)
    for idx in range(count):
        path = root / f"bench_{idx:05d}.bin"
        path.write_bytes(payload)


def run_benchmark(count: int, size_kb: int) -> dict:
    tmp_root = Path.cwd() / "temp" / "bench"
    source_dir = tmp_root / "source"
    dest_dir = tmp_root / "dest"
    if tmp_root.exists():
        shutil.rmtree(tmp_root, ignore_errors=True)
    source_dir.mkdir(parents=True, exist_ok=True)
    dest_dir.mkdir(parents=True, exist_ok=True)

    _generate_files(source_dir, count=count, size_kb=size_kb)

    cfg = load_config()
    cancel = CancelToken()

    t0 = time.perf_counter()
    scan = run_scan(str(source_dir), config=cfg, cancel_token=cancel)
    t1 = time.perf_counter()
    plan = plan_sort(scan, str(dest_dir), config=cfg, mode="copy", on_conflict="rename", cancel_token=cancel)
    t2 = time.perf_counter()
    report = execute_sort(plan, cancel_token=cancel, dry_run=True, conversion_mode="skip")
    t3 = time.perf_counter()

    return {
        "count": count,
        "size_kb": size_kb,
        "scan_items": len(scan.items),
        "plan_actions": len(plan.actions),
        "scan_sec": t1 - t0,
        "plan_sec": t2 - t1,
        "execute_dry_sec": t3 - t2,
        "cancelled": report.cancelled,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10_000)
    parser.add_argument("--size-kb", type=int, default=1)
    args = parser.parse_args()

    result = run_benchmark(count=args.count, size_kb=args.size_kb)
    print("Benchmark result:")
    for key, value in result.items():
        print(f"- {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
