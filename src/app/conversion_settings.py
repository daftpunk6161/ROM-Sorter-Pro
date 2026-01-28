"""Conversion settings helpers."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import logging

logger = logging.getLogger(__name__)

from ..config import Config
from .models import ScanItem


def _is_dat_match(item: ScanItem) -> bool:
    source = str(item.detection_source or "")
    if source.startswith("dat:"):
        return True
    raw = item.raw or {}
    raw_source = str(raw.get("detection_source") or "")
    return raw_source.startswith("dat:")


def _normalize_extension(ext: str) -> str:
    val = str(ext or "").strip().lower()
    if not val:
        return ""
    return val if val.startswith(".") else f".{val}"


def _normalize_system_name(name: str) -> str:
    return " ".join(str(name or "").lower().split())


def _resolve_tool_path(tool_value: Optional[str]) -> Optional[str]:
    if not tool_value:
        return None
    tool = str(tool_value).strip()
    if not tool:
        return None

    if os.path.isabs(tool):
        return tool if Path(tool).exists() else None

    repo_root = Path(__file__).resolve().parents[2]
    candidate = (repo_root / tool).resolve()
    if candidate.exists():
        return str(candidate)

    found = shutil.which(tool)
    if found:
        return found

    return None


def _resolve_conversion_settings(cfg: Config) -> Dict[str, Any]:
    try:
        features_cfg = cfg.get("features", {})
        if not isinstance(features_cfg, dict):
            features_cfg = {}
        sorting_cfg = features_cfg.get("sorting", {})
        if not isinstance(sorting_cfg, dict):
            sorting_cfg = {}
    except Exception:
        sorting_cfg = {}
    conversion_cfg = sorting_cfg.get("conversion", {}) or {}

    enabled = bool(conversion_cfg.get("enabled", False))
    require_dat = bool(conversion_cfg.get("require_dat_match", True))
    fallback_on_missing = bool(conversion_cfg.get("fallback_on_missing_tool", True))
    tools = conversion_cfg.get("tools", {}) or {}
    rules = conversion_cfg.get("rules", []) or []

    return {
        "enabled": enabled,
        "require_dat": require_dat,
        "fallback_on_missing": fallback_on_missing,
        "tools": tools,
        "rules": rules,
    }


def _match_conversion_rule(
    *,
    item: "ScanItem",
    src: Path,
    conversion_settings: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not conversion_settings.get("enabled"):
        return None

    if conversion_settings.get("require_dat") and not _is_dat_match(item):
        return None

    src_ext = _normalize_extension(src.suffix)
    if not src_ext:
        return None

    item_system = _normalize_system_name(item.detected_system)

    for rule in conversion_settings.get("rules", []) or []:
        rule_error = False
        try:
            if not rule or not isinstance(rule, dict):
                continue
            if not bool(rule.get("enabled", True)):
                continue

            exts = rule.get("extensions") or []
            if isinstance(exts, str):
                exts = [exts]
            norm_exts = {_normalize_extension(ext) for ext in exts if ext}
            if norm_exts and src_ext not in norm_exts:
                continue

            systems = rule.get("systems") or []
            if isinstance(systems, str):
                systems = [systems]
            if systems:
                norm_systems = {_normalize_system_name(s) for s in systems if s}
                if item_system not in norm_systems:
                    continue

            to_ext = _normalize_extension(rule.get("to_extension") or "")
            if not to_ext:
                continue

            tool_key = str(rule.get("tool") or "").strip()
            tool_value = conversion_settings.get("tools", {}).get(tool_key) or tool_key
            tool_path = _resolve_tool_path(tool_value)
            if not tool_path:
                return {"missing_tool": True, "rule": rule}

            return {
                "tool": tool_path,
                "tool_key": tool_key,
                "rule": rule,
                "to_extension": to_ext,
            }
        except Exception as exc:
            rule_error = True
            logger.debug("Conversion rule match failed: %s", exc)
        if rule_error:
            continue

    return None


def _match_conversion_rule_for_audit(
    *,
    item: "ScanItem",
    src: Path,
    conversion_settings: Dict[str, Any],
    include_disabled: bool,
) -> Optional[Dict[str, Any]]:
    src_ext = _normalize_extension(src.suffix)
    if not src_ext:
        return None

    item_system = _normalize_system_name(item.detected_system)
    require_dat = bool(conversion_settings.get("require_dat", True))
    dat_match = _is_dat_match(item)

    for rule in conversion_settings.get("rules", []) or []:
        rule_error = False
        try:
            if not rule or not isinstance(rule, dict):
                continue
            enabled = bool(rule.get("enabled", True))
            if not enabled and not include_disabled:
                continue

            exts = rule.get("extensions") or []
            if isinstance(exts, str):
                exts = [exts]
            norm_exts = {_normalize_extension(ext) for ext in exts if ext}
            if norm_exts and src_ext not in norm_exts:
                continue

            systems = rule.get("systems") or []
            if isinstance(systems, str):
                systems = [systems]
            if systems:
                norm_systems = {_normalize_system_name(s) for s in systems if s}
                if item_system not in norm_systems:
                    continue

            to_ext = _normalize_extension(rule.get("to_extension") or "")
            if not to_ext:
                continue

            tool_key = str(rule.get("tool") or "").strip()
            tool_value = conversion_settings.get("tools", {}).get(tool_key) or tool_key
            tool_path = _resolve_tool_path(tool_value)
            require_tool = bool(rule.get("require_tool", True))
            missing_tool = bool(require_tool and not tool_path)

            return {
                "rule": rule,
                "rule_name": str(rule.get("name") or "") or None,
                "enabled": enabled,
                "to_extension": to_ext,
                "tool_key": tool_key or None,
                "missing_tool": missing_tool,
                "require_dat": require_dat,
                "dat_match": dat_match,
            }
        except Exception as exc:
            rule_error = True
            logger.debug("Conversion audit rule match failed: %s", exc)
        if rule_error:
            continue

    return None


def _build_conversion_args(rule: Dict[str, Any], src: Path, dst: Path) -> List[str]:
    args = rule.get("args") or []
    if isinstance(args, str):
        args = [args]

    replacements = {
        "{src}": str(src),
        "{dst}": str(dst),
        "{src_dir}": str(src.parent),
        "{dst_dir}": str(dst.parent),
        "{src_stem}": src.stem,
        "{dst_stem}": dst.stem,
        "{src_name}": src.name,
        "{dst_name}": dst.name,
        "{src_ext}": src.suffix.lstrip("."),
        "{dst_ext}": dst.suffix.lstrip("."),
    }

    built: List[str] = []
    for arg in args:
        value = str(arg)
        for key, replacement in replacements.items():
            value = value.replace(key, replacement)
        if value:
            built.append(value)
    return built
