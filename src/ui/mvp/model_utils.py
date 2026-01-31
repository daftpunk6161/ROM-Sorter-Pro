"""Shared formatting helpers for MVP UI tables."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional


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
    if conf < 0.0:
        conf = 0.0
    if conf >= 0.85:
        icon = "🟢"
    elif conf >= 0.70:
        icon = "🟡"
    else:
        icon = "🔴"
    return f"{icon} {int(conf * 100)}%"


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


def _normalize_signal(value: str) -> str:
    return str(value or "").strip().replace("-", "_").replace(" ", "_").upper()


def _signal_reasons(signals: Iterable[str]) -> str:
    mapping = {
        "NO_DAT_MATCH": "keine DAT-Übereinstimmung",
        "NO_INDEX": "DAT-Index fehlt",
        "EXTENSION_UNKNOWN": "Dateiendung unbekannt",
        "AMBIGUOUS": "mehrdeutige Erkennung",
        "CONFLICT_GROUP": "Konfliktgruppe",
        "CONTRADICTION": "Widerspruch in Signalen",
        "HASH_COLLISION": "mögliche Hash-Kollision",
        "OVERRIDE_RULE": "Override-Regel",
        "BAD_DUMP": "Bad Dump (DAT)",
        "FUZZY_NAME_MATCH": "Fuzzy-Name-Match",
        "MAGIC_BYTES": "Magic-Bytes",
    }
    labels = []
    for signal in signals:
        key = _normalize_signal(signal)
        labels.append(mapping.get(key, signal))
    return ", ".join(label for label in labels if label)


def format_reason(item: object, *, min_confidence: Optional[float] = None) -> str:
    raw = getattr(item, "raw", None) or {}
    detection_source = getattr(item, "detection_source", None)
    detection_confidence = getattr(item, "detection_confidence", None)
    if isinstance(item, dict):
        raw = item.get("raw") or raw
        detection_source = item.get("detection_source") or detection_source
        detection_confidence = item.get("detection_confidence") or detection_confidence

    reason = str(raw.get("reason") or raw.get("policy") or "").strip()

    try:
        conf_value = float(detection_confidence) if detection_confidence is not None else None
    except Exception:
        conf_value = None

    if str(detection_source) == "policy-low-confidence":
        try:
            threshold = float(min_confidence) if min_confidence is not None else None
        except Exception:
            threshold = None
        if threshold is not None:
            return f"low-confidence (<{threshold:.2f})"
        return "low-confidence"

    if not reason and detection_source:
        reason = str(detection_source)

    signals = raw.get("signals") or []
    signal_text = ""
    if isinstance(signals, (list, tuple)) and signals:
        signal_text = _signal_reasons([str(s) for s in signals])

    details = [part for part in (reason, signal_text) if part]
    if not details:
        return ""
    return " | ".join(details)


def format_heuristics(item: object) -> str:
    raw = getattr(item, "raw", None) or {}
    if isinstance(item, dict):
        raw = item.get("raw") or raw
    details = raw.get("candidate_details") or raw.get("heuristic_details") or []
    if not isinstance(details, list) or not details:
        return "-"
    lines = []
    for entry in details[:5]:
        if not isinstance(entry, dict):
            continue
        platform_id = str(entry.get("platform_id") or "-")
        try:
            score = float(entry.get("score", 0.0))
        except Exception:
            score = 0.0
        signals = entry.get("signals") or []
        signal_text = ", ".join(str(s) for s in signals[:4]) if isinstance(signals, list) else "-"
        conflicts = entry.get("conflict_groups") or []
        conflict_text = ", ".join(str(c) for c in conflicts[:3]) if isinstance(conflicts, list) else "-"
        lines.append(f"{platform_id} (score {score:.2f}) | {signal_text} | Konflikt: {conflict_text}")
    return "\n".join(lines) if lines else "-"


def format_system_badge(system: Optional[str]) -> str:
    value = str(system or "").strip()
    if not value or value.lower() == "unknown":
        return value or "Unknown"

    key = value.lower()
    icon = "🎮"
    icon_map = {
        "nes": "🟥",
        "snes": "🟪",
        "super nintendo": "🟪",
        "n64": "🔵",
        "nintendo 64": "🔵",
        "gamecube": "🟣",
        "game boy": "🟢",
        "gb": "🟢",
        "gbc": "🟡",
        "gba": "🟡",
        "nintendo ds": "🟦",
        "3ds": "🟦",
        "switch": "🔴",
        "wii": "⚪",
        "wii u": "⚪",
        "genesis": "⚫",
        "mega drive": "⚫",
        "megadrive": "⚫",
        "mastersystem": "⚫",
        "psx": "🔺",
        "playstation": "🔺",
        "ps2": "🔷",
        "ps3": "🔷",
        "psp": "🔹",
        "vita": "🔹",
        "xbox": "❎",
        "xbox 360": "❎",
    }
    for needle, emoji in icon_map.items():
        if needle in key:
            icon = emoji
            break
    return f"{icon} {value}"
