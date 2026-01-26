#!/usr/bin/env python3
"""Micro-benchmark for IO throttling in hash calculation.

Usage:
  python scripts/bench_io_throttle.py --size-mb 64 --throttle-ms 2 --min-mb 1
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.file_utils import calculate_file_hash


def _write_test_file(path: Path, size_mb: int) -> None:
    path.write_bytes(b"x" * (size_mb * 1024 * 1024))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size-mb", type=int, default=64)
    parser.add_argument("--throttle-ms", type=float, default=1.0)
    parser.add_argument("--min-mb", type=int, default=1)
    args = parser.parse_args()

    tmp_dir = Path("temp")
    tmp_dir.mkdir(exist_ok=True)
    test_file = tmp_dir / f"bench_{args.size_mb}mb.bin"

    _write_test_file(test_file, args.size_mb)

    os.environ["ROM_SORTER_IO_THROTTLE_SLEEP_MS"] = str(args.throttle_ms)
    os.environ["ROM_SORTER_IO_THROTTLE_MIN_MB"] = str(args.min_mb)

    start = time.perf_counter()
    digest = calculate_file_hash(test_file, algorithm="md5")
    elapsed = time.perf_counter() - start

    print(f"hash={digest} size_mb={args.size_mb} throttle_ms={args.throttle_ms} min_mb={args.min_mb} elapsed={elapsed:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
