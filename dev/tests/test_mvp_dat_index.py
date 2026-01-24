import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_dat_index_parses_xml(tmp_path):
    from src.core.dat_index import DatIndex

    dat_xml = tmp_path / "sample.dat"
    dat_xml.write_text(
        """<?xml version=\"1.0\"?>
<datfile>
  <header>
    <name>Nintendo - Nintendo Entertainment System</name>
  </header>
  <game name=\"Test Game\">
    <rom name=\"test.nes\" crc=\"1234abcd\" md5=\"0123456789abcdef0123456789abcdef\" sha1=\"0123456789abcdef0123456789abcdef01234567\" />
  </game>
</datfile>
""",
        encoding="utf-8",
    )

    index = DatIndex()
    index.load_paths([str(dat_xml)])

    match = index.lookup_game("Test Game")
    assert match is not None
    assert match.system == "NES"

    hash_match = index.lookup_hashes(crc="1234abcd")
    assert hash_match is not None
    assert hash_match.system == "NES"


def _write_sqlite_dat(path: Path, system_name: str, game_name: str, rom_name: str, crc: str, sha1: str) -> None:
    path.write_text(
        f"""<?xml version=\"1.0\"?>
<datfile>
  <header>
    <name>{system_name}</name>
  </header>
  <game name=\"{game_name}\">
    <rom name=\"{rom_name}\" crc=\"{crc}\" sha1=\"{sha1}\" />
  </game>
</datfile>
""",
        encoding="utf-8",
    )


def test_sqlite_dat_index_incremental_rebuild_and_coverage(tmp_path):
    from src.core.dat_index_sqlite import DatIndexSqlite, build_index_from_config

    dat_dir = tmp_path / "dats"
    dat_dir.mkdir()
    dat_a = dat_dir / "a.dat"
    dat_b = dat_dir / "b.dat"
    _write_sqlite_dat(
      dat_a,
      "Nintendo - Nintendo Entertainment System",
      "Game A",
      "a.nes",
      "aaaaaaaa",
      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    _write_sqlite_dat(
      dat_b,
      "Super Nintendo Entertainment System",
      "Game B",
      "b.sfc",
      "bbbbbbbb",
      "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )

    index_path = tmp_path / "index.sqlite"
    lock_path = tmp_path / "index.lock"
    cfg = {"dats": {"import_paths": [str(dat_dir)], "index_path": str(index_path), "lock_path": str(lock_path)}}

    first = build_index_from_config(config=cfg)
    assert first["processed"] == 2
    assert first["removed"] == 0

    index = DatIndexSqlite(index_path)
    coverage = index.coverage_report()
    index.close()

    assert coverage["active_dat_files"] == 2
    assert coverage["inactive_dat_files"] == 0
    assert coverage["rom_hashes"] == 2
    assert coverage["game_names"] == 2

    dat_b.unlink()
    second = build_index_from_config(config=cfg)
    assert second["removed"] == 1

    index = DatIndexSqlite(index_path)
    coverage2 = index.coverage_report()
    index.close()

    assert coverage2["active_dat_files"] == 1
    assert coverage2["inactive_dat_files"] == 1
    assert coverage2["rom_hashes"] == 1
    assert coverage2["game_names"] == 1
