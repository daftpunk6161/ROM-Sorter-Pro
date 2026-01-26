"""Public controller API surface for UI and integrations.

Centralizes stable imports to keep UI decoupled from controller internals.
"""

from __future__ import annotations

from .controller import (
    ActionStatusCallback,
    CancelToken,
    ConflictPolicy,
    ConversionAuditReport,
    ConversionMode,
    DatSourceReport,
    LogCallback,
    NormalizationItem,
    NormalizationPlan,
    NormalizationReport,
    ProgressCallback,
    ScanItem,
    ScanResult,
    IdentificationResult,
    SortPlan,
    SortReport,
    SortMode,
    analyze_dat_sources,
    build_dat_index,
    build_library_report,
    filter_scan_items,
    infer_languages_and_version_from_name,
    infer_region_from_name,
    load_sort_resume_state,
    get_dat_sources,
    save_dat_sources,
)
from .scan_controller import run_scan, identify
from .sort_controller import plan_sort, plan_rebuild, execute_sort
from .conversion_controller import (
    audit_conversion_candidates,
    normalize_input,
    plan_normalization,
    execute_normalization,
)
from ..core.normalization import NormalizationResultItem

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
]
