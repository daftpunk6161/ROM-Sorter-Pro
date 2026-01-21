"""Shared formatting helpers for MVP UI tables."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def rom_display_name(input_path: str) -> str:
    try:
        return Path(str(input_path or "")).name or str(input_path or "")
    except Exception:
        return str(input_path or "")


def format_confidence(value: Optional[float]) -> str:
    try:
        conf = float(value or 0.0)
    except Exception:
        conf = 0.0
    if conf > 1.0:
        conf = 1.0
    return f"{int(conf * 100)}%"


def format_signals(item: object, default: str = "-") -> str:
    source = getattr(item, "detection_source", None)
    raw = getattr(item, "raw", None) or {}
    if isinstance(item, dict):
        raw = item.get("raw") or raw
        source = item.get("detection_source") or source
    signals = raw.get("signals")
    if isinstance(signals, (list, tuple)) and signals:
        return ", ".join(str(s) for s in signals[:5])
    if source:
        return str(source)
    signal = raw.get("detection_source") or raw.get("source")
    return str(signal) if signal else default


def format_candidates(item: object) -> str:
    raw = getattr(item, "raw", None) or {}
    if isinstance(item, dict):
        raw = item.get("raw") or raw
    candidates = raw.get("candidates") or raw.get("candidate_systems")
    if isinstance(candidates, (list, tuple)):
        return ", ".join(str(c) for c in candidates[:5])
    if candidates:
        return str(candidates)
    return "-"
