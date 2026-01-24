import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_start_version_uses_config():
    import json
    import start_rom_sorter

    config_path = ROOT / "src" / "config.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    expected = str(data.get("_metadata", {}).get("version") or "").strip()

    assert expected
    assert start_rom_sorter._load_version() == expected
