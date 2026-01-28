"""Version utilities for ROM Sorter Pro."""

from __future__ import annotations

import json
from pathlib import Path


def load_version() -> str:
    config_path = Path(__file__).resolve().parents[1] / "src" / "config.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        meta = data.get("_metadata", {}) if isinstance(data, dict) else {}
        version = str(meta.get("version") or "").strip()
        return version or "1.0.0"
    except Exception:
        return "1.0.0"
