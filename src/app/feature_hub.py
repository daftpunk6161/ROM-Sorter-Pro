"""Feature Hub helpers for advanced GUI integrations.

Keeps UI decoupled from low-level modules while exposing safe summary APIs.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .models import ScanResult, SortReport
from ..security.security_utils import sanitize_path


def _iter_scan_items(scan_result: Optional[ScanResult]) -> Iterable[Any]:
    if scan_result is None:
        return []
    return scan_result.items or []


def build_collection_dashboard_summary(
    scan_result: Optional[ScanResult],
) -> Dict[str, Any]:
    """Build a lightweight analytics summary from the latest scan.

    Returns a dict with totals and top system/region info.
    """
    if scan_result is None:
        return {}

    from ..analytics.collection_dashboard import CollectionDashboard

    roms: List[Dict[str, Any]] = []
    for item in _iter_scan_items(scan_result):
        path = str(item.input_path or "")
        size = 0
        if path:
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
        system = str(item.detected_system or "Unknown").strip() or "Unknown"
        region = str(item.region or "Unknown").strip() or "Unknown"
        roms.append(
            {
                "path": path,
                "platform": system,
                "platform_display": system,
                "verified": bool(getattr(item, "is_exact", False)),
                "status": "unknown" if system == "Unknown" else "ok",
                "region": region,
                "size": size,
            }
        )

    dashboard = CollectionDashboard()
    stats = dashboard.analyze(roms, include_duplicates=False)

    top_systems = sorted(
        stats.systems.items(), key=lambda kv: kv[1].rom_count, reverse=True
    )
    top_regions = sorted(
        stats.regions_overall.items(), key=lambda kv: kv[1], reverse=True
    )

    return {
        "total_roms": stats.total_roms,
        "total_systems": stats.total_systems,
        "total_size_bytes": stats.total_size_bytes,
        "verified_roms": stats.verified_roms,
        "unknown_roms": stats.unknown_roms,
        "verification_rate": stats.verification_rate,
        "top_systems": [(name, sys.rom_count) for name, sys in top_systems[:5]],
        "top_regions": [(name, count) for name, count in top_regions[:5]],
    }


def ensure_active_library(
    source_path: str,
    config_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Ensure a library exists for source path and mark it active."""
    from ..core.multi_library import MultiLibraryManager

    sanitized = sanitize_path(str(source_path or ""))
    if not sanitized:
        return {"ok": False, "error": "Quelle fehlt"}

    manager = MultiLibraryManager(config_dir=config_dir)
    source_resolved = Path(sanitized).resolve()

    existing = None
    for lib in manager.get_all_libraries():
        try:
            if Path(lib.path).resolve() == source_resolved:
                existing = lib
                break
        except Exception:
            continue

    if existing is None:
        name = source_resolved.name or "Library"
        existing = manager.create_library(name=name, path=str(source_resolved))
    else:
        manager.set_active(existing.id)

    return {
        "ok": True,
        "active_id": existing.id,
        "active_name": existing.name,
        "active_path": existing.path,
        "total_libraries": len(manager.get_all_libraries()),
    }


def ai_normalize_name(
    name: str,
    config_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Run AI-assisted name normalization and return a dict payload."""
    from ..detectors.ai_normalizer import AINameNormalizer

    normalizer = AINameNormalizer(config_dir=config_dir)
    result = normalizer.normalize(str(name or ""))
    return {
        "original": result.original,
        "normalized": result.normalized,
        "confidence": result.confidence,
        "corrections": list(result.corrections or []),
        "extracted": dict(result.extracted_info or {}),
    }


def get_media_preview(
    file_path: str,
    system: str,
    media_dirs: Optional[List[str]] = None,
    cache_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve local media assets for a ROM.

    Returns dict with boxart/screenshot/title/fanart paths.
    """
    from ..core.file_utils import calculate_file_hash
    from ..ui.preview.boxart_preview import BoxartPreview

    sanitized = sanitize_path(str(file_path or ""))
    if not sanitized:
        return {"ok": False, "error": "Pfad fehlt"}

    path = Path(sanitized)
    if not path.exists():
        return {"ok": False, "error": "ROM-Datei nicht gefunden"}

    rom_hash = calculate_file_hash(str(path), algorithm="sha1")
    if not rom_hash:
        return {"ok": False, "error": "Hash konnte nicht berechnet werden"}

    preview = BoxartPreview(cache_dir=cache_dir, media_dirs=media_dirs or [])
    rom_media = preview.register_rom(rom_hash, path.stem, system or "")

    def _asset_path(asset: Any) -> Optional[str]:
        if asset and asset.local_path and Path(asset.local_path).exists():
            return str(asset.local_path)
        return None

    return {
        "ok": True,
        "rom_hash": rom_hash,
        "boxart": _asset_path(rom_media.boxart),
        "screenshot": _asset_path(rom_media.screenshot),
        "title_screen": _asset_path(rom_media.title_screen),
        "fanart": _asset_path(rom_media.fanart),
    }


def update_badges_after_scan(
    scan_result: Optional[ScanResult],
    config_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Update badges after a successful scan."""
    from ..gamification.badges import BadgeManager

    if scan_result is None or scan_result.cancelled:
        return {"ok": False, "new_unlocks": [], "stats": {}}

    manager = BadgeManager(config_dir=config_dir)
    rom_count = len(scan_result.items)
    systems_count = len({(item.detected_system or "Unknown") for item in scan_result.items})
    verified_count = len([item for item in scan_result.items if getattr(item, "is_exact", False)])

    unlocked = []
    unlocked.extend(manager.check_collection_badges(rom_count, systems_count, verified_count))
    scan_badge = manager.record_scan()
    if scan_badge:
        unlocked.append(scan_badge)
    unlocked.extend(manager.check_special_badges())

    return {
        "ok": True,
        "new_unlocks": [badge.name for badge in unlocked],
        "stats": manager.get_stats(),
    }


def update_badges_after_execute(
    sort_report: Optional[SortReport],
    config_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Update badges after execute (sort) operation."""
    from ..gamification.badges import BadgeManager

    if sort_report is None or sort_report.cancelled:
        return {"ok": False, "new_unlocks": [], "stats": {}}

    manager = BadgeManager(config_dir=config_dir)
    unlocked = manager.record_sort()

    return {
        "ok": True,
        "new_unlocks": [badge.name for badge in unlocked],
        "stats": manager.get_stats(),
    }


def get_badge_status(
    config_dir: Optional[str] = None,
    *,
    include_hidden: bool = False,
) -> Dict[str, Any]:
    """Return current badge status and progress."""
    from ..gamification.badges import BadgeManager

    manager = BadgeManager(config_dir=config_dir)
    return {
        "stats": manager.get_stats(),
        "badges": manager.get_all_badges(include_hidden=include_hidden),
    }
