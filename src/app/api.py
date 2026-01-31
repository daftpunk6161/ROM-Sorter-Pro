"""Public controller API surface for UI and integrations.

Centralizes stable imports to keep UI decoupled from controller internals.
"""

from __future__ import annotations

from ..core.normalization import NormalizationItem, NormalizationPlan, NormalizationReport, NormalizationResultItem
from .controller import add_identification_override, add_identification_overrides_bulk, analyze_dat_sources, build_dat_index, build_library_report, get_symlink_warnings
from .controller import diff_sort_plans
from .controller import filter_scan_items
from .controller import get_dat_sources, infer_languages_and_version_from_name, infer_region_from_name
from .controller import load_sort_resume_state, save_dat_sources
from .database_export import export_scan_to_database
from .rollback_controller import apply_rollback, load_rollback_manifest, RollbackReport
from .conversion_controller import (
    audit_conversion_candidates,
    execute_normalization,
    normalize_input,
    plan_normalization,
)
from .async_api import async_execute_sort, async_plan_sort, async_run_scan
from .progress_streams import (
    ProgressEvent,
    run_scan_stream,
    plan_sort_stream,
    execute_sort_stream,
)
from .dat_sources_controller import DatSourceReport
from .models import (
    ActionStatusCallback,
    CancelToken,
    ConflictPolicy,
    ConversionAuditReport,
    ConversionMode,
    IdentificationResult,
    LogCallback,
    ProgressCallback,
    ScanItem,
    ScanResult,
    SortMode,
    SortPlan,
    SortReport,
)
from ..utils.result import Err, Ok, Result, is_err, is_ok, unwrap, unwrap_or
from .scan_controller import identify, run_scan
from .controller import suggest_identification_overrides
from .sort_controller import execute_sort, plan_rebuild, plan_sort

__all__ = [
    "ActionStatusCallback",
    "CancelToken",
    "ConflictPolicy",
    "ConversionAuditReport",
    "ConversionMode",
    "DatSourceReport",
    "LogCallback",
    "NormalizationItem",
    "NormalizationPlan",
    "NormalizationReport",
    "NormalizationResultItem",
    "ProgressCallback",
    "ScanItem",
    "ScanResult",
    "IdentificationResult",
    "SortPlan",
    "SortReport",
    "SortMode",
    "audit_conversion_candidates",
    "add_identification_override",
    "add_identification_overrides_bulk",
    "suggest_identification_overrides",
    "get_symlink_warnings",
    "diff_sort_plans",
    "analyze_dat_sources",
    "build_dat_index",
    "build_library_report",
    "identify",
    "get_dat_sources",
    "execute_sort",
    "filter_scan_items",
    "infer_languages_and_version_from_name",
    "infer_region_from_name",
    "load_sort_resume_state",
    "normalize_input",
    "plan_normalization",
    "plan_sort",
    "plan_rebuild",
    "run_scan",
    "save_dat_sources",
    "execute_normalization",
    "async_run_scan",
    "async_plan_sort",
    "async_execute_sort",
    "ProgressEvent",
    "run_scan_stream",
    "plan_sort_stream",
    "execute_sort_stream",
    "Err",
    "Ok",
    "Result",
    "is_ok",
    "is_err",
    "unwrap",
    "unwrap_or",
    "export_scan_to_database",
    "apply_rollback",
    "load_rollback_manifest",
    "RollbackReport",
]
