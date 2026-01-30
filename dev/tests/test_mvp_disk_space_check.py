import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app.controller import execute_sort  # noqa: E402
from src.app.models import SortAction, SortPlan  # noqa: E402
from src.exceptions import FileOperationError  # noqa: E402


pytestmark = pytest.mark.integration


def test_execute_sort_fails_when_disk_full(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = tmp_path / "game.rom"
    src.write_bytes(b"x" * 10)
    dest = tmp_path / "dest"
    dest.mkdir()

    plan = SortPlan(
        dest_path=str(dest),
        mode="copy",
        on_conflict="skip",
        actions=[
            SortAction(
                input_path=str(src),
                detected_system="SNES",
                planned_target_path=str(dest / "game.rom"),
                action="copy",
                status="pending",
            )
        ],
    )

    class _Usage:
        free = 1
        used = 0
        total = 1

    def _fake_disk_usage(_path: str):
        return _Usage()

    monkeypatch.setattr("src.app.controller.shutil.disk_usage", _fake_disk_usage)

    with pytest.raises(FileOperationError):
        execute_sort(plan, dry_run=False)
