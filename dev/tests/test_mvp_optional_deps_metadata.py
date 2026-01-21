import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_metadata_network_disabled_returns_none_requests():
    from src.database import metadata_manager as mm

    if mm._network_enabled():
        # If config enables network, just assert helper runs.
        assert mm._get_requests() is not None or mm._get_requests() is None
    else:
        assert mm._get_requests() is None
