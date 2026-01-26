import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_run_scan_raises_scanner_error_for_invalid_path():
    from src.app.controller import run_scan
    from src.exceptions import ScannerError

    with pytest.raises(ScannerError):
        run_scan("/path/does/not/exist")
