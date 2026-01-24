"""ROM Sorter Pro - GUI-first controller APIs.

Hard goals:
- UI calls only these functions (no low-level scanner/sorter internals)
- No heavy optional dependencies are imported here
- Thread-friendly: supports cancellation + progress/log callbacks

Public API (requested MVP surface):
- run_scan(source_path, config, progress_cb, log_cb, cancel_token) -> ScanResult
- plan_sort(scan_result, dest_path, config) -> SortPlan
- execute_sort(sort_plan, progress_cb, log_cb, cancel_token) -> SortReport
"""

from __future__ import annotations

import os
import time
import json
import errno
import re
import shutil
import threading
import subprocess
import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Literal, Optional, Sequence, Set, Tuple, Union

from ..config import Config, load_config, save_config
from ..utils.external_tools import build_external_command, run_wud2app, run_wudcompress
from ..security.security_utils import (
    InvalidPathError,
    is_valid_directory,
    sanitize_path,
    validate_file_operation,
)
from ..core.normalization import (
    NormalizationItem,
    NormalizationPlan,
    NormalizationReport,
    normalize_input as _normalize_input,
    plan_normalization as _plan_normalization,
    execute_normalization as _execute_normalization,
)
from ..core.dat_index_sqlite import DatIndexSqlite, build_index_from_config
from ..detectors.dat_identifier import identify_by_hash

# Reuse existing stable core implementation for scanning.
from ..core.scan_service import run_scan as _core_run_scan

SortMode = Literal["copy", "move"]
ConflictPolicy = Literal["skip", "overwrite", "rename"]
ConversionMode = Literal["all", "skip", "only"]

ProgressCallback = Callable[[int, int], None]
LogCallback = Callable[[str], None]
ActionStatusCallback = Callable[[int, str], None]


