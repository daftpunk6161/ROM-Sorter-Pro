import sys
import zipfile
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_lazy_archive_extraction_returns_minimal_info(tmp_path: Path) -> None:
    from src.scanning.high_performance_scanner import HighPerformanceScanner

    cfg = {"performance": {"optimization": {"lazy_archive_extraction": True}}, "scanner": {"chunk_size": 1024}}
    scanner = HighPerformanceScanner(config=cfg)

    zip_path = tmp_path / "lazy.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("game.nes", b"data")

    result = scanner._process_file(str(zip_path))
    assert result is not None
    assert result.get("is_archive") is True
    assert result.get("detection_source") == "archive-lazy"
