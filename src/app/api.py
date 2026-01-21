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
    LogCallback,
    ProgressCallback,
    ScanItem,
    ScanResult,
    IdentificationResult,
    SortPlan,
    SortReport,
    SortMode,
    audit_conversion_candidates,
    build_dat_index,
    identify,
    execute_sort,
    filter_scan_items,
    infer_languages_and_version_from_name,
    infer_region_from_name,
    load_sort_resume_state,
    plan_normalization,
    plan_sort,
    run_scan,
    execute_normalization,
)

__all__ = [
    "ActionStatusCallback",
    "CancelToken",
    "ConflictPolicy",
    "ConversionAuditReport",
    "ConversionMode",
    "LogCallback",
    "ProgressCallback",
    "ScanItem",
    "ScanResult",
    "IdentificationResult",
    "SortPlan",
    "SortReport",
    "SortMode",
    "audit_conversion_candidates",
    "build_dat_index",
    "identify",
    "execute_sort",
    "filter_scan_items",
    "infer_languages_and_version_from_name",
    "infer_region_from_name",
    "load_sort_resume_state",
    "plan_normalization",
    "plan_sort",
    "run_scan",
    "execute_normalization",
]
