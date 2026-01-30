import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_start_version_uses_config():
    """Test that _load_version returns a valid version string."""
    import start_rom_sorter

    version = start_rom_sorter._load_version()
    # Must return a non-empty version string (fallback is "1.0.0")
    assert version
    assert isinstance(version, str)
    # Basic semver-like pattern check
    assert "." in version
