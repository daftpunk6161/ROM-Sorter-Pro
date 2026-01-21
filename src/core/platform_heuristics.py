"""Platform heuristic engine (config-driven, zero-false-positive oriented).

Reads src/platforms/platform_catalog.yaml (JSON fallback) and produces:
- candidates: ranked platform_id list
- signals: evidence summary

This module does NOT assign a definitive platform; it only provides candidates.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..config.schema import JSONSCHEMA_AVAILABLE, validate_config_schema


@dataclass(frozen=True)
class PlatformCandidate:
    platform_id: str
    score: float
    signals: Tuple[str, ...]
    signal_types: Tuple[str, ...]
    conflict_groups: Tuple[str, ...]


def _catalog_yaml_path() -> Path:
    override = os.environ.get("ROM_SORTER_PLATFORM_CATALOG", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / "platforms" / "platform_catalog.yaml"


def _catalog_json_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "platform_catalog.json"


def _catalog_schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "platforms" / "platform_catalog.schema.json"


def _catalog_cache_key() -> str:
    yaml_path = _catalog_yaml_path()
    json_path = _catalog_json_path()
    yaml_mtime = str(yaml_path.stat().st_mtime) if yaml_path.exists() else "0"
    json_mtime = str(json_path.stat().st_mtime) if json_path.exists() else "0"
    env_override = os.environ.get("ROM_SORTER_PLATFORM_CATALOG", "").strip()
    return "|".join([env_override, str(yaml_path), yaml_mtime, str(json_path), json_mtime])


def _load_json_loose(text: str) -> Optional[Dict[str, Any]]:
    try:
        cleaned = re.sub(r",\s*(?=[}\]])", "", text)
        data = json.loads(cleaned)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _load_yaml_data(path: Path) -> Optional[Dict[str, Any]]:
    raw = None
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return None
    try:
        import yaml  # type: ignore
    except Exception:
        return _load_json_loose(raw)
    try:
        data = yaml.safe_load(raw)
    except Exception:
        return _load_json_loose(raw)
    return data if isinstance(data, dict) else None


logger = logging.getLogger(__name__)


def _basic_catalog_validation(data: object) -> Tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "catalog_root_not_object"

    platforms = data.get("platforms")
    if not isinstance(platforms, list):
        return False, "platforms_not_list"

    policy = data.get("policy")
    if policy is not None and not isinstance(policy, dict):
        return False, "policy_not_object"

    required_keys = (
        "platform_id",
        "canonical_name",
        "aliases",
        "category",
        "media_types",
        "allowed_containers",
        "typical_extensions",
        "positive_tokens",
        "negative_tokens",
        "conflict_groups",
        "minimum_signals",
    )

    for idx, entry in enumerate(platforms):
        if not isinstance(entry, dict):
            return False, f"platform_{idx}_not_object"
        for key in required_keys:
            if key not in entry:
                return False, f"platform_{idx}_missing_{key}"
        if not isinstance(entry.get("aliases"), list):
            return False, f"platform_{idx}_aliases_not_list"
        if not isinstance(entry.get("media_types"), list):
            return False, f"platform_{idx}_media_types_not_list"
        if not isinstance(entry.get("allowed_containers"), list):
            return False, f"platform_{idx}_allowed_containers_not_list"
        if not isinstance(entry.get("typical_extensions"), list):
            return False, f"platform_{idx}_typical_extensions_not_list"
        if not isinstance(entry.get("positive_tokens"), list):
            return False, f"platform_{idx}_positive_tokens_not_list"
        if not isinstance(entry.get("negative_tokens"), list):
            return False, f"platform_{idx}_negative_tokens_not_list"
        if not isinstance(entry.get("conflict_groups"), list):
            return False, f"platform_{idx}_conflict_groups_not_list"
        if not isinstance(entry.get("minimum_signals"), list):
            return False, f"platform_{idx}_minimum_signals_not_list"

    return True, "ok"


@lru_cache(maxsize=4)
def _load_catalog(_cache_key: str) -> Tuple[List[Dict[str, object]], str, Dict[str, Any]]:
    yaml_path = _catalog_yaml_path()
    json_path = _catalog_json_path()

    data: Optional[Dict[str, Any]] = None

    if yaml_path.exists():
        data = _load_yaml_data(yaml_path)
        if data is None:
            logger.warning("Platform catalog YAML could not be loaded: %s", yaml_path)

    if data is None and json_path.exists():
        raw = None
        try:
            raw = json_path.read_text(encoding="utf-8")
        except Exception:
            raw = None
        if raw is not None:
            data = _load_json_loose(raw)

    if data is None:
        return [], "missing", {}

    if not isinstance(data, dict):
        return [], "invalid", {}

    if JSONSCHEMA_AVAILABLE:
        is_valid, error = validate_config_schema(
            data,
            schema_path=str(_catalog_schema_path())
        )
        if not is_valid:
            logger.warning("Platform catalog schema validation failed: %s", error)
            return [], "invalid", {}
    else:
        is_valid, reason = _basic_catalog_validation(data)
        if not is_valid:
            logger.warning("Platform catalog validation failed: %s", reason)
            return [], "invalid", {}

    platforms = data.get("platforms", [])
    policy = data.get("policy") if isinstance(data.get("policy"), dict) else {}

    if isinstance(platforms, list):
        return platforms, "ok" if platforms else "empty", policy

    return [], "invalid", policy


def _norm_token(token: str) -> str:
    return re.sub(r"\s+", " ", (token or "").strip().lower())


def _text_haystack(path: str) -> str:
    try:
        p = Path(path)
        parts = list(p.parts)
        parts.append(p.stem)
        parts.append(p.name)
        return " ".join(_norm_token(str(x)) for x in parts if x)
    except Exception:
        return _norm_token(path)


def _match_token(haystack: str, token: str) -> bool:
    token = _norm_token(token)
    if not token:
        return False
    return token in haystack


def evaluate_platform_candidates(path: str, *, container: Optional[str] = None) -> Dict[str, object]:
    """Return candidate platforms and signals for a file path.

    This is strictly heuristic and intentionally conservative.
    """

    platforms, status, policy = _load_catalog(_catalog_cache_key())
    if not platforms:
        return {
            "candidates": [],
            "candidate_systems": [],
            "signals": [],
            "candidate_details": [],
            "policy": policy or {},
            "reason": f"catalog_{status}"
        }

    p = Path(str(path or ""))
    ext = p.suffix.lower()
    container_type = (container or ext.lstrip(".")) or "raw"
    haystack = _text_haystack(str(path))

    candidates: List[PlatformCandidate] = []

    for entry in platforms:
        platform_id = str(entry.get("platform_id") or "").strip()
        if not platform_id:
            continue

        typical_exts = [str(x).lower() for x in (entry.get("typical_extensions") or [])]
        allowed_containers = [str(x).lower() for x in (entry.get("allowed_containers") or [])]
        positive_tokens = [str(x) for x in (entry.get("positive_tokens") or [])]
        negative_tokens = [str(x) for x in (entry.get("negative_tokens") or [])]
        minimum_signals = [str(x).lower() for x in (entry.get("minimum_signals") or [])]

        score = 0.0
        signals: List[str] = []
        signal_types: List[str] = []

        # Extension evidence
        if ext and ext in typical_exts:
            score += 2.0
            signals.append(f"EXT:{ext}")
            signal_types.append("extension")

        # Container evidence
        if allowed_containers and container_type in allowed_containers:
            score += 1.0
            signals.append(f"CONTAINER:{container_type}")
            signal_types.append("container")

        # Token evidence
        for token in positive_tokens:
            if _match_token(haystack, token):
                score += 1.0
                signals.append(f"TOKEN:{token}")
                signal_types.append("token")

        # Negative tokens
        for token in negative_tokens:
            if _match_token(haystack, token):
                score -= 2.0
                signals.append(f"NEG:{token}")
                signal_types.append("token")

        if minimum_signals:
            if not all(req in signal_types for req in minimum_signals):
                continue

        if score <= 0:
            continue

        candidates.append(
            PlatformCandidate(
                platform_id=platform_id,
                score=score,
                signals=tuple(signals),
                signal_types=tuple(signal_types),
                conflict_groups=tuple(str(x) for x in (entry.get("conflict_groups") or [])),
            )
        )

    candidates.sort(key=lambda c: (-c.score, c.platform_id))

    top_signals: List[str] = list(candidates[0].signals) if candidates else []
    candidate_ids = [c.platform_id for c in candidates]
    candidate_labels = [f"{c.platform_id} ({c.score:.1f})" for c in candidates]
    candidate_details = [
        {
            "platform_id": c.platform_id,
            "score": c.score,
            "signals": list(c.signals),
            "signal_types": list(c.signal_types),
            "conflict_groups": list(c.conflict_groups),
        }
        for c in candidates
    ]

    return {
        "candidates": candidate_labels[:10],
        "candidate_systems": candidate_ids[:10],
        "signals": top_signals[:10],
        "candidate_details": candidate_details[:10],
        "policy": policy or {},
        "reason": "ok" if candidates else "no_match",
    }
