import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


def test_sqlite_dat_index_sharding_lookup(tmp_path: Path) -> None:
    from src.core.dat_index_sqlite import build_index_from_config, open_dat_index_from_config

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
    cfg = {
        "dats": {
            "import_paths": [str(dat_dir)],
            "index_path": str(index_path),
            "lock_path": str(lock_path),
            "sharding": {"enabled": True, "shard_count": 2},
        }
    }

    build_index_from_config(config=cfg)
    index = open_dat_index_from_config(cfg)
    assert index is not None

    match = index.lookup_sha1("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert match is not None
    assert match.platform_id == "NES"

    if hasattr(index, "close"):
        index.close()
