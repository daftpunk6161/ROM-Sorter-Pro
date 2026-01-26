import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_real_dat_fixture_sha1_match(tmp_path):
    from src.app.controller import build_dat_index
    from src.config import Config
    from src.core.dat_index_sqlite import DatIndexSqlite
    from src.detectors.dat_identifier import identify_by_hash

    fixture_dat = ROOT / "dev" / "tests" / "fixtures" / "real_dat" / "mini_nes.xml"
    fixture_rom = ROOT / "dev" / "tests" / "fixtures" / "real_roms" / "fixture_game1.nes"
    fixture_rom_crc = ROOT / "dev" / "tests" / "fixtures" / "real_roms" / "fixture_game2.bin"

    assert fixture_dat.exists()
    assert fixture_rom.exists()
    assert fixture_rom_crc.exists()

    index_path = tmp_path / "romsorter_dat_index.sqlite"
    lock_path = tmp_path / "romsorter_dat_index.lock"
    cfg = Config(
        {
            "dats": {
                "import_paths": [str(fixture_dat)],
                "index_path": str(index_path),
                "lock_path": str(lock_path),
            }
        }
    )

    result = build_dat_index(config=cfg)
    assert result["inserted"] >= 1

    index = DatIndexSqlite.from_config(cfg)
    try:
        match = identify_by_hash(str(fixture_rom), index)
        assert match is not None
        assert match.platform_id == "NES"
        assert match.is_exact is True
        assert "DAT_MATCH_SHA1" in match.signals

        match_crc = identify_by_hash(str(fixture_rom_crc), index)
        assert match_crc is not None
        assert match_crc.platform_id == "NES"
        assert match_crc.is_exact is True
        assert "DAT_MATCH_CRC_SIZE" in match_crc.signals
    finally:
        index.close()
