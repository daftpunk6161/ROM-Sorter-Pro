from __future__ import annotations

from pathlib import Path
from typing import Optional, cast

try:
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication
except Exception:  # PyQt5 fallback
    from PyQt5.QtGui import QFontDatabase
    from PyQt5.QtWidgets import QApplication


def try_load_font(font_path: str) -> Optional[str]:
    p = Path(font_path)
    if not p.exists():
        return None
    fid = QFontDatabase.addApplicationFont(str(p))
    if fid < 0:
        return None
    families = QFontDatabase.applicationFontFamilies(fid)
    return families[0] if families else None


def set_app_font(family: str, point_size: int = 10) -> None:
    app = QApplication.instance()
    if not app:
        return
    app = cast(QApplication, app)
    f = app.font()
    f.setFamily(family)
    f.setPointSize(point_size)
    app.setFont(f)
