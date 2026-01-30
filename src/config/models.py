from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field
    from pydantic import ConfigDict

    _CONFIG_DICT_AVAILABLE = True
except Exception:  # pragma: no cover
    BaseModel = object  # type: ignore
    Field = lambda default=None, **kwargs: default  # type: ignore
    ConfigDict = None  # type: ignore
    _CONFIG_DICT_AVAILABLE = False


if _CONFIG_DICT_AVAILABLE:
    class _BaseConfigModel(BaseModel):
        model_config = ConfigDict(extra="allow")
else:
    class _BaseConfigModel:  # type: ignore
        class Config:  # type: ignore
            extra = "allow"


class GuiFavorite(_BaseConfigModel):
    source: str
    dest: str
    label: Optional[str] = None


class GuiSettings(_BaseConfigModel):
    default_conflict_policy: Optional[str] = None
    log_visible: Optional[bool] = None
    window_width: Optional[int] = None
    window_height: Optional[int] = None
    favorites: List[GuiFavorite] = Field(default_factory=list)


class ScannerConfig(_BaseConfigModel):
    use_high_performance: Optional[bool] = None
    max_threads: Optional[int] = None
    chunk_size: Optional[int] = None
    follow_symlinks: Optional[bool] = None
    use_cache: Optional[bool] = None
    recursive: Optional[bool] = None
    max_depth: Optional[int] = None


class UiConfig(_BaseConfigModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    remember_window_state: Optional[bool] = None
    remember_last_directories: Optional[bool] = None
    show_tooltips: Optional[bool] = None
    animation_speed: Optional[float] = None
    icon_size: Optional[str] = None
    enable_drag_drop: Optional[bool] = None
    show_status_bar: Optional[bool] = None
    show_toolbar: Optional[bool] = None


class DatabaseConfig(_BaseConfigModel):
    use_memory_cache: Optional[bool] = None
    cache_size_mb: Optional[int] = None
    auto_backup: Optional[bool] = None
    backup_interval_days: Optional[int] = None
    backup_max_count: Optional[int] = None
    vacuum_on_exit: Optional[bool] = None


class CacheConfig(_BaseConfigModel):
    enabled: Optional[bool] = None
    max_size_mb: Optional[int] = None
    clean_on_exit: Optional[bool] = None
    expiry_days: Optional[int] = None


class DatsConfig(_BaseConfigModel):
    import_paths: List[str] = Field(default_factory=list)


class ProgressPersistenceConfig(_BaseConfigModel):
    enabled: Optional[bool] = None
    save_interval_sec: Optional[float] = None
    clear_on_success: Optional[bool] = None
    scan_resume_path: Optional[str] = None
    sort_resume_path: Optional[str] = None


class RollbackConfig(_BaseConfigModel):
    enabled: Optional[bool] = None
    manifest_path: Optional[str] = None


class BackupConfig(_BaseConfigModel):
    enabled: Optional[bool] = None
    local_dir: Optional[str] = None
    onedrive_enabled: Optional[bool] = None
    onedrive_dir: Optional[str] = None


class PluginsConfig(_BaseConfigModel):
    enabled: Optional[bool] = None
    paths: List[str] = Field(default_factory=list)


class FeaturesConfig(_BaseConfigModel):
    progress_persistence: Optional[ProgressPersistenceConfig] = None
    rollback: Optional[RollbackConfig] = None
    backup: Optional[BackupConfig] = None
    plugins: Optional[PluginsConfig] = None


class ConfigModel(_BaseConfigModel):
    gui_settings: Optional[GuiSettings] = None
    scanner: Optional[ScannerConfig] = None
    ui: Optional[UiConfig] = None
    database: Optional[DatabaseConfig] = None
    cache: Optional[CacheConfig] = None
    dats: Optional[DatsConfig] = None
    features: Optional[FeaturesConfig] = None


def validate_config(payload: Dict[str, Any]) -> ConfigModel:
    if not _CONFIG_DICT_AVAILABLE:
        raise RuntimeError("pydantic is not available")
    return ConfigModel.model_validate(payload) if hasattr(ConfigModel, "model_validate") else ConfigModel(**payload)
