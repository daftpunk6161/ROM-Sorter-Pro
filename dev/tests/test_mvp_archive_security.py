import sys
import zipfile
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


import pytest

pytestmark = pytest.mark.integration


def test_zip_slip_entries_are_ignored(tmp_path):
    from src.detectors.archive_detector import detect_console_from_archive

    archive_path = tmp_path / "archive.zip"

    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("../evil.nes", b"bad")

    console, confidence = detect_console_from_archive(str(archive_path))
    assert console == "Archive"
    assert confidence <= 0.5
