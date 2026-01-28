import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.integration


def test_execute_sort_invalid_path_continues_batch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.app import controller

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom1 = source / "game1.rom"
    rom2 = source / "game2.rom"
    rom1.write_text("x")
    rom2.write_text("y")

    scan = controller.ScanResult(
        source_path=str(source),
        items=[
            controller.ScanItem(input_path=str(rom1), detected_system="NES"),
            controller.ScanItem(input_path=str(rom2), detected_system="NES"),
        ],
        stats={},
        cancelled=False,
    )

    plan = controller.plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
    invalid_input = Path(plan.actions[0].input_path).resolve()
    original_validate = controller.validate_file_operation

    def fake_validate(path, base_dir=None, allow_read=False, allow_write=False):
        if Path(path).resolve() == invalid_input:
            raise controller.InvalidPathError("test invalid path")
        return original_validate(path, base_dir=base_dir, allow_read=allow_read, allow_write=allow_write)

    monkeypatch.setattr(controller, "validate_file_operation", fake_validate)

    report = controller.execute_sort(plan, cancel_token=None, dry_run=True)

    assert report.cancelled is False
    assert report.processed == len(plan.actions)
    assert len(report.errors) == 1
