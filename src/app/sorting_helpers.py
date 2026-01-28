"""Sorting helper functions."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .models import ConflictPolicy, ScanItem


def _apply_rename_template(template: str, item: ScanItem, src: Path, safe_system: str) -> str:
    class _SafeDict(dict):
        def __missing__(self, key):
            return ""

    ext_dot = src.suffix
    ext = ext_dot.lstrip(".")

    canonical = None
    try:
        raw = getattr(item, "raw", None) or {}
        canonical = raw.get("canonical_name")
    except Exception:
        canonical = None

    base_name = (canonical or src.stem).strip() if isinstance(canonical, str) else src.stem

    data = _SafeDict(
        name=base_name,
        ext=ext,
        ext_dot=ext_dot,
        system=safe_system,
        region=item.region or "",
        version=item.version or "",
        languages="-".join(item.languages or ()),
    )

    rendered = template.format_map(data).strip()
    if not rendered:
        rendered = src.name

    if not rendered.lower().endswith(ext_dot.lower()) and ext_dot:
        rendered += ext_dot
    return rendered


def _resolve_target_path(target_file: Path, on_conflict: ConflictPolicy) -> Optional[Path]:
    if not target_file.exists():
        return target_file

    if on_conflict == "skip":
        return None

    if on_conflict == "overwrite":
        return target_file

    stem = target_file.stem
    suffix = target_file.suffix
    for i in range(1, 10_000):
        candidate = target_file.with_name(f"{stem} ({i}){suffix}")
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"Could not find free filename for {target_file.name}")


def _safe_system_name(system: str) -> str:
    value = (system or "Unknown").strip() or "Unknown"
    safe = "".join(ch for ch in value if ch.isalnum() or ch in (" ", "-", "_", ".")).strip()
    return safe or "Unknown"


def _is_confident_detection(item: "ScanItem", min_confidence: float) -> bool:
    source = str(item.detection_source or "").strip().lower()
    try:
        conf = float(item.detection_confidence or 0.0)
    except Exception:
        conf = 0.0

    if (item.detected_system or "Unknown").strip() in ("", "Unknown"):
        return False

    if not source:
        return True

    if source in ("manual", "user", "override"):
        return True

    if source.startswith("dat:"):
        return True

    if source == "extension-unique":
        return conf >= min_confidence

    return conf >= min_confidence
