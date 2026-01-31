"""Optional Pydantic config models (lazy use)."""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from pydantic import BaseModel
    PYDANTIC_AVAILABLE = True
except Exception:
    class _BaseModelFallback:  # type: ignore
        """Fallback base model when pydantic is unavailable."""

    BaseModel = _BaseModelFallback  # type: ignore
    PYDANTIC_AVAILABLE = False


class SortingConfigModel(BaseModel):  # type: ignore[misc]
    console_sorting_enabled: Optional[bool] = True
    create_console_folders: Optional[bool] = True
    region_based_sorting: Optional[bool] = False
    preserve_folder_structure: Optional[bool] = False
    rename_template: Optional[str] = None
    copy_first_staging: Optional[bool] = False
    copy_first_staging_dir: Optional[str] = None
    estimated_throughput_mb_s: Optional[float] = None


class AppConfigModel(BaseModel):  # type: ignore[misc]
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
