from __future__ import annotations

ICONS = {
    "scan": "🔎",
    "preview": "👁️",
    "execute": "⚡",
    "cancel": "⛔",
    "settings": "⚙️",
    "db": "🗄️",
    "igir": "🧩",
    "convert": "🧪",
    "sort": "🗂️",
    "log": "📜",
    "safe": "✅",
    "warn": "⚠️",
    "error": "❌",
    "folder": "📁",
    "export": "⬇️",
}


def label(text: str, icon_key: str) -> str:
    icon = ICONS.get(icon_key, "")
    return f"{icon} {text}".strip() if icon else text
