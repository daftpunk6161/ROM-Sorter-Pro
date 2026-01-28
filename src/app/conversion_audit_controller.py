"""Conversion audit helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import Config, load_config
from .conversion_settings import _match_conversion_rule_for_audit, _normalize_extension, _resolve_conversion_settings
from .models import CancelToken, ConversionAuditItem, ConversionAuditReport


def _load_cfg(config: Optional[Config | Dict[str, Any]]) -> Config:
    if isinstance(config, Config):
        return config
    if isinstance(config, dict):
        return Config(config)
    try:
        return Config(load_config())
    except Exception:
        return Config()


def audit_conversion_candidates(
    source_path: str,
    config: Optional[Config] = None,
    progress_cb=None,
    log_cb=None,
    cancel_token: Optional[CancelToken] = None,
    include_disabled: bool = True,
) -> ConversionAuditReport:
    from .controller import run_scan

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
                current_extension=current_ext,
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
        source_path=str(source_path or ""),
        items=items,
        totals=totals,
        cancelled=cancelled,
    )
