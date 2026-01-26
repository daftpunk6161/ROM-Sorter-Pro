"""Optional Pydantic config models (lazy use)."""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from pydantic import BaseModel
    PYDANTIC_AVAILABLE = True
except Exception:
    BaseModel = object  # type: ignore
    PYDANTIC_AVAILABLE = False


class SortingConfigModel(BaseModel if PYDANTIC_AVAILABLE else object):
    console_sorting_enabled: Optional[bool] = True
    create_console_folders: Optional[bool] = True
    region_based_sorting: Optional[bool] = False
    preserve_folder_structure: Optional[bool] = False


class AppConfigModel(BaseModel if PYDANTIC_AVAILABLE else object):
    features: Optional[Dict[str, Any]] = None
    dats: Optional[Dict[str, Any]] = None


def validate_with_pydantic(config_data: Dict[str, Any]) -> bool:
    if not PYDANTIC_AVAILABLE:
        return False
    try:
        AppConfigModel(**(config_data or {}))
        return True
    except Exception:
        return False
