"""Scan controller facade (thin wrapper)."""

from __future__ import annotations

from typing import Optional

from .controller import identify as _identify
from .controller import run_scan as _run_scan
from .models import CancelToken, IdentificationResult, LogCallback, ProgressCallback, ScanItem, ScanResult
from ..config import Config


def run_scan(
    source_path: str,
    config: Optional[Config | dict] = None,
    progress_cb: Optional[ProgressCallback] = None,
    log_cb: Optional[LogCallback] = None,
    cancel_token: Optional[CancelToken] = None,
) -> ScanResult:
    return _run_scan(
        source_path=source_path,
        config=config,
        progress_cb=progress_cb,
        log_cb=log_cb,
        cancel_token=cancel_token,
    )


def identify(
    scan_items: list[ScanItem],
    config: Optional[Config | dict] = None,
    progress_cb: Optional[ProgressCallback] = None,
    cancel_token: Optional[CancelToken] = None,
) -> list[IdentificationResult]:
    return _identify(
        scan_items=scan_items,
        config=config,
        progress_cb=progress_cb,
        cancel_token=cancel_token,
    )
