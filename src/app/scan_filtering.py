"""Scan item filtering and dedupe helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union
import logging

from ..config import Config, load_config
from .models import ScanItem
from .naming_helpers import (
    infer_languages_and_version_from_name,
    infer_region_from_name,
    normalize_title_for_dedupe,
    version_score,
)

logger = logging.getLogger(__name__)
DEFAULT_REGION_PRIORITY: Tuple[str, ...] = (
    "Europe",
    "USA",
    "World",
    "Japan",
    "Other",
    "Unknown",
)

DEFAULT_LANGUAGE_PRIORITY: Tuple[str, ...] = (
    "De",
    "En",
    "Fr",
    "Es",
    "It",
    "Pt",
    "Nl",
)


def _load_cfg(config: Optional[Config | Dict[str, Any]]) -> Config:
    if isinstance(config, Config):
        return config
    if isinstance(config, dict):
        return Config(config)
    try:
        return Config(load_config())
    except Exception:
        return Config()


def select_preferred_variants(
    items: List[ScanItem],
    *,
    region_priority: Tuple[str, ...] = DEFAULT_REGION_PRIORITY,
    language_priority: Tuple[str, ...] = DEFAULT_LANGUAGE_PRIORITY,
) -> List[ScanItem]:
    """Dedupe multiple region variants of the same title."""

    priority_index = {name: i for i, name in enumerate(region_priority)}
    lang_index = {name: i for i, name in enumerate(language_priority)}

    def region_rank(region: Optional[str]) -> int:
        r = (region or "Unknown").strip() or "Unknown"
        return priority_index.get(r, len(region_priority))

    def best_language_rank(languages: Tuple[str, ...]) -> int:
        if not languages:
            return len(language_priority)
        best = len(language_priority)
        for lang in languages:
            best = min(best, lang_index.get(str(lang), len(language_priority)))
        return best

    def variant_score(it: ScanItem) -> Tuple[int, int, int, float, int, str]:
        langs = tuple(getattr(it, "languages", ()) or ())
        version_val = getattr(it, "version", None)
        if not version_val:
            try:
                _, version_val = infer_languages_and_version_from_name(Path(it.input_path).name)
            except Exception:
                version_val = None
        return (
            region_rank(getattr(it, "region", None)),
            0 if langs else 1,
            best_language_rank(langs),
            -version_score(version_val),
            -len(langs),
            str(it.input_path or ""),
        )

    chosen: Dict[Tuple[str, str], ScanItem] = {}
    for it in items:
        key = (
            (it.detected_system or "Unknown").strip() or "Unknown",
            normalize_title_for_dedupe(it.input_path),
        )

        current = chosen.get(key)
        if current is None:
            chosen[key] = it
            continue

        if variant_score(it) < variant_score(current):
            chosen[key] = it

    return sorted(chosen.values(), key=lambda x: (x.input_path or ""))


def filter_scan_items(
    items: List[ScanItem],
    *,
    system_filter: Union[str, Sequence[str]] = "All",
    language_filter: Union[str, Sequence[str]] = "All",
    version_filter: str = "All",
    region_filter: Union[str, Sequence[str]] = "All",
    extension_filter: str = "",
    min_size_mb: Optional[float] = None,
    max_size_mb: Optional[float] = None,
    dedupe_variants: bool = False,
    region_priority: Tuple[str, ...] = DEFAULT_REGION_PRIORITY,
    language_priority: Tuple[str, ...] = DEFAULT_LANGUAGE_PRIORITY,
    config: Optional[Config] = None,
) -> List[ScanItem]:
    """Filter scan items by language/version/region and optionally dedupe by preferred region."""

    cfg = _load_cfg(config)
    try:
        prioritization = cfg.get("prioritization", {}) or {}
        region_priorities = prioritization.get("region_priorities", {}) or {}
        language_priorities = prioritization.get("language_priorities", {}) or {}
        region_order = prioritization.get("region_order", []) or []
        language_order = prioritization.get("language_order", []) or []
    except Exception:
        region_priorities = {}
        language_priorities = {}
        region_order = []
        language_order = []

    def _build_priority(default: Tuple[str, ...], order_list: Sequence[str], priority_map: Dict[str, Any]) -> Tuple[str, ...]:
        ordered: List[str] = []
        for entry in order_list:
            value = str(entry).strip()
            if value and value not in ordered:
                ordered.append(value)
        if isinstance(priority_map, dict):
            ranked = sorted(
                ((str(k), int(v)) for k, v in priority_map.items()),
                key=lambda x: x[1],
            )
            for key, _ in ranked:
                if key and key not in ordered:
                    ordered.append(key)
        for entry in default:
            if entry not in ordered:
                ordered.append(entry)
        return tuple(ordered)

    region_priority = _build_priority(region_priority, region_order, region_priorities)
    language_priority = _build_priority(language_priority, language_order, language_priorities)

    def _normalize_filter_values(value: Union[str, Sequence[str]]) -> Set[str]:
        if value is None:
            return {"All"}
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return {"All"}
            parts = [part.strip() for part in re.split(r"[;,]", raw) if part.strip()]
            if len(parts) > 1:
                return set(parts)
            return {raw}
        values = {str(v).strip() for v in value if str(v).strip()}
        return values or {"All"}

    system_values = _normalize_filter_values(system_filter)
    lang_values = _normalize_filter_values(language_filter)
    ver = (version_filter or "All").strip() or "All"
    region_values = _normalize_filter_values(region_filter)
    ext_raw = (extension_filter or "").strip()
    ext_filters = set()
    if ext_raw:
        for chunk in re.split(r"[;,\s]+", ext_raw):
            chunk = chunk.strip().lower()
            if not chunk:
                continue
            ext_filters.add(chunk if chunk.startswith(".") else f".{chunk}")
    min_bytes = int(min_size_mb * 1024 * 1024) if min_size_mb is not None else None
    max_bytes = int(max_size_mb * 1024 * 1024) if max_size_mb is not None else None

    def norm_langs(item: "ScanItem") -> Tuple[str, ...]:
        langs = getattr(item, "languages", ()) or ()
        if langs:
            return tuple(langs)
        try:
            parsed, _ = infer_languages_and_version_from_name(Path(item.input_path).name)
            return tuple(parsed)
        except Exception:
            return ()

    def norm_ver(item: "ScanItem") -> str:
        v = getattr(item, "version", None)
        if v:
            return str(v)
        try:
            _, parsed_v = infer_languages_and_version_from_name(Path(item.input_path).name)
            return str(parsed_v or "Unknown")
        except Exception:
            return "Unknown"

    def norm_region(item: "ScanItem") -> str:
        r = getattr(item, "region", None)
        if r:
            return str(r)
        try:
            return str(infer_region_from_name(Path(item.input_path).name) or "Unknown")
        except Exception:
            return "Unknown"

    filtered: List["ScanItem"] = []
    for item in items:
        system_name = (getattr(item, "detected_system", None) or "Unknown").strip() or "Unknown"
        item_langs = norm_langs(item)
        item_ver = norm_ver(item)
        item_region = norm_region(item)

        if "All" not in system_values:
            wants_unknown_system = "Unknown" in system_values
            system_targets = {val for val in system_values if val != "Unknown"}
            if system_name == "Unknown":
                if not wants_unknown_system:
                    continue
            else:
                if system_targets and system_name not in system_targets:
                    continue
                if not system_targets and wants_unknown_system:
                    continue

        if ext_filters:
            try:
                ext = Path(item.input_path).suffix.lower()
            except Exception:
                ext = ""
            if ext not in ext_filters:
                continue

        if min_bytes is not None or max_bytes is not None:
            try:
                size = Path(item.input_path).stat().st_size
            except Exception as exc:
                logger.debug("Failed to stat input for size filter: %s", exc)
                size = None
            if size is None:
                continue
            if min_bytes is not None and size < min_bytes:
                continue
            if max_bytes is not None and size > max_bytes:
                continue

        if "All" not in lang_values:
            wants_unknown_lang = "Unknown" in lang_values
            lang_targets = {val for val in lang_values if val != "Unknown"}
            if item_langs:
                if lang_targets:
                    if not any(lang in item_langs for lang in lang_targets):
                        continue
                elif wants_unknown_lang:
                    continue
            else:
                if not wants_unknown_lang:
                    continue

        if ver != "All":
            if ver == "Unknown":
                if item_ver != "Unknown":
                    continue
            else:
                if item_ver != ver:
                    continue

        if "All" not in region_values:
            wants_unknown_region = "Unknown" in region_values
            region_targets = {val for val in region_values if val != "Unknown"}
            if item_region == "Unknown":
                if not wants_unknown_region:
                    continue
            else:
                if region_targets and item_region not in region_targets:
                    continue
                if not region_targets and wants_unknown_region:
                    continue

        filtered.append(item)

    if dedupe_variants:
        cfg = _load_cfg(config)
        try:
            prio_cfg = cfg.get("prioritization", {}) or {}
        except Exception:
            prio_cfg = {}

        try:
            region_order = prio_cfg.get("region_order")
            if isinstance(region_order, list) and region_order:
                region_priority = tuple(str(x) for x in region_order if str(x).strip()) or region_priority
        except Exception as exc:
            logger.debug("Region priority config invalid: %s", exc)

        try:
            language_order = prio_cfg.get("language_order")
            if isinstance(language_order, list) and language_order:
                language_priority = tuple(str(x) for x in language_order if str(x).strip()) or language_priority
        except Exception as exc:
            logger.debug("Language priority config invalid: %s", exc)

        return select_preferred_variants(
            filtered,
            region_priority=region_priority,
            language_priority=language_priority,
        )

    return filtered
