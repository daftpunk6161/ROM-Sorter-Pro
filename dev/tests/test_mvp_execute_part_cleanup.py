import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_execute_sort_copy_error_cleans_part_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    from src.app.controller import ScanItem, ScanResult, execute_sort, plan_sort

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "biggame.rom"
    rom.write_bytes(b"x" * (2 * 1024 * 1024))

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
    assert len(plan.actions) == 1
    assert plan.actions[0].planned_target_path

    dst = Path(plan.actions[0].planned_target_path)
    part = dst.with_name(dst.name + ".part")

    real_open = builtins.open

    class WriteFail:
        def __init__(self, f):
            self._f = f
            self._writes = 0

        def write(self, data):
            self._writes += 1
            if self._writes == 1:
                raise OSError("disk full")
            return self._f.write(data)

        def __enter__(self):
            self._f.__enter__()
            return self

        def __exit__(self, exc_type, exc, tb):
            return self._f.__exit__(exc_type, exc, tb)

        def __getattr__(self, name):
            return getattr(self._f, name)

    def fake_open(file, mode="r", *args, **kwargs):
        try:
            path = Path(file)
        except TypeError:
            path = None

        if path is not None and path.resolve() == part.resolve() and "w" in mode and "b" in mode:
            return WriteFail(real_open(file, mode, *args, **kwargs))

        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)

    report = execute_sort(plan, dry_run=False)

    assert report.processed == 1
    assert report.errors
    assert not dst.exists()
    assert not part.exists()
