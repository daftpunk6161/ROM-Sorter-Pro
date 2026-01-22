import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core import normalization

pytestmark = pytest.mark.integration


def test_load_converters_falls_back_to_config(monkeypatch):
    config = {
        "features": {
            "sorting": {
                "conversion": {
                    "enabled": True,
                    "tools": {"chdman": "C:/tools/chdman.exe"},
                    "rules": [
                        {
                            "name": "cd_to_chd",
                            "enabled": True,
                            "systems": ["PS1"],
                            "extensions": [".cue"],
                            "to_extension": ".chd",
                            "tool": "chdman",
                            "args": ["createcd", "-i", "{src}", "-o", "{dst}"]
                        }
                    ],
                }
            }
        }
    }

    monkeypatch.setattr(normalization, "_load_yaml_or_json", lambda _path: {"version": "1.0", "converters": []})
    monkeypatch.setattr(normalization, "load_config", lambda _path=None: config)

    converters = normalization.load_converters()

    assert converters
    entry = converters[0]
    assert entry["converter_id"] == "cd_to_chd"
    assert entry["output_extension"] == ".chd"
    assert entry["exe_path"].endswith("chdman.exe")
    assert "{input}" in entry["args_template"]
    assert "{output}" in entry["args_template"]
    assert "DiscTrackSet" in entry["input_kinds"]
