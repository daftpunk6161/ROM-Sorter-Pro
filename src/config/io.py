"""Config I/O utilities."""

from __future__ import annotations

import json
import os
import logging
from typing import Any, Dict, Optional

from .schema import validate_config_schema
from .pydantic_models import validate_with_pydantic

logger = logging.getLogger(__name__)


def _normalize_gui_settings(config_data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(config_data, dict):
        return {}

    interface_cfg = config_data.get("interface")
    interface_gui = {}
    if isinstance(interface_cfg, dict):
        interface_gui = interface_cfg.get("gui_settings") or {}
        if not isinstance(interface_gui, dict):
            interface_gui = {}

    gui_cfg = config_data.get("gui_settings") or {}
    if not isinstance(gui_cfg, dict):
        gui_cfg = {}

    if interface_gui:
        if not gui_cfg:
            gui_cfg = dict(interface_gui)
        else:
            for key, value in interface_gui.items():
                gui_cfg.setdefault(key, value)
        config_data["gui_settings"] = gui_cfg

        if isinstance(interface_cfg, dict) and "gui_settings" in interface_cfg:
            interface_cfg.pop("gui_settings", None)
            config_data["interface"] = interface_cfg

    return config_data


def get_config_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    primary = os.path.join(base_dir, "config.json")
    if os.path.exists(primary):
        return primary
    return os.path.join(base_dir, "src", "config.json")


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    if config_path is None:
        config_path = get_config_path()
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                data = _normalize_gui_settings(data)
                ok, error = validate_config_schema(data)
                if not ok:
                    logger.warning("Config schema validation failed: %s", error)
                if os.getenv("ROM_SORTER_USE_PYDANTIC") == "1":
                    if not validate_with_pydantic(data):
                        logger.warning("Pydantic config validation failed")
                return data
            return {}
    except Exception:
        return {}


def save_config(config_data: Dict[str, Any], config_path: Optional[str] = None) -> bool:
    if config_path is None:
        config_path = get_config_path()
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        data = dict(config_data or {})
        data = _normalize_gui_settings(data)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False
