import os
import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_scan_profile_writes_to_env_path(tmp_path, monkeypatch):
    from src.core.scan_service import run_scan

    source = tmp_path / "source"
    source.mkdir()
    (source / "file.bin").write_text("data")

    profile_path = tmp_path / "scan.prof"
    monkeypatch.setenv("ROM_SORTER_PROFILE", "1")
    monkeypatch.setenv("ROM_SORTER_PROFILE_PATH", str(profile_path))

    result = run_scan(str(source))
    assert result["source"]
    assert profile_path.exists()
