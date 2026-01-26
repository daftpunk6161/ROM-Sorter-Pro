import sys
import zipfile
import zlib
import hashlib
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

pytestmark = pytest.mark.integration


def _write_dat_index(index_path: Path, entries: list[tuple[bytes, str]]) -> None:
    from src.core.dat_index_sqlite import DatIndexSqlite

    index = DatIndexSqlite(index_path)
    cur = index.conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO dat_files (dat_id, source_path, mtime, size_bytes, active) VALUES (1, ?, 0, 0, 1)",
        ("test.dat",),
    )
    for payload, platform_id in entries:
        sha1 = hashlib.sha1(payload).hexdigest()
        crc32 = f"{zlib.crc32(payload) & 0xFFFFFFFF:08x}"
        size_bytes = len(payload)
        cur.execute(
            "INSERT INTO rom_hashes (dat_id, platform_id, rom_name, set_name, crc32, sha1, size_bytes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, platform_id, "rom", "set", crc32, sha1, size_bytes),
        )
    index.conn.commit()
    index.close()


def test_zip_slip_entries_are_ignored(tmp_path):
    from src.detectors.archive_detector import detect_console_from_archive

    archive_path = tmp_path / "archive.zip"

    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("../evil.nes", b"bad")

    console, confidence = detect_console_from_archive(str(archive_path))
    assert console == "Archive"
    assert confidence <= 0.5


def test_zip_mixed_content_returns_unknown(tmp_path):
    from src.scanning.high_performance_scanner import HighPerformanceScanner

    index_path = tmp_path / "dat_index.sqlite"
    good_payload = b"GOOD-ROM"
    bad_payload = b"UNKNOWN-ROM"
    _write_dat_index(index_path, [(good_payload, "NES")])

    archive_path = tmp_path / "mixed.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("good.nes", good_payload)
        zf.writestr("bad.bin", bad_payload)

    scanner = HighPerformanceScanner(config={"dats": {"index_path": str(index_path)}})
    result = scanner._process_zip_archive(str(archive_path))

    assert result is not None
    assert result.get("system") == "Unknown"
    assert result.get("detection_source") == "zip-mixed"
    assert result.get("is_exact") is False


def test_zip_all_entries_match_single_system(tmp_path):
    from src.scanning.high_performance_scanner import HighPerformanceScanner

    index_path = tmp_path / "dat_index.sqlite"
    payload_a = b"ROM-A"
    payload_b = b"ROM-B"
    _write_dat_index(index_path, [(payload_a, "SNES"), (payload_b, "SNES")])

    archive_path = tmp_path / "single_system.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("a.sfc", payload_a)
        zf.writestr("b.sfc", payload_b)

    scanner = HighPerformanceScanner(config={"dats": {"index_path": str(index_path)}})
    result = scanner._process_zip_archive(str(archive_path))

    assert result is not None
    assert result.get("system") == "SNES"
    assert result.get("is_exact") is True
