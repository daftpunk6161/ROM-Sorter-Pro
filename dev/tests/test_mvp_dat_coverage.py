from pathlib import Path
from typing import Any, Dict, cast

from src.core.dat_index_sqlite import DatIndexSqlite


def test_dat_coverage_report_counts_platforms(tmp_path: Path) -> None:
    index_path = tmp_path / "index.sqlite"
    index = DatIndexSqlite(index_path)
    try:
        cur = index.conn.cursor()
        cur.execute(
            "INSERT INTO dat_files (source_path, mtime, size_bytes, active) VALUES (?, ?, ?, ?)",
            ("/tmp/a.dat", 1, 10, 1),
        )
        cur.execute(
            "INSERT INTO dat_files (source_path, mtime, size_bytes, active) VALUES (?, ?, ?, ?)",
            ("/tmp/b.dat", 1, 10, 0),
        )
        cur.execute(
            "INSERT INTO rom_hashes (dat_id, platform_id, rom_name, set_name, crc32, sha1, size_bytes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "NES", "rom1", "set1", "abc", None, 123),
        )
        cur.execute(
            "INSERT INTO rom_hashes (dat_id, platform_id, rom_name, set_name, crc32, sha1, size_bytes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "SNES", "rom2", "set2", "def", None, 456),
        )
        cur.execute(
            "INSERT INTO game_names (dat_id, platform_id, game_name) VALUES (?, ?, ?)",
            (1, "NES", "Game 1"),
        )
        index.conn.commit()

        report = cast(Dict[str, Any], index.coverage_report())

        assert report["active_dat_files"] == 1
        assert report["inactive_dat_files"] == 1
        assert report["rom_hashes"] == 2
        assert report["game_names"] == 1
        platforms = cast(Dict[str, Dict[str, int]], report.get("platforms") or {})
        assert platforms["NES"]["roms"] == 1
        assert platforms["NES"]["games"] == 1
        assert platforms["SNES"]["roms"] == 1
        assert platforms["SNES"]["games"] == 0
    finally:
        index.close()