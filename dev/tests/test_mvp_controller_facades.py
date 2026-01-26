import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_scan_controller_facade_raises_scanner_error():
    from src.app.scan_controller import run_scan
    from src.exceptions import ScannerError

    with pytest.raises(ScannerError):
        run_scan("/nope/invalid")
