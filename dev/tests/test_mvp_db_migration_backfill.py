import sqlite3
import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_update_rom_database_backfills_system_id(tmp_path):
    from scripts.update_rom_database import setup_database, update_rom_database

    db_path = tmp_path / "roms.db"
    conn = setup_database(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO consoles (name, folder, extensions, enabled, detection_priority) VALUES (?, ?, ?, ?, ?)",
            ("TestConsole", "TestConsole", ".tst", 1, 100),
        )
        cur.execute(
            "INSERT INTO roms (name, filename, console, path, filesize, size) VALUES (?, ?, ?, ?, ?, ?)",
            ("TestRom", "TestRom.tst", "TestConsole", "/tmp/TestRom.tst", 1, 1),
        )
        conn.commit()
    finally:
        conn.close()

    assert update_rom_database(str(db_path))

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT system_id FROM roms WHERE console = ?", ("TestConsole",))
        row = cur.fetchone()
        assert row is not None
        assert row[0] is not None
    finally:
        conn.close()
