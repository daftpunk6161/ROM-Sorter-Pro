"""Qt typography helpers (optional font loading)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import importlib


def _try_import_qt():
    for base in ("PySide6", "PyQt5"):
        try:
            QtGui = importlib.import_module(f"{base}.QtGui")
            QtWidgets = importlib.import_module(f"{base}.QtWidgets")
            return QtGui, QtWidgets
        except Exception:
            continue
    return None, None


def try_load_font(font_path: str) -> Optional[str]:
    path = Path(font_path)
    if not path.exists():
        return None
    QtGui, _QtWidgets = _try_import_qt()
    if QtGui is None:
        return None
    try:
        fid = QtGui.QFontDatabase.addApplicationFont(str(path))
        if fid < 0:
            return None
        families = QtGui.QFontDatabase.applicationFontFamilies(fid)
        return families[0] if families else None
    except Exception:
        return None


def set_app_font(family: str, point_size: int = 10) -> None:
    QtGui, QtWidgets = _try_import_qt()
    if QtWidgets is None:
        return
    app = QtWidgets.QApplication.instance()
    if not app:
        return
    try:
        font = app.font()
        font.setFamily(family)
        font.setPointSize(point_size)
        app.setFont(font)
    except Exception:
        return
