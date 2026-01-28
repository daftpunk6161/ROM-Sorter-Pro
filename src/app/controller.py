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

import errno
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..config import Config
from ..core.dat_index_sqlite import DatIndexSqlite
from ..core.normalization import (
    NormalizationItem,
    NormalizationPlan,
    NormalizationReport,
    execute_normalization as _execute_normalization,
    normalize_input as _normalize_input,
    plan_normalization as _plan_normalization,
)
from ..core.scan_service import run_scan as _core_run_scan
from ..detectors.dat_identifier import identify_by_hash
from ..exceptions import FileOperationError, ScannerError
from ..security.security_utils import (
    InvalidPathError,
    is_valid_directory,
    sanitize_path,
    validate_file_operation,
)
from ..utils.external_tools import build_external_command, run_wud2app, run_wudcompress
from .conversion_audit_controller import audit_conversion_candidates
from .conversion_settings import (
    _build_conversion_args,
    _is_dat_match,
    _match_conversion_rule,
    _match_conversion_rule_for_audit,
    _normalize_extension,
    _normalize_system_name,
    _resolve_conversion_settings,
    _resolve_tool_path,
)
from .dat_index_controller import build_dat_index
from .dat_sources_controller import (
    DatSourceReport,
    analyze_dat_sources,
    get_dat_sources,
    save_dat_sources,
)
from .execute_helpers import atomic_copy_with_cancel, run_conversion_with_cancel
from .identification_overrides import (
    _apply_identification_override,
    _load_identification_overrides,
)
from .library_report import build_library_report
from .models import (
    ActionStatusCallback,
    CancelToken,
    ConflictPolicy,
    ConversionAuditItem,
    ConversionAuditReport,
    ConversionMode,
    ExternalToolsReport,
    IdentificationResult,
    LogCallback,
    ProgressCallback,
    ScanItem,
    ScanResult,
    SortAction,
    SortMode,
    SortPlan,
    SortReport,
    SortResumeState,
)
from .naming_helpers import (
    infer_languages_and_version_from_name,
    infer_region_from_name,
    normalize_title_for_dedupe,
)
from .performance_helpers import (
    _get_dict,
    _load_cfg,
    _progress_batch_enabled,
    _resolve_copy_buffer_size,
)
from .resume_controller import (
    load_scan_resume,
    load_sort_resume,
    load_sort_resume_state,
    save_scan_resume,
    save_sort_resume,
)
from .scan_filtering import (
    DEFAULT_LANGUAGE_PRIORITY,
    DEFAULT_REGION_PRIORITY,
    filter_scan_items,
    select_preferred_variants,
)
from .security_helpers import has_symlink_parent
from .sorting_helpers import (
    _apply_rename_template,
    _is_confident_detection,
    _resolve_target_path,
    _safe_system_name,
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
        raise ScannerError("Source directory is empty")

    if not is_valid_directory(source_sanitized, must_exist=True):
        raise ScannerError(f"Invalid source directory: {source_sanitized}", file_path=source_sanitized)

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
        sorting_cfg = _get_dict(cfg, "features", "sorting")
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
        is_exact = bool(rom.get("is_exact") or False)
        if override is not None:
            system = str(override["platform_id"])
            detection_conf_value = float(override.get("confidence", 1.0))
            detection_source = "override"
            is_exact = True
            override_name = str(override.get("name") or "override")

        if detection_source == "extension-unique" and detection_conf_value is not None:
            if detection_conf_value < min_confidence:
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
            raw_payload["override_name"] = override_name
        if signals:
            raw_payload["signals"] = signals
        if candidates:
            raw_payload["candidates"] = candidates

        items.append(
            ScanItem(
                input_path=input_path_val,
                detected_system=system,
                detection_source=str(detection_source or ""),
                detection_confidence=detection_conf_value,
                is_exact=is_exact,
                languages=tuple(languages or ()),
                version=version,
                region=region,
                raw=raw_payload,
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
    config: Optional[Config | Dict[str, Any]] = None,
    progress_cb: Optional[ProgressCallback] = None,
    cancel_token: Optional[CancelToken] = None,
) -> List[IdentificationResult]:
    """Run DAT/Hash-first identification over scan items."""

    cfg = _load_cfg(config)
    overrides = _load_identification_overrides(cfg)

    dat_cfg = cfg.get("dats", {}) or {}
    index_path = dat_cfg.get("index_path") or os.path.join("data", "index", "romsorter_dat_index.sqlite")

    dat_index: Optional[DatIndexSqlite] = None
    try:
        if index_path and Path(str(index_path)).exists():
            dat_index = DatIndexSqlite(Path(str(index_path)))
    except Exception:
        dat_index = None

    results: List[IdentificationResult] = []
    total = len(scan_items)

    for idx, item in enumerate(scan_items, start=1):
        if cancel_token is not None and cancel_token.is_cancelled():
            break

        input_path = str(item.input_path or "")
        input_exists = bool(input_path and Path(input_path).exists())

        override = _apply_identification_override(input_path, overrides) if input_path else None
        if override is not None:
            name = str(override.get("name") or "override")
            results.append(
                IdentificationResult(
                    platform_id=str(override["platform_id"]),
                    confidence=float(override.get("confidence", 1.0)),
                    is_exact=True,
                    signals=["OVERRIDE_RULE"],
                    candidates=[str(override["platform_id"])],
                    reason=f"override:{name}",
                    input_kind="RawRom",
                )
            )
        elif dat_index and input_exists:
            match = identify_by_hash(input_path, dat_index)
            if match is not None:
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

    raw_dest = Path(dest_sanitized)
    dest_root = raw_dest.resolve()

    def _error_plan(reason: str) -> SortPlan:
        actions = [
            SortAction(
                input_path=str(item.input_path or ""),
                detected_system=item.detected_system or "Unknown",
                planned_target_path=None,
                action=mode,
                status="error",
                error=reason,
            )
            for item in scan_result.items
        ]
        return SortPlan(
            dest_path=str(dest_root),
            mode=mode,
            on_conflict=on_conflict,
            actions=actions,
        )

    if raw_dest.exists():
        try:
            if raw_dest.is_symlink():
                return _error_plan(f"Symlink destination not allowed: {raw_dest}")
            try:
                resolved = raw_dest.resolve(strict=False)
                absolute = raw_dest.absolute()
                if resolved != absolute:
                    return _error_plan(f"Symlink destination not allowed: {raw_dest}")
            except Exception:
                pass
        except Exception:
            pass

    if has_symlink_parent(dest_root):
        return _error_plan(f"Symlink destination not allowed: {dest_root}")

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
        sorting_cfg = _get_dict(cfg, "features", "sorting")
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

    last_cancel_check = time.monotonic()
    for idx, item in enumerate(items):
        if cancel_token is not None:
            if cancel_token.is_cancelled():
                break
            if idx % 100 == 0:
                now = time.monotonic()
                if (now - last_cancel_check) >= 0.1 and cancel_token.is_cancelled():
                    break
                last_cancel_check = now

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

            final_target, resolve_error = _resolve_target_path(target_file, on_conflict=on_conflict)
            if resolve_error:
                actions.append(
                    SortAction(
                        input_path=str(src),
                        detected_system=item.detected_system,
                        planned_target_path=None,
                        action=mode,
                        status="error",
                        error=resolve_error,
                    )
                )
                continue
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
            if has_symlink_parent(final_target):
                raise InvalidPathError(f"Symlink parent not allowed: {final_target}")

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

    dest_root = Path(sort_plan.dest_path).resolve()
    cfg = _load_cfg(None)
    buffer_size = _resolve_copy_buffer_size(cfg)
    batch_progress = _progress_batch_enabled(cfg)
    conversion_timeout_sec: Optional[float] = 300.0
    try:
        sorting_cfg = _get_dict(cfg, "features", "sorting")
        timeout_value = sorting_cfg.get("conversion_timeout_sec")
        if timeout_value is not None:
            conversion_timeout_sec = float(timeout_value)
    except Exception:
        conversion_timeout_sec = 300.0

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
            if has_symlink_parent(dst_raw):
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

            if is_conversion and dry_run:
                if action_status_cb is not None:
                    action_status_cb(row_index, "dry-run (convert)")

                processed += 1

                if sort_plan.mode == "copy":
                    copied += 1
                else:
                    moved += 1

                if log_cb is not None:
                    log_cb(f"[DRY-RUN] Would convert: {src.name} -> {dst}")

            elif is_conversion:
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
                            timeout_sec=conversion_timeout_sec,
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
                            timeout_sec=conversion_timeout_sec,
                        )
                        ok = result.success
                        conversion_cancelled = result.cancelled
                    else:
                        cmd = [str(action.conversion_tool)] + list(action.conversion_args or [])
                        ok, conversion_cancelled = run_conversion_with_cancel(
                            cmd,
                            cancel_token,
                            timeout_sec=conversion_timeout_sec,
                        )
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
                        ok = atomic_copy_with_cancel(
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
                                ok = atomic_copy_with_cancel(
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

        try:
            src_raw = Path(action.input_path)
            if src_raw.is_symlink():
                raise InvalidPathError(f"Symlink source not allowed: {src_raw}")
            if output_file.exists() and output_file.is_symlink():
                raise InvalidPathError(f"Symlink destination not allowed: {output_file}")
            if has_symlink_parent(output_file):
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

        src_raw = Path(action.input_path)
        if src_raw.is_symlink():
            raise InvalidPathError(f"Symlink source not allowed: {src_raw}")
        if output_file.exists() and output_file.is_symlink():
            raise InvalidPathError(f"Symlink destination not allowed: {output_file}")
        if has_symlink_parent(output_file):
            raise InvalidPathError(f"Symlink parent not allowed: {output_file}")

        src = src_raw.resolve()
        dst = output_file.resolve()

        validate_file_operation(src, base_dir=None, allow_read=True, allow_write=True)
        validate_file_operation(dst, base_dir=out_dir, allow_read=True, allow_write=True)

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
