import os
import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.integration


def test_qt_main_window_render_smoke() -> None:
    from src.ui.compat import _detect_qt_binding

    if _detect_qt_binding() is None:
        return

    from src.ui.mvp import qt_app

    QtWidgets, _QtCore, _QtGui, _binding = qt_app._load_qt()
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = QtWidgets.QMainWindow()
    window.show()
    app.processEvents()
    window.close()


def test_tk_main_window_render_smoke() -> None:
    try:
        import tkinter as tk
    except Exception:
        return

    try:
        root = tk.Tk()
    except Exception:
        return

    try:
        root.withdraw()
        root.update_idletasks()
        root.update()
    finally:
        root.destroy()
