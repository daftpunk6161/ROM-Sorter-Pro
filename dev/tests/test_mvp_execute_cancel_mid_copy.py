import sys
import pytest
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.integration


def test_execute_sort_cancel_mid_copy_cleans_part_file(tmp_path, monkeypatch):
    # Mutation-proof: ignoring cancel_token in the copy loop should fail this test.
    """Deterministic mid-copy cancellation.

    We monkeypatch builtins.open for the source file so that after the first read()
    call we cancel the CancelToken. The controller should delete the temporary
    '.part' file and not leave the final destination file behind.
    """

    import builtins

    from src.app.controller import CancelToken, ScanItem, ScanResult, execute_sort, plan_sort

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "biggame.rom"
    # Large enough to require multiple read iterations even with default buffer.
    rom.write_bytes(b"x" * (3 * 1024 * 1024))

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
    assert len(plan.actions) == 1
    assert plan.actions[0].planned_target_path

    token = CancelToken()

    dst = Path(plan.actions[0].planned_target_path)
    part = dst.with_name(dst.name + ".part")

    real_open = builtins.open

    class ReadCanceller:
        def __init__(self, f):
            self._f = f
            self._reads = 0

        def read(self, n=-1):
            data = self._f.read(n)
            self._reads += 1
            if self._reads == 1:
                token.cancel()
            return data

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

        if path is not None and path.resolve() == rom.resolve() and "r" in mode and "b" in mode:
            return ReadCanceller(real_open(file, mode, *args, **kwargs))

        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)

    report = execute_sort(plan, cancel_token=token, dry_run=False)

    assert report.cancelled is True
    assert report.copied == 0
    assert not dst.exists()
    assert not part.exists()


def test_execute_sort_cancel_from_other_thread(tmp_path, monkeypatch):
    import builtins
    import threading

    from src.app.controller import CancelToken, ScanItem, ScanResult, execute_sort, plan_sort

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "biggame.rom"
    rom.write_bytes(b"x" * (3 * 1024 * 1024))

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
    token = CancelToken()

    dst = Path(plan.actions[0].planned_target_path)
    part = dst.with_name(dst.name + ".part")

    real_open = builtins.open
    read_started = threading.Event()

    class ReadSignal:
        def __init__(self, f):
            self._f = f
            self._reads = 0

        def read(self, n=-1):
            data = self._f.read(n)
            self._reads += 1
            if self._reads == 1:
                read_started.set()
            return data

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

        if path is not None and path.resolve() == rom.resolve() and "r" in mode and "b" in mode:
            return ReadSignal(real_open(file, mode, *args, **kwargs))

        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)

    def _cancel_when_reading():
        if read_started.wait(timeout=2.0):
            token.cancel()

    t = threading.Thread(target=_cancel_when_reading, daemon=True)
    t.start()

    report = execute_sort(plan, cancel_token=token, dry_run=False)

    assert report.cancelled is True
    assert not dst.exists()
    assert not part.exists()
