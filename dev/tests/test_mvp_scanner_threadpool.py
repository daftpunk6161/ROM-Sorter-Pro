import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_scanner_uses_threadpool_for_processing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import concurrent.futures

    from src.scanning.high_performance_scanner import HighPerformanceScanner

    scan_dir = tmp_path / "scan"
    scan_dir.mkdir()
    for i in range(20):
        (scan_dir / f"rom_{i}.bin").write_text("data")

    scanner = HighPerformanceScanner({})

    # Avoid heavy processing
    monkeypatch.setattr(scanner, "_process_file", lambda *_args, **_kwargs: {})

    real_executor = concurrent.futures.ThreadPoolExecutor
    seen: dict[str, int | None] = {"max_workers": None}

    class SpyExecutor:
        def __init__(self, max_workers: int):
            seen["max_workers"] = max_workers
            self._executor = real_executor(max_workers=max_workers)

        def __enter__(self):
            return self._executor

        def __exit__(self, exc_type, exc, tb):
            self._executor.shutdown(wait=True)
            return False

    monkeypatch.setattr(concurrent.futures, "ThreadPoolExecutor", SpyExecutor)

    scanner._scan_thread(str(scan_dir), {
        "recursive": True,
        "file_types": None,
        "max_depth": -1,
        "follow_symlinks": False,
        "use_cache": False,
    })

    assert seen["max_workers"] is not None
    assert seen["max_workers"] >= 2
