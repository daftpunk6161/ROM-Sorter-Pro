import sqlite3
import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_setup_database_unified_roms_schema(tmp_path):
    from scripts.update_rom_database import setup_database

    db_path = tmp_path / "roms.db"
    conn = setup_database(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(roms)")
        cols = {row[1] for row in cursor.fetchall()}
    finally:
        conn.close()

    expected = {
        "id",
        "name",
        "filename",
        "console",
        "path",
        "filesize",
        "size",
        "crc",
        "md5",
        "sha1",
        "hash",
        "metadata",
        "source",
        "confidence",
        "system_id",
        "created_at",
        "updated_at",
    }
    missing = expected - cols
    assert not missing, f"Missing columns: {missing}"

    cursor = sqlite3.connect(str(db_path)).cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='systems'")
        assert cursor.fetchone() is not None
    finally:
        cursor.connection.close()
