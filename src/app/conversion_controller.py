"""Conversion/normalization controller facade (thin wrapper)."""

from __future__ import annotations

from typing import Optional, Iterable

from .controller import (
    CancelToken,
    ConversionAuditReport,
    ProgressCallback,
    LogCallback,
    audit_conversion_candidates as _audit,
    normalize_input as _normalize_input,
    plan_normalization as _plan_normalization,
    execute_normalization as _execute_normalization,
    NormalizationItem,
    NormalizationPlan,
    NormalizationReport,
)
from ..config import Config


def audit_conversion_candidates(
    source_path: str,
    config: Optional[Config] = None,
    progress_cb: Optional[ProgressCallback] = None,
    log_cb: Optional[LogCallback] = None,
    cancel_token: Optional[CancelToken] = None,
    include_disabled: bool = True,
) -> ConversionAuditReport:
    return _audit(
        source_path=source_path,
        config=config,
        progress_cb=progress_cb,
        log_cb=log_cb,
        cancel_token=cancel_token,
        include_disabled=include_disabled,
    )


def normalize_input(input_path: str, *, platform_hint: Optional[str] = None) -> NormalizationItem:
    return _normalize_input(input_path, platform_hint=platform_hint)


def plan_normalization(
    items: Iterable[NormalizationItem],
    *,
    output_root: Optional[str] = None,
    temp_root: Optional[str] = None,
) -> NormalizationPlan:
    return _plan_normalization(items, output_root=output_root, temp_root=temp_root)


def execute_normalization(
    plan: NormalizationPlan,
    *,
    cancel_token: Optional[CancelToken] = None,
    dry_run: bool = True,
) -> NormalizationReport:
    return _execute_normalization(plan, cancel_token=cancel_token, dry_run=dry_run)
