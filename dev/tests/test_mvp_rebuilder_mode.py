import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_plan_rebuild_forces_copy_and_skip(tmp_path):
    from src.app.controller import ScanItem, ScanResult, plan_rebuild

    source_dir = tmp_path / "src"
    source_dir.mkdir()
    rom_path = source_dir / "Game A.nes"
    rom_path.write_bytes(b"data")

    scan = ScanResult(
        source_path=str(source_dir),
        items=[
            ScanItem(
                input_path=str(rom_path),
                detected_system="NES",
                detection_source="test",
                detection_confidence=1.0,
                is_exact=True,
            )
        ],
        stats={"total": 1},
        cancelled=False,
    )

    plan = plan_rebuild(scan, str(tmp_path / "dest"))
    assert plan.mode == "copy"
    assert plan.on_conflict == "skip"
