import json
import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core import normalization  # noqa: E402

pytestmark = pytest.mark.integration


def test_load_converters_persists_yaml(monkeypatch, tmp_path):
    converters_path = tmp_path / "converters.yaml"

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

    monkeypatch.setattr(normalization, "_converters_path", lambda: converters_path)
    monkeypatch.setattr(normalization, "_load_yaml_or_json", lambda _path: {"version": "1.0", "converters": []})
    monkeypatch.setattr(normalization, "load_config", lambda _path=None: config)

    converters = normalization.load_converters()

    assert converters
    assert converters_path.exists()
    data = json.loads(converters_path.read_text(encoding="utf-8"))
    assert data.get("converters")
