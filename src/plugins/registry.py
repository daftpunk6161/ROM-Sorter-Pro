"""Lightweight plugin registry for detectors and converters."""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

DetectorFunc = Callable[[str, Optional[str]], Any]


@dataclass(frozen=True)
class DetectorPlugin:
    name: str
    func: DetectorFunc
    priority: int = 50


@dataclass
class PluginRegistry:
    detectors: List[DetectorPlugin] = field(default_factory=list)
    converter_rules: List[Dict[str, Any]] = field(default_factory=list)

    def register_detector(self, name: str, func: DetectorFunc, *, priority: int = 50) -> None:
        self.detectors.append(DetectorPlugin(name=name, func=func, priority=int(priority)))

    def register_converter_rule(self, rule: Dict[str, Any]) -> None:
        if isinstance(rule, dict):
            self.converter_rules.append(rule)


_REGISTRY_CACHE: Optional[PluginRegistry] = None
_REGISTRY_PATHS: Optional[tuple[str, ...]] = None


def _iter_plugin_paths(cfg: Optional[dict]) -> List[Path]:
    env_paths = os.environ.get("ROM_SORTER_PLUGIN_PATHS", "").strip()
    if env_paths:
        paths = [Path(part.strip()) for part in env_paths.split(";") if part.strip()]
        return paths

    cfg_paths: List[Path] = []
    if cfg:
        try:
            plugin_cfg = (cfg.get("features") or {}).get("plugins") or {}
            raw_paths = plugin_cfg.get("paths") or []
            if isinstance(raw_paths, str):
                raw_paths = [raw_paths]
            for entry in raw_paths:
                if entry:
                    cfg_paths.append(Path(str(entry)))
        except Exception:
            cfg_paths = []

    default_path = Path(__file__).resolve().parents[2] / "plugins"
    if not cfg_paths:
        return [default_path]
    return cfg_paths


def _load_module_from_path(path: Path, logger: logging.Logger) -> Optional[Any]:
    if not path.exists() or not path.is_file():
        return None
    if path.name.startswith("_") or path.suffix.lower() != ".py":
        return None
    module_name = f"rom_sorter_plugin_{path.stem}_{abs(hash(str(path)))}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as exc:
        logger.warning("Plugin load failed for %s: %s", path, exc)
        return None


def get_plugin_registry(cfg: Optional[dict] = None, *, force_reload: bool = False) -> PluginRegistry:
    logger = logging.getLogger(__name__)
    paths = _iter_plugin_paths(cfg)
    normalized = tuple(str(path.resolve()) for path in paths)

    global _REGISTRY_CACHE, _REGISTRY_PATHS
    if not force_reload and _REGISTRY_CACHE is not None and _REGISTRY_PATHS == normalized:
        return _REGISTRY_CACHE

    registry = PluginRegistry()

    enabled = True
    if cfg is not None:
        try:
            plugin_cfg = (cfg.get("features") or {}).get("plugins") or {}
            enabled = bool(plugin_cfg.get("enabled", True))
        except Exception:
            enabled = True

    if not enabled:
        _REGISTRY_CACHE = registry
        _REGISTRY_PATHS = normalized
        return registry

    for root in paths:
        if not root.exists() or not root.is_dir():
            continue
        for plugin_path in sorted(root.glob("*.py")):
            module = _load_module_from_path(plugin_path, logger)
            if module is None:
                continue
            register = getattr(module, "register", None)
            if callable(register):
                try:
                    register(registry)
                except Exception as exc:
                    logger.warning("Plugin register failed for %s: %s", plugin_path, exc)

    registry.detectors.sort(key=lambda item: item.priority)
    _REGISTRY_CACHE = registry
    _REGISTRY_PATHS = normalized
    return registry


def collect_plugin_detectors(cfg: Optional[dict] = None) -> List[DetectorPlugin]:
    return list(get_plugin_registry(cfg).detectors)


def collect_plugin_converters(cfg: Optional[dict] = None) -> List[Dict[str, Any]]:
    return list(get_plugin_registry(cfg).converter_rules)
