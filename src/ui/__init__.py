"""ROM Sorter Pro UI package.

Minimal, side-effect-free exports to keep GUI startup stable.
"""

from __future__ import annotations

# Public, side-effect-free helpers
def is_ui_available() -> bool:
    try:
        import tkinter  # noqa: F401

        return True
    except Exception:
        return False


def get_ui_mode() -> str:
    if not is_ui_available():
        return "cli"

    try:
        import PySide6  # noqa: F401

        return "qt"
    except Exception:
        pass

    try:
        import PyQt5  # noqa: F401

        return "qt"
    except Exception:
        pass

    return "tkinter"


__all__ = [
    "is_ui_available",
    "get_ui_mode",
]
