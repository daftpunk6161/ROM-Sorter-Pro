#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Library health report utilities."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List


def _iter_items(scan_result: Any) -> Iterable[Any]:
    if hasattr(scan_result, "items"):
        return scan_result.items
    return scan_result or []


def generate_library_health_report(scan_result: Any) -> Dict[str, Any]:
    """Generate a basic library health report from a ScanResult or list of rom dicts."""
    items = list(_iter_items(scan_result))

    unknown_console = 0
    missing_metadata = 0

    hash_map: Dict[str, List[Any]] = defaultdict(list)

    for item in items:
        if hasattr(item, "detected_system"):
            system = item.detected_system or "Unknown"
            raw = item.raw or {}
        else:
            system = (item.get("system") if isinstance(item, dict) else None) or "Unknown"
            raw = item if isinstance(item, dict) else {}

        if system == "Unknown":
            unknown_console += 1

        if not raw.get("detection_confidence") and not raw.get("detection_source"):
            missing_metadata += 1

        hash_val = raw.get("md5") or raw.get("sha1") or raw.get("crc32")
        if hash_val:
            hash_map[f"{system}:{hash_val}"] .append(item)

    duplicates = {k: v for k, v in hash_map.items() if len(v) > 1}

    return {
        "total_roms": len(items),
        "unknown_console": unknown_console,
        "missing_metadata": missing_metadata,
        "duplicate_groups": len(duplicates),
        "duplicates": {k: len(v) for k, v in duplicates.items()},
    }
