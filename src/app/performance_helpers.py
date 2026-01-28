"""Performance-related helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..config import Config, load_config


def _load_cfg(config: Optional[Config | Dict[str, Any]]) -> Config:
    if isinstance(config, Config):
        return config
    if isinstance(config, dict):
        return Config(config)
    try:
        return Config(load_config())
    except Exception:
        return Config()


def _get_dict(cfg: Config, *keys: str) -> Dict[str, Any]:
    if not keys:
        return {}
    current: Any = cfg.get(keys[0], {})
    for key in keys[1:]:
        if isinstance(current, dict):
            current = current.get(key, {})
        else:
            current = {}
    return current if isinstance(current, dict) else {}


def _progress_batch_enabled(cfg: Config) -> bool:
    try:
        opt_cfg = _get_dict(cfg, "performance", "optimization")
        return bool(opt_cfg.get("enable_progress_batching", True))
    except Exception:
        return True


def _resolve_copy_buffer_size(cfg: Config) -> int:
    size = None
    try:
        perf_cfg = _get_dict(cfg, "performance", "processing")
        size = perf_cfg.get("io_buffer_size")
    except Exception:
        size = None
    try:
        size = int(size or 1024 * 1024)
    except Exception:
        size = 1024 * 1024
    return max(64 * 1024, min(8 * 1024 * 1024, size))
