from __future__ import annotations

from pathlib import Path

import pytest

from src.app.database_export import export_scan_to_database
from src.app.models import ScanItem, ScanResult
from src.database.rom_database import ROMDatabase

pytestmark = pytest.mark.integration


def test_export_scan_to_database(tmp_path: Path) -> None:
    db_path = tmp_path / "roms.sqlite"

    src_file = tmp_path / "game.rom"
    src_file.write_bytes(b"DATA")

    scan = ScanResult(
        source_path=str(tmp_path),
        items=[
            ScanItem(
                input_path=str(src_file),
                detected_system="Unknown",
                detection_source="manual",
                detection_confidence=1.0,
                is_exact=True,
            )
        ],
        stats={},
        cancelled=False,
    )

    count = export_scan_to_database(scan, db_path=str(db_path))
    assert count == 1

    db = ROMDatabase(db_path=str(db_path))
    stats = db.get_statistics()
    assert int(stats.get("total_roms", 0)) >= 1
