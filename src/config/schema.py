"""Config schema validation helpers."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except Exception:
    jsonschema = None
    JSONSCHEMA_AVAILABLE = False


def validate_config_schema(config_data: Dict[str, Any], schema_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    if not JSONSCHEMA_AVAILABLE:
        return True, None

    if schema_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        schema_path = os.path.join(base_dir, "config-schema.json")

    if not os.path.exists(schema_path):
        return True, None

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(instance=config_data, schema=schema)
        return True, None
    except Exception as exc:
        return False, str(exc)
