import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_plan_sort_respects_cancel_token(tmp_path):
    from src.app.controller import CancelToken, ScanItem, ScanResult, plan_sort

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom_one = source / "game1.rom"
    rom_two = source / "game2.rom"
    rom_one.write_text("x")
    rom_two.write_text("y")

    scan = ScanResult(
        source_path=str(source),
        items=[
            ScanItem(input_path=str(rom_one), detected_system="NES"),
            ScanItem(input_path=str(rom_two), detected_system="SNES"),
        ],
        stats={},
        cancelled=False,
    )

    token = CancelToken()
    token.cancel()

    plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename", cancel_token=token)

    assert plan.actions == []
