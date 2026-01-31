import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app.controller import ScanItem, add_identification_override, identify  # noqa: E402
from src.core.dat_index_sqlite import DatIndexSqlite  # noqa: E402
from src.hash_utils import calculate_crc32  # noqa: E402
from src.core.file_utils import calculate_file_hash  # noqa: E402

pytestmark = pytest.mark.integration


def _create_index(tmp_path: Path) -> Path:
    index_path = tmp_path / "romsorter_dat_index.sqlite"
    DatIndexSqlite(index_path).close()
    return index_path


def _insert_hash_row(
    index_path: Path,
    *,
    dat_id: int = 1,
    platform_id: str,
    sha1: str | None,
    crc32: str | None,
    size_bytes: int,
) -> None:
    conn = sqlite3.connect(str(index_path))
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO rom_hashes (dat_id, platform_id, rom_name, set_name, crc32, sha1, size_bytes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (dat_id, platform_id, "Test ROM", "Test Set", (crc32 or "").lower(), sha1, size_bytes),
        )
        conn.commit()
    finally:
        conn.close()


def test_identify_returns_unknown_when_index_missing(tmp_path):
    rom = tmp_path / "game.rom"
    rom.write_text("data", encoding="utf-8")

    items = [ScanItem(input_path=str(rom), detected_system="Unknown")]
    config = {"dats": {"index_path": str(tmp_path / "missing.sqlite")}}

    results = identify(items, config=config)

    assert results
    assert results[0].platform_id == "Unknown"
    assert results[0].reason == "index-missing"
    assert "NO_INDEX" in results[0].signals


def test_identify_returns_missing_input_when_file_missing(tmp_path):
    index_path = _create_index(tmp_path)
    missing = tmp_path / "missing.rom"

    items = [ScanItem(input_path=str(missing), detected_system="Unknown")]
    config = {"dats": {"index_path": str(index_path)}}

    results = identify(items, config=config)

    assert results
    assert results[0].platform_id == "Unknown"
    assert results[0].reason == "input-missing"
    assert "INPUT_MISSING" in results[0].signals


def test_identify_returns_dat_match(tmp_path):
    rom = tmp_path / "game.rom"
    rom.write_text("data", encoding="utf-8")

    sha1 = calculate_file_hash(str(rom), algorithm="sha1")
    assert sha1
    crc32 = calculate_crc32(str(rom))
    size_bytes = os.stat(rom).st_size

    index_path = _create_index(tmp_path)
    _insert_hash_row(index_path, platform_id="NES", sha1=sha1, crc32=crc32, size_bytes=size_bytes)

    items = [ScanItem(input_path=str(rom), detected_system="Unknown")]
    config = {"dats": {"index_path": str(index_path)}}

    results = identify(items, config=config)

    assert results
    assert results[0].platform_id == "NES"
    assert results[0].is_exact is True
    assert "DAT_MATCH_SHA1" in results[0].signals


def test_identify_crc_size_fallback(tmp_path):
    rom = tmp_path / "game.rom"
    rom.write_text("data", encoding="utf-8")

    crc32 = calculate_crc32(str(rom))
    size_bytes = os.stat(rom).st_size

    index_path = _create_index(tmp_path)
    _insert_hash_row(index_path, platform_id="SNES", sha1=None, crc32=crc32, size_bytes=size_bytes)

    items = [ScanItem(input_path=str(rom), detected_system="Unknown")]
    config = {"dats": {"index_path": str(index_path)}}

    results = identify(items, config=config)

    assert results
    assert results[0].platform_id == "SNES"
    assert results[0].is_exact is True
    assert "DAT_MATCH_CRC_SIZE" in results[0].signals


def test_identify_returns_cross_check_on_crc_size(tmp_path: Path) -> None:
    rom = tmp_path / "game.rom"
    rom.write_text("data", encoding="utf-8")

    crc32 = calculate_crc32(str(rom))
    size_bytes = os.stat(rom).st_size

    index_path = _create_index(tmp_path)
    _insert_hash_row(
        index_path,
        dat_id=1,
        platform_id="NES",
        sha1=None,
        crc32=crc32,
        size_bytes=size_bytes,
    )
    _insert_hash_row(
        index_path,
        dat_id=2,
        platform_id="SNES",
        sha1=None,
        crc32=crc32,
        size_bytes=size_bytes,
    )

    items = [ScanItem(input_path=str(rom), detected_system="Unknown")]
    config = {"dats": {"index_path": str(index_path)}}

    results = identify(items, config=config)

    assert results
    assert "DAT_MATCH_CRC_SIZE" in results[0].signals
    assert "DAT_CROSS_CHECK" in results[0].signals
    assert results[0].reason == "crc32-size-cross-check"
    assert "NES" in results[0].candidates
    assert "SNES" in results[0].candidates


def test_identify_override_rule(tmp_path):
    rom = tmp_path / "override-game.rom"
    rom.write_text("data", encoding="utf-8")

    override_path = tmp_path / "identify_overrides.json"
    override_path.write_text(
        """
        {
            "rules": [
                {
                    "name": "local_override",
                    "platform_id": "Genesis",
                    "name_regex": "override-game",
                    "extension": ".rom"
                }
            ]
        }
        """,
        encoding="utf-8",
    )

    items = [ScanItem(input_path=str(rom), detected_system="Unknown")]
    config = {
        "dats": {"index_path": str(tmp_path / "missing.sqlite")},
        "identification_overrides": {"path": str(override_path), "enabled": True},
    }

    results = identify(items, config=config)

    assert results
    assert results[0].platform_id == "Genesis"
    assert results[0].is_exact is True
    assert "OVERRIDE_RULE" in results[0].signals
    assert results[0].reason == "override:local_override"


def test_add_identification_override_writes_file(tmp_path: Path) -> None:
    override_path = tmp_path / "identify_overrides.json"
    config = {"identification_overrides": {"path": str(override_path), "enabled": True}}

    ok, message, path = add_identification_override(
        input_path="C:/ROMs/Test/game.rom",
        platform_id="SNES",
        config=config,
    )

    assert ok is True
    assert message == "ok"
    assert Path(path).exists()

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data[0]["platform_id"] == "SNES"
    assert data[0]["paths"] == ["C:/ROMs/Test/game.rom"]


def test_add_identification_overrides_bulk_writes_file(tmp_path: Path) -> None:
    from src.app.controller import add_identification_overrides_bulk

    override_path = tmp_path / "identify_overrides.json"
    config = {"identification_overrides": {"path": str(override_path), "enabled": True}}

    ok, message, path = add_identification_overrides_bulk(
        input_paths=["C:/ROMs/Test/game1.rom", "C:/ROMs/Test/game2.rom"],
        platform_id="SNES",
        config=config,
    )

    assert ok is True
    assert message == "ok"
    assert Path(path).exists()

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data[0]["platform_id"] == "SNES"
    assert sorted(data[0]["paths"]) == ["C:/ROMs/Test/game1.rom", "C:/ROMs/Test/game2.rom"]
