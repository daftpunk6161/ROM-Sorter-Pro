"""Identification override helpers."""

from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import Config


def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_identification_overrides(cfg: Config) -> List[Dict[str, Any]]:
    override_cfg = cfg.get("identification_overrides", {})
    if isinstance(override_cfg, str):
        override_cfg = {"path": override_cfg}
    if not isinstance(override_cfg, dict):
        return []
    if override_cfg.get("enabled") is False:
        return []

    raw_path = str(override_cfg.get("path") or "config/identify_overrides.yaml").strip()
    if not raw_path:
        return []
    path = Path(raw_path)
    if not path.is_absolute():
        path = (_resolve_repo_root() / path).resolve()
    if not path.exists():
        return []

    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return []

    data: Optional[Dict[str, Any]] = None
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(raw)
        except Exception:
            data = None
    else:
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(raw)
        except Exception:
            try:
                data = json.loads(raw)
            except Exception:
                data = None

    if isinstance(data, list):
        return [rule for rule in data if isinstance(rule, dict)]
    if isinstance(data, dict):
        rules = data.get("rules") or []
        if isinstance(rules, list):
            return [rule for rule in rules if isinstance(rule, dict)]
    return []


def _match_identification_override(rule: Dict[str, Any], input_path: str) -> bool:
    path_str = str(input_path or "")
    if not path_str:
        return False
    filename = Path(path_str).name
    suffix = Path(path_str).suffix.lower()

    matchers = []

    paths = rule.get("paths") or rule.get("path_equals")
    if isinstance(paths, str):
        paths = [paths]
    if isinstance(paths, list):
        matchers.append(any(str(p) == path_str for p in paths))

    path_regex = rule.get("path_regex")
    if path_regex:
        try:
            matchers.append(re.search(str(path_regex), path_str) is not None)
        except Exception:
            return False

    name_regex = rule.get("name_regex") or rule.get("filename_regex")
    if name_regex:
        try:
            matchers.append(re.search(str(name_regex), filename) is not None)
        except Exception:
            return False

    path_glob = rule.get("path_glob")
    if path_glob:
        matchers.append(fnmatch.fnmatch(path_str, str(path_glob)))

    contains = rule.get("contains")
    if contains:
        if isinstance(contains, str):
            contains = [contains]
        if isinstance(contains, list):
            matchers.append(any(str(token).lower() in path_str.lower() for token in contains))

    ext = rule.get("extension") or rule.get("ext")
    if ext:
        ext_val = str(ext).lower()
        if not ext_val.startswith("."):
            ext_val = f".{ext_val}"
        matchers.append(suffix == ext_val)

    starts_with = rule.get("starts_with")
    if starts_with:
        matchers.append(filename.lower().startswith(str(starts_with).lower()))

    ends_with = rule.get("ends_with")
    if ends_with:
        matchers.append(filename.lower().endswith(str(ends_with).lower()))

    if not matchers:
        return False
    return all(matchers)


def _apply_identification_override(
    input_path: str,
    overrides: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    for rule in overrides:
        if not _match_identification_override(rule, input_path):
            continue
        platform = rule.get("platform_id") or rule.get("platform") or rule.get("system")
        if not platform:
            continue
        name = rule.get("name") or rule.get("id") or "override"
        confidence = rule.get("confidence")
        try:
            confidence_val = float(confidence) if confidence is not None else 1.0
        except Exception:
            confidence_val = 1.0
        return {
            "platform_id": str(platform),
            "name": str(name),
            "confidence": confidence_val,
        }
    return None
