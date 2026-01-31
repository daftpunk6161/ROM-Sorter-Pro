from pathlib import Path

from src.app.controller import ScanItem, identify
from src.config import Config
from src.core.dat_index_sqlite import DatIndexSqlite


def test_fuzzy_name_match_returns_candidate(tmp_path: Path) -> None:
    index_path = tmp_path / "index.sqlite"
    index = DatIndexSqlite(index_path)
    try:
        cur = index.conn.cursor()
        cur.execute(
            "INSERT INTO dat_files (source_path, mtime, size_bytes, active) VALUES (?, ?, ?, ?)",
            ("/tmp/test.dat", 1, 10, 1),
        )
        cur.execute(
            "INSERT INTO game_names (dat_id, platform_id, game_name) VALUES (?, ?, ?)",
            (1, "SNES", "super mario world"),
        )
        index.conn.commit()
    finally:
        index.close()

    rom = tmp_path / "Super Mario World (USA).sfc"
    rom.write_text("data")

    cfg = Config({"dats": {"index_path": str(index_path)}})
    results = identify([ScanItem(input_path=str(rom), detected_system="Unknown")], config=cfg)

    assert results
    assert "FUZZY_NAME_MATCH" in results[0].signals
    assert results[0].platform_id in ("SNES", "Unknown")