class CancelToken:
    """Thread-safe cancellation token."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def event(self) -> threading.Event:
        return self._event


@dataclass(frozen=True)
class ScanItem:
    input_path: str
    detected_system: str
    detection_source: Optional[str] = None
    detection_confidence: Optional[float] = None
    is_exact: bool = False
    languages: Tuple[str, ...] = ()
    version: Optional[str] = None
    region: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class IdentificationResult:
    platform_id: str
    confidence: float
    is_exact: bool
    signals: List[str]
    candidates: List[str]
    reason: str
    input_kind: str
    normalized_artifact: Optional[str] = None


_LANG_TOKEN_RE = re.compile(r"\(([A-Za-z]{2}(?:\s*,\s*[A-Za-z]{2})*)\)")
_VERSION_RE = re.compile(
    r"\b(v\d+(?:\.\d+)*|rev\s*[0-9a-z]+|final|beta|alpha|demo|prototype|proto|sample)\b",
    re.IGNORECASE,
)


_REGION_PAREN_TOKEN_RE = re.compile(r"\(([^\)]*)\)")
_REGION_HINT_RE = re.compile(
    r"\b(europe|eur|pal|usa|u\.?s\.?a\.?|united\s+states|ntsc-u|japan|ntsc-j|world)\b",
    re.IGNORECASE,
)

DEFAULT_REGION_PRIORITY: Tuple[str, ...] = (
    "Europe",
    "USA",
    "World",
    "Japan",
    "Other",
    "Unknown",
)

DEFAULT_LANGUAGE_PRIORITY: Tuple[str, ...] = (
    # Pragmatic defaults for deduping language variants.
    # The first matching language wins when multiple variants exist.
    "De",
    "En",
    "Fr",
    "Es",
    "It",
    "Pt",
    "Nl",
)


def infer_languages_and_version_from_name(name: str) -> Tuple[Tuple[str, ...], Optional[str]]:
    """Infer language codes and a version tag from a ROM filename.

    Heuristic, dependency-free, intended for simple GUI filtering.
    Examples:
      - "Game (En,Fr,De) (Rev 1).zip" -> ("En","Fr","De"), "Rev 1"
      - "Title v1.1 (Proto).bin" -> (), "v1.1" (first match wins)
    """

    filename = os.path.basename(str(name or ""))

    # Languages: tokens like (En,Fr,De)
    lang_tokens: List[str] = []
    for m in _LANG_TOKEN_RE.finditer(filename):
        raw = m.group(1)
        for part in raw.split(","):
            code = part.strip()
            if len(code) != 2:
                continue
            # Normalize "EN"/"en" -> "En"
            lang_tokens.append(code[:1].upper() + code[1:].lower())

    languages = tuple(sorted(set(lang_tokens)))

    # Version: first match wins
    version: Optional[str] = None
    vm = _VERSION_RE.search(filename)
    if vm:
        token = vm.group(1)
        low = token.strip().lower()
        if low.startswith("rev"):
            # Normalize: "rev 1" / "rev1" / "Rev A" -> "Rev 1" / "Rev A"
            rest = low[3:].strip() or "?"
            version = f"Rev {rest.upper() if rest.isalpha() else rest}"
        elif low.startswith("v"):
            version = "v" + low[1:]
        elif low == "proto" or low == "prototype":
            version = "Proto"
        else:
            version = low[:1].upper() + low[1:]

    return languages, version


def infer_region_from_name(name: str) -> Optional[str]:
    """Infer a coarse region label from a ROM filename.

    Heuristic and dependency-free. Intended for deduplication and basic filtering.
    Returns one of: Europe, USA, Japan, World, Other, Unknown.
    """

    filename = os.path.basename(str(name or ""))
    if not filename:
        return "Unknown"

    # Prefer explicit parenthesis tokens first (common in No-Intro style).
    for m in _REGION_PAREN_TOKEN_RE.finditer(filename):
        token = (m.group(1) or "").strip()
        if not token:
            continue

        low = token.lower()

        # Single-letter region codes like (E)/(U)/(J)/(W)
        if len(token) == 1 and token.isalpha():
            code = token.upper()
            if code == "E":
                return "Europe"
            if code == "U":
                return "USA"
            if code == "J":
                return "Japan"
            if code == "W":
                return "World"

        # Common explicit strings
        if "europe" in low or low == "eur" or "pal" in low:
            return "Europe"
        if "usa" in low or "u.s.a" in low or "united states" in low or "ntsc-u" in low:
            return "USA"
        if "japan" in low or "ntsc-j" in low:
            return "Japan"
        if "world" in low:
            return "World"

        # Country tokens: treat as Other (still better than Unknown)
        if any(k in low for k in ("germany", "france", "italy", "spain", "uk", "australia", "korea", "brazil", "china", "asia", "canada", "russia")):
            return "Other"

    # Fallback: search whole filename for hints.
    hm = _REGION_HINT_RE.search(filename)
    if hm:
        hit = hm.group(1).lower()
        if hit in ("europe", "eur", "pal"):
            return "Europe"
        if hit in ("usa", "united states", "ntsc-u") or hit.startswith("u"):
            return "USA"
        if hit in ("japan", "ntsc-j"):
            return "Japan"
        if hit == "world":
            return "World"

    return "Unknown"


def normalize_title_for_dedupe(input_path: str) -> str:
    """Normalize a filename into a stable title key for variant deduplication."""

    try:
        stem = Path(str(input_path or "")).stem
    except Exception:
        stem = str(input_path or "")

    # Strip bracket/paren tags (regions, languages, revisions, groups, etc.)
    base = re.sub(r"\[[^\]]*\]", " ", stem)
    base = re.sub(r"\([^\)]*\)", " ", base)
    base = re.sub(r"[._-]+", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    return base


def select_preferred_variants(
    items: List[ScanItem],
    *,
    region_priority: Tuple[str, ...] = DEFAULT_REGION_PRIORITY,
    language_priority: Tuple[str, ...] = DEFAULT_LANGUAGE_PRIORITY,
) -> List[ScanItem]:
    """Dedupe multiple region variants of the same title.

    Key: (detected_system, normalized_title). For each key, keep the item whose region
    ranks highest in region_priority. Deterministic tie-break: input_path.
    """

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

    def variant_score(it: ScanItem) -> Tuple[int, int, int, int, str]:
        langs = tuple(getattr(it, "languages", ()) or ())
        # Lower is better for the tuple.
        return (
            region_rank(getattr(it, "region", None)),
            0 if langs else 1,  # prefer entries that carry language info
            best_language_rank(langs),  # then prefer best language
            -len(langs),  # then prefer more languages (more inclusive)
            str(it.input_path or ""),  # deterministic tie-break
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

    # Stable output ordering (so planning stays deterministic)
    return sorted(chosen.values(), key=lambda x: (x.input_path or ""))


def filter_scan_items(
    items: List[ScanItem],
    *,
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

    def norm_langs(item: ScanItem) -> Tuple[str, ...]:
        langs = getattr(item, "languages", ()) or ()
        if langs:
            return tuple(langs)
        try:
            parsed, _ = infer_languages_and_version_from_name(Path(item.input_path).name)
            return tuple(parsed)
        except Exception:
            return ()

    def norm_ver(item: ScanItem) -> str:
        v = getattr(item, "version", None)
        if v:
            return str(v)
        try:
            _, parsed_v = infer_languages_and_version_from_name(Path(item.input_path).name)
            return str(parsed_v or "Unknown")
        except Exception:
            return "Unknown"

    def norm_region(item: ScanItem) -> str:
        r = getattr(item, "region", None)
        if r:
            return str(r)
        try:
            return str(infer_region_from_name(Path(item.input_path).name) or "Unknown")
        except Exception:
            return "Unknown"

    filtered: List[ScanItem] = []
    for item in items:
        item_langs = norm_langs(item)
        item_ver = norm_ver(item)
        item_region = norm_region(item)

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
            except Exception:
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
        except Exception:
            pass

        try:
            language_order = prio_cfg.get("language_order")
            if isinstance(language_order, list) and language_order:
                language_priority = tuple(str(x) for x in language_order if str(x).strip()) or language_priority
        except Exception:
            pass

        return select_preferred_variants(
            filtered,
            region_priority=region_priority,
            language_priority=language_priority,
        )

    return filtered


@dataclass(frozen=True)
class ScanResult:
    source_path: str
    items: List[ScanItem]
    stats: Dict[str, Any]
    cancelled: bool = False


@dataclass(frozen=True)
class SortAction:
    input_path: str
    detected_system: str
    planned_target_path: Optional[str]
    action: str
    status: str
    error: Optional[str] = None
    conversion_tool: Optional[str] = None
    conversion_tool_key: Optional[str] = None
    conversion_args: Optional[List[str]] = None
    conversion_rule: Optional[str] = None
    conversion_output_extension: Optional[str] = None


@dataclass(frozen=True)
class SortPlan:
    dest_path: str
    mode: SortMode
    on_conflict: ConflictPolicy
    actions: List[SortAction]


@dataclass(frozen=True)
class SortResumeState:
    sort_plan: SortPlan
    resume_from_index: int


@dataclass(frozen=True)
class SortReport:
    dest_path: str
    mode: SortMode
    on_conflict: ConflictPolicy
    processed: int
    copied: int
    moved: int
    overwritten: int
    renamed: int
    skipped: int
    errors: List[str]
    cancelled: bool


@dataclass(frozen=True)
class ExternalToolsReport:
    processed: int
    succeeded: int
    failed: int
    errors: List[str]
    cancelled: bool


@dataclass(frozen=True)
class DatSourceReport:
    paths: List[str]
    existing_paths: List[str]
    missing_paths: List[str]
    dat_files: int
    dat_xml_files: int
    dat_zip_files: int


@dataclass(frozen=True)
class ConversionAuditItem:
    input_path: str
    detected_system: str
    current_extension: str
    recommended_extension: Optional[str]
    rule_name: Optional[str]
    tool_key: Optional[str]
    status: str
    reason: Optional[str] = None


@dataclass(frozen=True)
class ConversionAuditReport:
    source_path: str
    items: List[ConversionAuditItem]
    totals: Dict[str, int]
    cancelled: bool = False


def _load_cfg(config: Optional[Config]) -> Config:
    if config is not None:
        return config
    try:
        return load_config()
    except Exception:
        return Config()


def _resolve_copy_buffer_size(cfg: Config) -> int:
    size = None
    try:
        perf_cfg = cfg.get("performance", {}).get("processing", {}) or {}
        size = perf_cfg.get("io_buffer_size")
    except Exception:
        size = None
    try:
        size = int(size or 1024 * 1024)
    except Exception:
        size = 1024 * 1024
    return max(64 * 1024, min(8 * 1024 * 1024, size))


def _progress_batch_enabled(cfg: Config) -> bool:
    try:
        opt_cfg = cfg.get("performance", {}).get("optimization", {}) or {}
        return bool(opt_cfg.get("enable_progress_batching", True))
    except Exception:
        return True


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
        sorting_cfg = cfg.get("features", {}).get("sorting", {}) or {}
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
    item: ScanItem,
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
        except Exception:
            continue

    return None


def _match_conversion_rule_for_audit(
    *,
    item: ScanItem,
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
        except Exception:
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
    }

    built: List[str] = []
    for arg in args:
        value = str(arg)
        for key, replacement in replacements.items():
            value = value.replace(key, replacement)
        if value:
            built.append(value)
    return built


def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_identification_overrides(cfg: Config) -> List[Dict[str, Any]]:
    override_cfg = cfg.get("identification_overrides", {}) if isinstance(cfg, dict) else {}
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


def _safe_system_name(system: str) -> str:
    value = (system or "Unknown").strip() or "Unknown"
    safe = "".join(ch for ch in value if ch.isalnum() or ch in (" ", "-", "_", ".")).strip()
    return safe or "Unknown"


def _is_confident_detection(item: ScanItem, min_confidence: float) -> bool:
    source = str(item.detection_source or "").strip().lower()
    try:
        conf = float(item.detection_confidence or 0.0)
    except Exception:
        conf = 0.0

    if (item.detected_system or "Unknown").strip() in ("", "Unknown"):
        return False

    if not source:
        return True

    if source in ("manual", "user", "override"):
        return True

    if source.startswith("dat:"):
        return True

    if source == "extension-unique":
        return conf >= min_confidence

    return conf >= min_confidence


def _apply_rename_template(template: str, item: ScanItem, src: Path, safe_system: str) -> str:
    class _SafeDict(dict):
        def __missing__(self, key):
            return ""

    ext_dot = src.suffix
    ext = ext_dot.lstrip(".")

    canonical = None
    try:
        raw = getattr(item, "raw", None) or {}
        canonical = raw.get("canonical_name")
    except Exception:
        canonical = None

    base_name = (canonical or src.stem).strip() if isinstance(canonical, str) else src.stem

    data = _SafeDict(
        name=base_name,
        ext=ext,
        ext_dot=ext_dot,
        system=safe_system,
        region=item.region or "",
        version=item.version or "",
        languages="-".join(item.languages or ()),
    )

    rendered = template.format_map(data).strip()
    if not rendered:
        rendered = src.name

    if not rendered.lower().endswith(ext_dot.lower()) and ext_dot:
        rendered += ext_dot
    return rendered


def _resolve_target_path(target_file: Path, on_conflict: ConflictPolicy) -> Optional[Path]:
    if not target_file.exists():
        return target_file

    if on_conflict == "skip":
        return None

    if on_conflict == "overwrite":
        return target_file

    stem = target_file.stem
    suffix = target_file.suffix
    for i in range(1, 10_000):
        candidate = target_file.with_name(f"{stem} ({i}){suffix}")
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"Could not find free filename for {target_file.name}")


def _serialize_sort_plan(sort_plan: SortPlan) -> Dict[str, Any]:
    return {
        "dest_path": sort_plan.dest_path,
        "mode": sort_plan.mode,
        "on_conflict": sort_plan.on_conflict,
        "actions": [action.__dict__ for action in sort_plan.actions],
    }


def save_sort_resume(sort_plan: SortPlan, start_index: int, path: str) -> None:
    payload = _serialize_sort_plan(sort_plan)
    payload["resume_from_index"] = int(start_index)
    target = Path(path)
    validate_file_operation(target, base_dir=None, allow_read=True, allow_write=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_sort_resume(path: str) -> SortPlan:
    return load_sort_resume_state(path).sort_plan


def load_sort_resume_state(path: str) -> SortResumeState:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    actions = [SortAction(**action) for action in payload.get("actions", [])]
    resume_from_index = int(payload.get("resume_from_index") or 0)
    if resume_from_index < 0:
        resume_from_index = 0
    if resume_from_index > len(actions):
        resume_from_index = len(actions)
    plan = SortPlan(
        dest_path=payload.get("dest_path", ""),
        mode=payload.get("mode", "copy"),
        on_conflict=payload.get("on_conflict", "rename"),
        actions=actions,
    )
    return SortResumeState(sort_plan=plan, resume_from_index=resume_from_index)


def save_scan_resume(scan_result: ScanResult, path: str) -> None:
    payload = {
        "source_path": scan_result.source_path,
        "stats": scan_result.stats,
        "cancelled": scan_result.cancelled,
        "items": [item.__dict__ for item in scan_result.items],
    }
    target = Path(path)
    validate_file_operation(target, base_dir=None, allow_read=True, allow_write=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_scan_resume(path: str) -> ScanResult:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    items = [ScanItem(**item) for item in payload.get("items", [])]
    return ScanResult(
        source_path=payload.get("source_path", ""),
        items=items,
        stats=payload.get("stats", {}),
        cancelled=payload.get("cancelled", False),
    )


def run_scan(
    source_path: str,
    config: Optional[Config] = None,
    progress_cb: Optional[ProgressCallback] = None,
    log_cb: Optional[LogCallback] = None,
    cancel_token: Optional[CancelToken] = None,
) -> ScanResult:
    """Run a scan and return a structured ScanResult."""

    source_sanitized = sanitize_path(str(source_path or ""))
    if not source_sanitized:
        raise ValueError("Source directory is empty")

    if not is_valid_directory(source_sanitized, must_exist=True):
        raise ValueError(f"Invalid source directory: {source_sanitized}")

    cfg = _load_cfg(config)
    cancel_event = cancel_token.event if cancel_token is not None else None

    result = _core_run_scan(
        source_sanitized,
        config=cfg,
        on_progress=(lambda c, t: progress_cb(int(c), int(t))) if progress_cb else None,
        on_log=(lambda msg: log_cb(str(msg))) if log_cb else None,
        cancel_event=cancel_event,
    )

    items: List[ScanItem] = []
    min_confidence = 0.95
    try:
        sorting_cfg = cfg.get("features", {}).get("sorting", {}) or {}
        min_confidence = float(sorting_cfg.get("confidence_threshold", min_confidence))
    except Exception:
        min_confidence = 0.95
    overrides = _load_identification_overrides(cfg)

    for rom in list(result.get("roms") or []):
        input_path_val = str(rom.get("path") or rom.get("file") or "")
        system = str(rom.get("system") or "Unknown")
        detection_confidence = rom.get("detection_confidence")
        try:
            detection_conf_value = float(detection_confidence) if detection_confidence is not None else None
        except Exception:
            detection_conf_value = None

        detection_source = rom.get("detection_source")
        override = _apply_identification_override(input_path_val, overrides) if input_path_val else None
        override_name = None
        if override is not None:
            system = str(override["platform_id"])
            detection_conf_value = float(override["confidence"])
            detection_source = "override"
            override_name = str(override.get("name") or "override")
        if system != "Unknown":
            if detection_conf_value is None or detection_conf_value < min_confidence:
                if detection_source != "override":
                    system = "Unknown"
                    detection_source = "policy-low-confidence"

        languages: Tuple[str, ...] = ()
        version: Optional[str] = None
        region: Optional[str] = None
        if input_path_val:
            try:
                languages, version = infer_languages_and_version_from_name(Path(input_path_val).name)
            except Exception:
                languages, version = (), None
            try:
                region = infer_region_from_name(Path(input_path_val).name)
            except Exception:
                region = None

        raw_payload = dict(rom)
        signals = list(raw_payload.get("signals") or [])
        candidates = list(raw_payload.get("candidates") or [])
        if override_name:
            signals.append("OVERRIDE_RULE")
            if system and system not in candidates:
                candidates.append(system)
            raw_payload["override_rule"] = override_name
            raw_payload["override_platform"] = system
            raw_payload["reason"] = f"override:{override_name}"

        items.append(
            ScanItem(
                input_path=input_path_val,
                detected_system=system,
                detection_source=detection_source,
                detection_confidence=detection_conf_value,
                is_exact=bool(rom.get("is_exact", False)) or bool(override_name),
                languages=languages,
                version=version,
                region=region,
                raw={
                    **raw_payload,
                    "signals": signals,
                    "candidates": candidates,
                    "candidate_systems": rom.get("candidate_systems") or [],
                    "policy": "low-confidence" if detection_source == "policy-low-confidence" else None,
                    "policy_threshold": min_confidence,
                },
            )
        )

    return ScanResult(
        source_path=str(result.get("source") or source_sanitized),
        items=items,
        stats=dict(result.get("stats") or {}),
        cancelled=bool(result.get("cancelled")),
    )


def identify(
    scan_items: List[ScanItem],
    config: Optional[Config] = None,
    progress_cb: Optional[ProgressCallback] = None,
    cancel_token: Optional[CancelToken] = None,
) -> List[IdentificationResult]:
    """Run DAT/Hash-first identification over scan items."""

    cfg = _load_cfg(config)
    results: List[IdentificationResult] = []
    overrides = _load_identification_overrides(cfg)

    dat_index: Optional[DatIndexSqlite] = None
    try:
        dat_cfg = cfg.get("dats", {}) or {}
        index_path = dat_cfg.get("index_path") or os.path.join("data", "index", "romsorter_dat_index.sqlite")
        if os.path.exists(index_path):
            dat_index = DatIndexSqlite(Path(index_path))
    except Exception:
        dat_index = None

    total = len(scan_items)
    for idx, item in enumerate(scan_items, start=1):
        if cancel_token is not None and cancel_token.is_cancelled():
            break

        input_path = str(item.input_path or "")
        input_exists = bool(input_path and os.path.exists(input_path))
        override = _apply_identification_override(input_path, overrides) if input_path else None
        if override is not None:
            platform_id = str(override["platform_id"])
            name = str(override.get("name") or "override")
            confidence = float(override.get("confidence") or 1.0)
            results.append(
                IdentificationResult(
                    platform_id=platform_id,
                    confidence=confidence,
                    is_exact=True,
                    signals=["OVERRIDE_RULE"],
                    candidates=[platform_id],
                    reason=f"override:{name}",
                    input_kind="RawRom",
                    normalized_artifact=None,
                )
            )
            if progress_cb:
                progress_cb(idx, total)
            continue
        if dat_index and input_exists:
            match = identify_by_hash(input_path, dat_index)
            if match:
                results.append(
                    IdentificationResult(
                        platform_id=match.platform_id,
                        confidence=match.confidence,
                        is_exact=match.is_exact,
                        signals=list(match.signals),
                        candidates=list(match.candidates),
                        reason=match.reason,
                        input_kind=match.input_kind,
                        normalized_artifact=match.normalized_artifact,
                    )
                )
            else:
                results.append(
                    IdentificationResult(
                        platform_id="Unknown",
                        confidence=0.0,
                        is_exact=False,
                        signals=["NO_DAT_MATCH"],
                        candidates=[],
                        reason="no-dat-match",
                        input_kind="RawRom",
                    )
                )
        elif dat_index and not input_exists:
            results.append(
                IdentificationResult(
                    platform_id="Unknown",
                    confidence=0.0,
                    is_exact=False,
                    signals=["INPUT_MISSING"],
                    candidates=[],
                    reason="input-missing",
                    input_kind="RawRom",
                )
            )
        else:
            results.append(
                IdentificationResult(
                    platform_id="Unknown",
                    confidence=0.0,
                    is_exact=False,
                    signals=["NO_INDEX"],
                    candidates=[],
                    reason="index-missing",
                    input_kind="RawRom",
                )
            )

        if progress_cb:
            progress_cb(idx, total)

    if dat_index:
        dat_index.close()

    return results


def build_dat_index(
    config: Optional[Config] = None,
    cancel_token: Optional[CancelToken] = None,
) -> Dict[str, int]:
    cancel_event = cancel_token.event if cancel_token is not None else None
    return build_index_from_config(config=config, cancel_event=cancel_event)


def _normalize_dat_sources(paths: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for raw in paths:
        value = str(raw or "").strip()
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def get_dat_sources(config: Optional[Config] = None) -> List[str]:
    cfg = _load_cfg(config)
    dat_cfg = cfg.get("dats", {}) or {}
    paths = dat_cfg.get("import_paths") or []
    if isinstance(paths, str):
        paths = [p.strip() for p in paths.split(";") if p.strip()]
    return _normalize_dat_sources(paths)


def save_dat_sources(paths: Iterable[str], config: Optional[Config] = None) -> List[str]:
    cfg = _load_cfg(config)
    dat_cfg = cfg.get("dats", {}) or {}
    normalized = _normalize_dat_sources(paths)
    dat_cfg["import_paths"] = normalized
    cfg["dats"] = dat_cfg
    save_config(cfg)
    return normalized


def analyze_dat_sources(paths: Iterable[str]) -> DatSourceReport:
    normalized = _normalize_dat_sources(paths)
    existing: List[str] = []
    missing: List[str] = []
    dat_files = 0
    dat_xml_files = 0
    dat_zip_files = 0

    for raw in normalized:
        path = Path(raw)
        if not path.exists():
            missing.append(raw)
            continue
        existing.append(raw)
        if path.is_dir():
            dat_files += sum(1 for _ in path.rglob("*.dat"))
            dat_xml_files += sum(1 for _ in path.rglob("*.xml"))
            dat_zip_files += sum(1 for _ in path.rglob("*.zip"))
        else:
            suffix = path.suffix.lower()
            if suffix == ".dat":
                dat_files += 1
            elif suffix == ".xml":
                dat_xml_files += 1
            elif suffix == ".zip":
                dat_zip_files += 1

    return DatSourceReport(
        paths=normalized,
        existing_paths=existing,
        missing_paths=missing,
        dat_files=dat_files,
        dat_xml_files=dat_xml_files,
        dat_zip_files=dat_zip_files,
    )


def audit_conversion_candidates(
    source_path: str,
    config: Optional[Config] = None,
    progress_cb: Optional[ProgressCallback] = None,
    log_cb: Optional[LogCallback] = None,
    cancel_token: Optional[CancelToken] = None,
    include_disabled: bool = True,
) -> ConversionAuditReport:
    """Audit a folder for conversion candidates based on configured rules."""

    scan = run_scan(
        source_path,
        config=config,
        progress_cb=None,
        log_cb=log_cb,
        cancel_token=cancel_token,
    )

    cfg = _load_cfg(config)
    conversion_settings = _resolve_conversion_settings(cfg)

    items: List[ConversionAuditItem] = []
    cancelled = False

    total = len(scan.items)
    for idx, item in enumerate(scan.items, start=1):
        if cancel_token is not None and cancel_token.is_cancelled():
            cancelled = True
            break

        input_path = str(item.input_path or "")
        detected_system = str(item.detected_system or "Unknown")

        try:
            src = Path(input_path).resolve()
            current_ext = _normalize_extension(src.suffix)
        except Exception:
            current_ext = ""

        audit = None
        if input_path:
            try:
                audit = _match_conversion_rule_for_audit(
                    item=item,
                    src=Path(input_path),
                    conversion_settings=conversion_settings,
                    include_disabled=include_disabled,
                )
            except Exception:
                audit = None

        status = "no_rule"
        reason = None
        recommended_ext = None
        rule_name = None
        tool_key = None

        if audit:
            recommended_ext = audit.get("to_extension")
            rule_name = audit.get("rule_name")
            tool_key = audit.get("tool_key")
            if audit.get("require_dat") and not audit.get("dat_match"):
                status = "dat_required"
                reason = "Requires DAT match"
            elif audit.get("missing_tool"):
                status = "missing_tool"
                reason = "Tool not available"
            elif not audit.get("enabled", True):
                status = "disabled_rule"
                reason = "Rule disabled"
            else:
                if recommended_ext and current_ext and current_ext == recommended_ext:
                    status = "optimal"
                else:
                    status = "should_convert"

        items.append(
            ConversionAuditItem(
                input_path=input_path,
                detected_system=detected_system,
                current_extension=current_ext or "",
                recommended_extension=recommended_ext,
                rule_name=rule_name,
                tool_key=tool_key,
                status=status,
                reason=reason,
            )
        )

        if progress_cb is not None:
            progress_cb(idx, total)

    totals: Dict[str, int] = {}
    for item in items:
        totals[item.status] = totals.get(item.status, 0) + 1

    return ConversionAuditReport(
        source_path=scan.source_path,
        items=items,
        totals=totals,
        cancelled=cancelled,
    )


def plan_sort(
    scan_result: ScanResult,
    dest_path: str,
    config: Optional[Config] = None,
    mode: SortMode = "copy",
    on_conflict: ConflictPolicy = "rename",
    cancel_token: Optional[CancelToken] = None,
) -> SortPlan:
    """Create a deterministic SortPlan without writing to disk."""

    if mode not in ("copy", "move"):
        raise ValueError(f"Invalid mode: {mode!r}")
    if on_conflict not in ("skip", "overwrite", "rename"):
        raise ValueError(f"Invalid on_conflict: {on_conflict!r}")

    dest_sanitized = sanitize_path(str(dest_path or ""))
    if not dest_sanitized:
        raise ValueError("Destination directory is empty")

    dest_root = Path(dest_sanitized).resolve()

    # Destination may not exist yet for planning; validate shape only.
    if dest_root.exists() and not dest_root.is_dir():
        raise ValueError(f"Destination is not a directory: {dest_sanitized}")

    cfg = _load_cfg(config)

    rename_template = None
    create_unknown_folder = True
    unknown_folder_name = "Unknown"
    quarantine_unknown = False
    quarantine_folder_name = "Quarantine"
    min_confidence = 0.95
    console_sorting_enabled = True
    create_console_folders = True
    region_based_sorting = False
    preserve_folder_structure = False
    conversion_settings: Dict[str, Any] = {
        "enabled": False,
        "require_dat": True,
        "fallback_on_missing": True,
        "tools": {},
        "rules": [],
    }
    try:
        sorting_cfg = cfg.get("features", {}).get("sorting", {}) or {}
        rename_template = sorting_cfg.get("rename_template")
        create_unknown_folder = bool(sorting_cfg.get("create_unknown_folder", True))
        unknown_folder_name = str(sorting_cfg.get("unknown_folder_name") or "Unknown")
        quarantine_unknown = bool(sorting_cfg.get("quarantine_unknown", False))
        quarantine_folder_name = str(sorting_cfg.get("quarantine_folder_name") or "Quarantine")
        min_confidence = float(sorting_cfg.get("confidence_threshold", 0.95))
        console_sorting_enabled = bool(sorting_cfg.get("console_sorting_enabled", True))
        create_console_folders = bool(sorting_cfg.get("create_console_folders", True))
        region_based_sorting = bool(sorting_cfg.get("region_based_sorting", False))
        preserve_folder_structure = bool(sorting_cfg.get("preserve_folder_structure", False))
        conversion_settings = _resolve_conversion_settings(cfg)
    except Exception:
        rename_template = None

    actions: List[SortAction] = []

    # Determinism: sort by input path.
    items = sorted(scan_result.items, key=lambda it: (it.input_path or ""))

    for item in items:
        if cancel_token is not None and cancel_token.is_cancelled():
            break

        if not item.input_path:
            actions.append(
                SortAction(
                    input_path="",
                    detected_system=item.detected_system or "Unknown",
                    planned_target_path=None,
                    action=mode,
                    status="error",
                    error="Missing input path",
                )
            )
            continue

        try:
            src = Path(item.input_path).resolve()
            validate_file_operation(src, base_dir=None, allow_read=True, allow_write=True)

            if _is_confident_detection(item, min_confidence):
                safe_system = _safe_system_name(item.detected_system)
            else:
                if not create_unknown_folder and not quarantine_unknown:
                    actions.append(
                        SortAction(
                            input_path=str(src),
                            detected_system=item.detected_system or "Unknown",
                            planned_target_path=None,
                            action=mode,
                            status="skipped",
                            error="Unknown or low-confidence detection",
                        )
                    )
                    continue
                if quarantine_unknown:
                    safe_system = _safe_system_name(quarantine_folder_name)
                else:
                    safe_system = _safe_system_name(unknown_folder_name)

            target_dir = dest_root
            if console_sorting_enabled and create_console_folders:
                target_dir = target_dir / safe_system

            if region_based_sorting:
                region_value = item.region
                if not region_value or str(region_value) == "Unknown":
                    try:
                        region_value = infer_region_from_name(src.name)
                    except Exception:
                        region_value = None
                if region_value and str(region_value) != "Unknown":
                    target_dir = target_dir / _safe_system_name(str(region_value))

            if preserve_folder_structure:
                try:
                    rel = src.parent.relative_to(Path(scan_result.source_path).resolve())
                    if str(rel) not in (".", ""):
                        target_dir = target_dir / rel
                except Exception:
                    pass
            target_name = src.name
            if isinstance(rename_template, str) and rename_template.strip():
                target_name = _apply_rename_template(rename_template, item, src, safe_system)

            conversion_meta = None
            if conversion_settings.get("enabled"):
                conversion_meta = _match_conversion_rule(
                    item=item,
                    src=src,
                    conversion_settings=conversion_settings,
                )
                if conversion_meta and conversion_meta.get("missing_tool"):
                    if conversion_settings.get("fallback_on_missing", True):
                        conversion_meta = None
                    else:
                        actions.append(
                            SortAction(
                                input_path=str(src),
                                detected_system=item.detected_system,
                                planned_target_path=None,
                                action="convert",
                                status="skipped",
                                error="Conversion tool not available",
                            )
                        )
                        continue

            if conversion_meta and conversion_meta.get("to_extension"):
                target_name = Path(target_name).with_suffix(conversion_meta["to_extension"]).name

            target_file = target_dir / target_name

            final_target = _resolve_target_path(target_file, on_conflict=on_conflict)
            if final_target is None:
                actions.append(
                    SortAction(
                        input_path=str(src),
                        detected_system=item.detected_system,
                        planned_target_path=None,
                        action=mode,
                        status="skipped",
                        error="Target exists (skip)",
                    )
                )
                continue

            # Validate planned destination path stays within destination root.
            validate_file_operation(final_target, base_dir=dest_root, allow_read=True, allow_write=True)

            action_value = mode
            status = "planned"
            if conversion_meta:
                action_value = "convert"
                status = "planned (convert)"
            if final_target != target_file:
                status = "planned (convert, rename)" if conversion_meta else "planned (rename)"

            conversion_args = None
            conversion_tool = None
            conversion_tool_key = None
            conversion_rule_name = None
            conversion_output_extension = None
            if conversion_meta:
                conversion_tool = conversion_meta.get("tool")
                conversion_tool_key = conversion_meta.get("tool_key")
                conversion_rule = conversion_meta.get("rule") or {}
                conversion_args = _build_conversion_args(conversion_rule, src, final_target)
                conversion_rule_name = str(conversion_rule.get("name") or "") or None
                conversion_output_extension = conversion_meta.get("to_extension")

            actions.append(
                SortAction(
                    input_path=str(src),
                    detected_system=item.detected_system,
                    planned_target_path=str(final_target),
                    action=action_value,
                    status=status,
                    conversion_tool=conversion_tool,
                    conversion_tool_key=conversion_tool_key,
                    conversion_args=conversion_args,
                    conversion_rule=conversion_rule_name,
                    conversion_output_extension=conversion_output_extension,
                )
            )

        except Exception as exc:
            actions.append(
                SortAction(
                    input_path=str(item.input_path),
                    detected_system=item.detected_system,
                    planned_target_path=None,
                    action=mode,
                    status="error",
                    error=str(exc),
                )
            )

    return SortPlan(
        dest_path=str(dest_root),
        mode=mode,
        on_conflict=on_conflict,
        actions=actions,
    )


def plan_rebuild(
    scan_result: ScanResult,
    dest_path: str,
    config: Optional[Config] = None,
    cancel_token: Optional[CancelToken] = None,
) -> SortPlan:
    """Create a copy-only rebuild plan (skip conflicts, no destructive moves)."""

    return plan_sort(
        scan_result=scan_result,
        dest_path=dest_path,
        config=config,
        mode="copy",
        on_conflict="skip",
        cancel_token=cancel_token,
    )


def execute_sort(
    sort_plan: SortPlan,
    progress_cb: Optional[ProgressCallback] = None,
    log_cb: Optional[LogCallback] = None,
    action_status_cb: Optional[ActionStatusCallback] = None,
    cancel_token: Optional[CancelToken] = None,
    dry_run: bool = False,
    resume_path: Optional[str] = None,
    start_index: int = 0,
    only_indices: Optional[List[int]] = None,
    conversion_mode: ConversionMode = "all",
) -> SortReport:
    """Execute a previously computed SortPlan (or simulate it with dry_run=True)."""

    def _atomic_copy_with_cancel(
        src: Path,
        dst: Path,
        *,
        allow_replace: bool,
        cancel_token: Optional[CancelToken],
        buffer_size: int = 1024 * 1024,
    ) -> bool:
        """Copy src -> dst atomically with cancellation support.

        Writes into a temporary file in the destination directory and replaces dst on success.
        Returns False if cancelled (and guarantees no partial dst is left behind).
        """

        if cancel_token is not None and cancel_token.is_cancelled():
            return False

        if dst.exists() and not allow_replace:
            raise FileExistsError(str(dst))

        tmp = dst.with_name(dst.name + ".part")

        try:
            if tmp.exists():
                try:
                    tmp.unlink()
                except Exception:
                    os.remove(str(tmp))

            cancelled_midway = False

            with open(src, "rb") as fsrc, open(tmp, "wb") as fdst:
                while True:
                    if cancel_token is not None and cancel_token.is_cancelled():
                        cancelled_midway = True
                        break

                    chunk = fsrc.read(buffer_size)
                    if not chunk:
                        break
                    fdst.write(chunk)

                if not cancelled_midway:
                    try:
                        fdst.flush()
                        os.fsync(fdst.fileno())
                    except Exception:
                        # Best-effort only; not all platforms/fs support fsync.
                        pass

            if cancelled_midway or (cancel_token is not None and cancel_token.is_cancelled()):
                try:
                    tmp.unlink()
                except Exception:
                    try:
                        os.remove(str(tmp))
                    except Exception:
                        pass
                return False

            os.replace(str(tmp), str(dst))

            try:
                shutil.copystat(src, dst, follow_symlinks=True)
            except Exception:
                pass

            return True

        except Exception:
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                try:
                    os.remove(str(tmp))
                except Exception:
                    pass
            raise

    def _run_conversion_with_cancel(
        cmd: List[str],
        cancel_token: Optional[CancelToken],
    ) -> Tuple[bool, bool]:
        if cancel_token is not None and cancel_token.is_cancelled():
            return False, True

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            return False, False

        while True:
            if cancel_token is not None and cancel_token.is_cancelled():
                try:
                    process.terminate()
                except Exception:
                    pass
                try:
                    process.wait(timeout=2)
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass
                return False, True

            code = process.poll()
            if code is not None:
                return code == 0, False
            time.sleep(0.1)

    dest_root = Path(sort_plan.dest_path).resolve()
    cfg = _load_cfg(None)
    buffer_size = _resolve_copy_buffer_size(cfg)
    batch_progress = _progress_batch_enabled(cfg)

    errors: List[str] = []
    processed = 0
    copied = 0
    moved = 0
    overwritten = 0
    renamed = 0
    skipped = 0
    cancelled = False

    total_actions = len(sort_plan.actions)

    if only_indices:
        requested = [int(idx) for idx in only_indices]
        filtered = [idx for idx in sorted(set(requested)) if 0 <= idx < total_actions]
        actions_to_run = [(idx, sort_plan.actions[idx]) for idx in filtered]
    else:
        safe_start = max(0, int(start_index))
        safe_start = min(safe_start, total_actions)
        actions_to_run = list(enumerate(sort_plan.actions[safe_start:], start=safe_start))

    if conversion_mode != "all":
        filtered_actions: List[Tuple[int, SortAction]] = []
        for idx, action in actions_to_run:
            is_convert = action.action == "convert"
            if conversion_mode == "skip" and is_convert:
                continue
            if conversion_mode == "only" and not is_convert:
                continue
            filtered_actions.append((idx, action))
        actions_to_run = filtered_actions

    total = len(actions_to_run)

    cancel_start_row: Optional[int] = None
    remaining_rows: Optional[List[int]] = None

    if log_cb is not None:
        log_cb(
            f"Starting execute_sort into: {dest_root} (dry_run={dry_run}, mode={sort_plan.mode}, on_conflict={sort_plan.on_conflict})"
        )

    def _has_symlink_parent(path: Path) -> bool:
        for parent in path.parents:
            try:
                if parent.exists() and parent.is_symlink():
                    return True
            except Exception:
                continue
        return False

    progress_every = max(1, total // 100) if batch_progress and total > 0 else 1
    last_progress_ts = 0.0

    for step, (row_index, action) in enumerate(actions_to_run, start=1):
        if cancel_token is not None and cancel_token.is_cancelled():
            cancelled = True
            cancel_start_row = row_index
            remaining_rows = [row for row, _action in actions_to_run[step - 1 :]]
            if log_cb is not None:
                log_cb("Cancellation requested. Stopping sort…")
            break

        if action.status.startswith("skipped") or action.planned_target_path is None:
            skipped += 1
            processed += 1
            if action_status_cb is not None:
                action_status_cb(row_index, "skipped")
            if progress_cb is not None:
                if not batch_progress or step == total or step % progress_every == 0:
                    now = time.time()
                    if (now - last_progress_ts) >= 0.05 or step == total:
                        last_progress_ts = now
                        progress_cb(step, total)
            continue

        try:
            src_raw = Path(action.input_path)
            if src_raw.is_symlink():
                raise InvalidPathError(f"Symlink source not allowed: {src_raw}")

            dst_raw = Path(action.planned_target_path)
            if dst_raw.exists() and dst_raw.is_symlink():
                raise InvalidPathError(f"Symlink destination not allowed: {dst_raw}")
            if _has_symlink_parent(dst_raw):
                raise InvalidPathError(f"Symlink parent not allowed: {dst_raw}")

            src = src_raw.resolve()
            dst = dst_raw.resolve()

            validate_file_operation(src, base_dir=None, allow_read=True, allow_write=True)
            validate_file_operation(dst, base_dir=dest_root, allow_read=True, allow_write=True)

            # Track rename heuristically: planned target name differs from source name.
            if dst.name != src.name:
                renamed += 1

            is_conversion = (
                action.action == "convert"
                and action.conversion_tool
                and action.conversion_args is not None
            )

            if action_status_cb is not None:
                action_status_cb(row_index, "converting…" if is_conversion else f"{sort_plan.mode}ing…")

            if is_conversion:
                if not dry_run:
                    dst.parent.mkdir(parents=True, exist_ok=True)

                    allow_replace = sort_plan.on_conflict == "overwrite"

                    if allow_replace and dst.exists():
                        overwritten += 1
                        try:
                            dst.unlink()
                        except Exception:
                            os.remove(str(dst))

                    tool_key = str(action.conversion_tool_key or "").lower()
                    if tool_key == "wud2app":
                        temp_dir = dst.parent / "_temp"
                        temp_dir.mkdir(parents=True, exist_ok=True)
                        result = run_wud2app(
                            input_path=str(src),
                            output_dir=str(dst.parent),
                            temp_dir=str(temp_dir),
                            log_cb=log_cb,
                            cancel_token=cancel_token,
                            dry_run=False,
                        )
                        ok = result.success
                        conversion_cancelled = result.cancelled
                    elif tool_key == "wudcompress":
                        temp_dir = dst.parent / "_temp"
                        temp_dir.mkdir(parents=True, exist_ok=True)
                        result = run_wudcompress(
                            input_path=str(src),
                            output_file=str(dst),
                            output_dir=str(dst.parent),
                            temp_dir=str(temp_dir),
                            log_cb=log_cb,
                            cancel_token=cancel_token,
                            dry_run=False,
                        )
                        ok = result.success
                        conversion_cancelled = result.cancelled
                    else:
                        cmd = [str(action.conversion_tool)] + list(action.conversion_args or [])
                        ok, conversion_cancelled = _run_conversion_with_cancel(cmd, cancel_token)
                    if conversion_cancelled:
                        cancelled = True
                        cancel_start_row = row_index
                        remaining_rows = [row for row, _action in actions_to_run[step:]]
                        if action_status_cb is not None:
                            action_status_cb(row_index, "cancelled")
                        if log_cb is not None:
                            log_cb("Cancelled during conversion.")
                        try:
                            if dst.exists():
                                dst.unlink()
                        except Exception:
                            pass
                        break
                    if not ok:
                        raise RuntimeError(f"Conversion failed for {src.name}")

                    if not dst.exists():
                        raise RuntimeError(
                            f"Conversion reported success but output missing: {dst}"
                        )

                    if sort_plan.mode == "move":
                        try:
                            src.unlink()
                        except Exception:
                            os.remove(str(src))

                if sort_plan.mode == "copy":
                    copied += 1
                else:
                    moved += 1

                processed += 1

                if action_status_cb is not None:
                    action_status_cb(row_index, "converted")

                if log_cb is not None:
                    verb = "Would convert" if dry_run else "Convert"
                    log_cb(f"{verb}: {src.name} -> {dst}")

            else:
                if not dry_run:
                    dst.parent.mkdir(parents=True, exist_ok=True)

                    allow_replace = sort_plan.on_conflict == "overwrite"

                    # Overwrite policy: remove existing file first.
                    if allow_replace and dst.exists():
                        overwritten += 1
                        try:
                            dst.unlink()
                        except Exception:
                            os.remove(str(dst))

                    if sort_plan.mode == "copy":
                        ok = _atomic_copy_with_cancel(
                            src,
                            dst,
                            allow_replace=allow_replace,
                            cancel_token=cancel_token,
                            buffer_size=buffer_size,
                        )
                        if not ok:
                            cancelled = True
                            cancel_start_row = row_index
                            remaining_rows = [row for row, _action in actions_to_run[step:]]
                            if action_status_cb is not None:
                                action_status_cb(row_index, "cancelled")
                            if log_cb is not None:
                                log_cb("Cancelled during copy; cleaned up partial file.")
                            break
                    else:
                        # Prefer fast rename when possible; fallback to cancellable copy+delete.
                        try:
                            if cancel_token is not None and cancel_token.is_cancelled():
                                cancelled = True
                                cancel_start_row = row_index
                                remaining_rows = [row for row, _action in actions_to_run[step:]]
                                if action_status_cb is not None:
                                    action_status_cb(row_index, "cancelled")
                                break

                            if dst.exists() and not allow_replace:
                                raise FileExistsError(str(dst))

                            os.replace(str(src), str(dst))

                        except OSError as move_exc:
                            winerr = getattr(move_exc, "winerror", None)
                            if move_exc.errno in (errno.EXDEV,) or winerr in (17,):
                                ok = _atomic_copy_with_cancel(
                                    src,
                                    dst,
                                    allow_replace=allow_replace,
                                    cancel_token=cancel_token,
                                    buffer_size=buffer_size,
                                )
                                if not ok:
                                    cancelled = True
                                    cancel_start_row = row_index
                                    remaining_rows = [row for row, _action in actions_to_run[step:]]
                                    if action_status_cb is not None:
                                        action_status_cb(row_index, "cancelled")
                                    if log_cb is not None:
                                        log_cb("Cancelled during move; cleaned up partial file.")
                                    break

                                try:
                                    src.unlink()
                                except Exception:
                                    os.remove(str(src))
                            else:
                                raise

                if sort_plan.mode == "copy":
                    copied += 1
                    if action_status_cb is not None:
                        action_status_cb(row_index, "copied")
                else:
                    moved += 1
                    if action_status_cb is not None:
                        action_status_cb(row_index, "moved")

                processed += 1

                if log_cb is not None:
                    verb = "Would copy" if dry_run and sort_plan.mode == "copy" else "Copy"
                    if sort_plan.mode == "move":
                        verb = "Would move" if dry_run else "Move"
                    log_cb(f"{verb}: {src.name} -> {dst}")

        except InvalidPathError as exc:
            processed += 1
            msg = f"Error sorting {action.input_path}: {exc}"
            errors.append(msg)
            if action_status_cb is not None:
                action_status_cb(row_index, f"error: {exc}")
            if log_cb is not None:
                log_cb(msg)
            raise
        except Exception as exc:
            processed += 1
            msg = f"Error sorting {action.input_path}: {exc}"
            errors.append(msg)
            if action_status_cb is not None:
                action_status_cb(row_index, f"error: {exc}")
            if log_cb is not None:
                log_cb(msg)

        if progress_cb is not None:
            if not batch_progress or step == total or step % progress_every == 0:
                now = time.time()
                if (now - last_progress_ts) >= 0.05 or step == total:
                    last_progress_ts = now
                    progress_cb(step, total)

    if cancelled and resume_path and cancel_start_row is not None and only_indices is None:
        try:
            save_sort_resume(sort_plan, cancel_start_row, resume_path)
            if log_cb is not None:
                log_cb(f"Resume state saved: {resume_path}")
        except Exception as exc:
            if log_cb is not None:
                log_cb(f"Failed to save resume state: {exc}")

    if cancelled and action_status_cb is not None and cancel_start_row is not None:
        rows_to_mark = remaining_rows
        if rows_to_mark is None and only_indices is None:
            rows_to_mark = list(range(cancel_start_row, total_actions))
        if rows_to_mark:
            for row in rows_to_mark:
                try:
                    action_status_cb(row, "not executed (cancelled)")
                except Exception:
                    break

    if log_cb is not None:
        log_cb(
            f"Sort finished. Copied: {copied}, Moved: {moved}, Skipped: {skipped}, Errors: {len(errors)}, Cancelled: {cancelled}"
        )

    return SortReport(
        dest_path=str(dest_root),
        mode=sort_plan.mode,
        on_conflict=sort_plan.on_conflict,
        processed=processed,
        copied=copied,
        moved=moved,
        overwritten=overwritten,
        renamed=renamed,
        skipped=skipped,
        errors=errors,
        cancelled=cancelled,
    )


def build_external_tools_commands(
    sort_plan: SortPlan,
    output_dir: Optional[str],
    temp_dir: Optional[str],
    config: Optional[Config] = None,
) -> List[str]:
    cfg = _load_cfg(config)
    out_dir = Path(output_dir or sort_plan.dest_path).resolve()
    tmp_dir = Path(temp_dir or (out_dir / "_temp")).resolve()

    commands: List[str] = []

    for action in sort_plan.actions:
        tool_key = str(action.conversion_tool_key or "").lower().strip()
        if action.action != "convert" or not tool_key:
            continue
        if tool_key not in ("wud2app", "wudcompress"):
            continue
        if not action.input_path or not action.planned_target_path:
            commands.append(f"[{tool_key}] ERROR: missing input or target path")
            continue

        output_file = out_dir / Path(action.planned_target_path).name

        def _has_symlink_parent(path: Path) -> bool:
            for parent in path.parents:
                try:
                    if parent.exists() and parent.is_symlink():
                        return True
                except Exception:
                    continue
            return False

        try:
            src_raw = Path(action.input_path)
            if src_raw.is_symlink():
                raise InvalidPathError(f"Symlink source not allowed: {src_raw}")
            if output_file.exists() and output_file.is_symlink():
                raise InvalidPathError(f"Symlink destination not allowed: {output_file}")
            if _has_symlink_parent(output_file):
                raise InvalidPathError(f"Symlink parent not allowed: {output_file}")

            src = src_raw.resolve()
            dst = output_file.resolve()

            validate_file_operation(src, base_dir=None, allow_read=True, allow_write=True)
            validate_file_operation(dst, base_dir=out_dir, allow_read=True, allow_write=True)
        except InvalidPathError as exc:
            commands.append(f"[{tool_key}] ERROR: {exc}")
            continue
        cmd, err = build_external_command(
            tool_key=tool_key,
            input_path=str(action.input_path),
            output_file=str(output_file),
            output_dir=str(out_dir),
            temp_dir=str(tmp_dir),
            config=cfg,
        )
        if err:
            commands.append(f"[{tool_key}] ERROR: {err}")
        else:
            commands.append(str(cmd))

    return commands


def execute_external_tools(
    sort_plan: SortPlan,
    output_dir: Optional[str],
    temp_dir: Optional[str],
    config: Optional[Config] = None,
    progress_cb: Optional[ProgressCallback] = None,
    log_cb: Optional[LogCallback] = None,
    action_status_cb: Optional[ActionStatusCallback] = None,
    cancel_token: Optional[CancelToken] = None,
    dry_run: bool = False,
    timeout_sec: Optional[float] = None,
) -> ExternalToolsReport:
    cfg = _load_cfg(config)
    out_dir = Path(output_dir or sort_plan.dest_path).resolve()
    tmp_dir = Path(temp_dir or (out_dir / "_temp")).resolve()

    if log_cb is not None:
        log_cb(f"Starting external tools queue into: {out_dir} (dry_run={dry_run})")

    actions = [
        (idx, action)
        for idx, action in enumerate(sort_plan.actions)
        if action.action == "convert" and str(action.conversion_tool_key or "").lower().strip() in ("wud2app", "wudcompress")
    ]

    total = len(actions)
    processed = 0
    succeeded = 0
    failed = 0
    errors: List[str] = []
    cancelled = False

    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir.mkdir(parents=True, exist_ok=True)

    def _has_symlink_parent(path: Path) -> bool:
        for parent in path.parents:
            try:
                if parent.exists() and parent.is_symlink():
                    return True
            except Exception:
                continue
        return False

    for step, (row_index, action) in enumerate(actions, start=1):
        if cancel_token is not None and cancel_token.is_cancelled():
            cancelled = True
            if log_cb is not None:
                log_cb("Cancellation requested. Stopping external tools queue…")
            break

        tool_key = str(action.conversion_tool_key or "").lower().strip()
        if not action.input_path or not action.planned_target_path:
            failed += 1
            processed += 1
            msg = f"[{tool_key}] Missing input or target path"
            errors.append(msg)
            if action_status_cb is not None:
                action_status_cb(row_index, f"error: {msg}")
            continue

        output_file = out_dir / Path(action.planned_target_path).name

        if action_status_cb is not None:
            action_status_cb(row_index, "converting (external)…")

        if tool_key == "wud2app":
            result = run_wud2app(
                input_path=str(action.input_path),
                output_dir=str(out_dir),
                temp_dir=str(tmp_dir),
                config=cfg,
                log_cb=log_cb,
                cancel_token=cancel_token,
                dry_run=dry_run,
                timeout_sec=timeout_sec,
            )
            ok = result.success
            cancelled = cancelled or result.cancelled
            message = result.message
        else:
            result = run_wudcompress(
                input_path=str(action.input_path),
                output_file=str(output_file),
                output_dir=str(out_dir),
                temp_dir=str(tmp_dir),
                config=cfg,
                log_cb=log_cb,
                cancel_token=cancel_token,
                dry_run=dry_run,
                timeout_sec=timeout_sec,
            )
            ok = result.success
            cancelled = cancelled or result.cancelled
            message = result.message

        if cancelled:
            if action_status_cb is not None:
                action_status_cb(row_index, "cancelled")
            break

        if ok:
            succeeded += 1
            if action_status_cb is not None:
                action_status_cb(row_index, "converted (external)")
        else:
            failed += 1
            msg = f"[{tool_key}] {message}"
            errors.append(msg)
            if action_status_cb is not None:
                action_status_cb(row_index, f"error: {message}")

        processed += 1
        if progress_cb is not None:
            progress_cb(step, total)

    return ExternalToolsReport(
        processed=processed,
        succeeded=succeeded,
        failed=failed,
        errors=errors,
        cancelled=cancelled,
    )


def normalize_input(
    input_path: str,
    *,
    platform_hint: Optional[str] = None,
) -> NormalizationItem:
    """Classify and validate a single input path for normalization."""

    return _normalize_input(input_path, platform_hint=platform_hint)


def plan_normalization(
    items: Iterable[NormalizationItem],
    *,
    output_root: Optional[str] = None,
    temp_root: Optional[str] = None,
) -> NormalizationPlan:
    """Build a conversion plan based on config-driven converters."""

    return _plan_normalization(items, output_root=output_root, temp_root=temp_root)


def execute_normalization(
    plan: NormalizationPlan,
    *,
    cancel_token: Optional[CancelToken] = None,
    dry_run: bool = True,
) -> NormalizationReport:
    """Execute a normalization plan (converters only)."""

    return _execute_normalization(plan, cancel_token=cancel_token, dry_run=dry_run)
