from pathlib import Path

from src.core.dat_index_sqlite import DatIndexSqlite
from src.detectors.dat_identifier import identify_by_hash
from src.core.file_utils import calculate_file_hash


def test_identify_bad_dump_signal(tmp_path: Path) -> None:
    index_path = tmp_path / "index.sqlite"
    index = DatIndexSqlite(index_path)
    try:
        rom = tmp_path / "game.rom"
        rom.write_text("data")
        sha1 = calculate_file_hash(rom, algorithm="sha1")
        assert sha1 is not None

        cur = index.conn.cursor()
        cur.execute(
            "INSERT INTO dat_files (source_path, mtime, size_bytes, active) VALUES (?, ?, ?, ?)",
            ("/tmp/test.dat", 1, 10, 1),
        )
        cur.execute(
            "INSERT INTO rom_hashes (dat_id, platform_id, rom_name, set_name, crc32, sha1, size_bytes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "NES", "Game [b].rom", "Game", "abcd", sha1, 4),
        )
        index.conn.commit()

        result = identify_by_hash(str(rom), index)

        assert result is not None
        assert "BAD_DUMP" in result.signals
    finally:
        index.close()