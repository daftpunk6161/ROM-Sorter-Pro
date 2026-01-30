"""Minimal i18n helper for UI labels (de/en)."""

from __future__ import annotations

from typing import Dict, Optional

from ..config import load_config

_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "de": {
        "scan": "Scan",
        "preview": "Preview",
        "preview_sort": "Preview Sort (Dry-run)",
        "execute": "Execute",
        "execute_sort": "Execute Sort",
        "cancel": "Cancel",
        "resume": "Resume",
        "retry_failed": "Retry Failed",
        "convert_execute": "Konvertierungen ausführen",
        "convert_audit": "Konvertierungen prüfen (Audit)",
        "paths": "Pfade",
        "source": "Quelle",
        "dest": "Ziel",
        "choose_source": "Quelle wählen…",
        "choose_dest": "Ziel wählen…",
        "open_dest": "Ziel öffnen",
        "action": "Aktion",
        "actions": "Aktionen",
        "conflicts": "Bei Konflikt",
        "mode": "Modus",
        "mode_copy": "copy",
        "mode_move": "move",
        "status": "Status",
        "results": "Ergebnisse",
        "log": "Log",
        "ready": "Bereit",
    },
    "en": {
        "scan": "Scan",
        "preview": "Preview",
        "preview_sort": "Preview sort (dry-run)",
        "execute": "Execute",
        "execute_sort": "Execute sort",
        "cancel": "Cancel",
        "resume": "Resume",
        "retry_failed": "Retry Failed",
        "convert_execute": "Run conversions",
        "convert_audit": "Audit conversions",
        "paths": "Paths",
        "source": "Source",
        "dest": "Destination",
        "choose_source": "Choose source…",
        "choose_dest": "Choose destination…",
        "open_dest": "Open destination",
        "action": "Action",
        "actions": "Actions",
        "conflicts": "On conflict",
        "mode": "Mode",
        "mode_copy": "copy",
        "mode_move": "move",
        "status": "Status",
        "results": "Results",
        "log": "Log",
        "ready": "Ready",
    },
}


def _normalize_lang(value: Optional[str]) -> str:
    if not value:
        return "de"
    text = str(value).lower()
    if text.startswith("en"):
        return "en"
    return "de"


def get_ui_language() -> str:
    try:
        cfg = load_config()
        ui_cfg = cfg.get("ui") or {}
        lang = ui_cfg.get("language") or cfg.get("language")
        return _normalize_lang(lang)
    except Exception:
        return "de"


def translate(key: str, *, default: Optional[str] = None, lang: Optional[str] = None) -> str:
    language = _normalize_lang(lang or get_ui_language())
    return _TRANSLATIONS.get(language, {}).get(key, default or key)
