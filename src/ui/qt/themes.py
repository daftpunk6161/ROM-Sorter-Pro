"""Qt palette-based themes for optional shell layouts.

This module avoids importing Qt at import time so tests can run without Qt.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
from typing import Any, Callable, Optional

from .typography import set_app_font, try_load_font


def _try_import_qt():
    for base in ("PySide6", "PyQt5"):
        try:
            QtGui = importlib.import_module(f"{base}.QtGui")
            QtWidgets = importlib.import_module(f"{base}.QtWidgets")
            QtCore = importlib.import_module(f"{base}.QtCore")
            return QtGui, QtWidgets, QtCore
        except Exception:
            continue
    return None, None, None


def _qss_base(radius: int = 10, padding: int = 8) -> str:
    return f"""
    * {{
        font-size: 10pt;
    }}
    QWidget {{
        border: none;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        border-radius: {radius}px;
        padding: {padding}px;
        border: 1px solid rgba(127,127,127,0.35);
    }}
    QComboBox::drop-down {{
        border: none;
        width: 26px;
    }}
    QPushButton {{
        border-radius: {radius}px;
        padding: {padding}px 14px;
        font-weight: 600;
    }}
    QPushButton:disabled {{
        opacity: 0.55;
    }}
    QGroupBox {{
        border: 1px solid rgba(127,127,127,0.25);
        border-radius: {radius}px;
        margin-top: 10px;
        padding: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        font-weight: 700;
    }}
    QTableView {{
        border-radius: {radius}px;
        border: 1px solid rgba(127,127,127,0.25);
        gridline-color: rgba(127,127,127,0.18);
    }}
    QHeaderView::section {{
        padding: 8px;
        font-weight: 700;
        border: none;
        border-bottom: 1px solid rgba(127,127,127,0.25);
    }}
    QScrollBar:vertical {{
        width: 12px;
        margin: 2px;
        border-radius: 6px;
        background: rgba(127,127,127,0.08);
    }}
    QScrollBar::handle:vertical {{
        border-radius: 6px;
        min-height: 28px;
        background: rgba(127,127,127,0.35);
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QToolBar {{
        spacing: 8px;
        padding: 6px;
    }}

    /* Wizard cards */
    QFrame#wizard_card {{
        background: rgba(255,255,255,0.70);
        border: 1px solid rgba(15,23,42,0.08);
        border-radius: 16px;
    }}
    QLabel#wizard_step {{
        font-size: 18pt;
        font-weight: 800;
    }}
    QLabel#wizard_title {{
        font-size: 12pt;
        font-weight: 700;
    }}
    QLabel#wizard_subtitle {{
        opacity: 0.75;
    }}
    QLabel#wizard_icon {{
        font-size: 26pt;
    }}
    """


def _palette_builder(colors: dict[str, str]) -> Callable[[object, object], object]:
    def _build(QtGui, _QtCore):
        palette = QtGui.QPalette()
        qcolor = QtGui.QColor
        palette.setColor(QtGui.QPalette.Window, qcolor(colors["window"]))
        palette.setColor(QtGui.QPalette.WindowText, qcolor(colors["window_text"]))
        palette.setColor(QtGui.QPalette.Base, qcolor(colors["base"]))
        palette.setColor(QtGui.QPalette.Text, qcolor(colors["text"]))
        palette.setColor(QtGui.QPalette.Button, qcolor(colors["button"]))
        palette.setColor(QtGui.QPalette.ButtonText, qcolor(colors["button_text"]))
        palette.setColor(QtGui.QPalette.Highlight, qcolor(colors["highlight"]))
        palette.setColor(QtGui.QPalette.HighlightedText, qcolor(colors["highlighted_text"]))
        palette.setColor(QtGui.QPalette.Link, qcolor(colors.get("link", colors["highlight"])))
        try:
            palette.setColor(QtGui.QPalette.PlaceholderText, qcolor(colors.get("placeholder", colors["text"])))
        except Exception:
            pass
        return palette

    return _build


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    qss: str
    palette_builder: Optional[Callable[[object, object], object]] = None
    base_font_family: Optional[str] = None
    base_font_size: int = 10
    font_path: Optional[str] = None


THEMES = {
    "modern_light": Theme(
        key="modern_light",
        name="Modern Light",
        qss=_qss_base(radius=10, padding=8) + r"""
        QWidget { background: #f7f7fb; color: #12131a; }
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #ffffff; }
        QPushButton { background: #2b7cff; color: white; }
        QPushButton:hover { background: #1f6ef5; }
        QPushButton:pressed { background: #1b5fce; }
        QPushButton#secondary { background: rgba(18,19,26,0.06); color: #12131a; }
        QPushButton#secondary:hover { background: rgba(18,19,26,0.10); }
        QPushButton#danger { background: #e5484d; color: white; }
        QPushButton#danger:hover { background: #d63e43; }
        QHeaderView::section { background: rgba(18,19,26,0.04); }
        QGroupBox { background: rgba(255,255,255,0.55); }
        """,
        palette_builder=_palette_builder(
            {
                "window": "#f7f7fb",
                "window_text": "#12131a",
                "base": "#ffffff",
                "text": "#12131a",
                "button": "#f7f7fb",
                "button_text": "#12131a",
                "highlight": "#2b7cff",
                "highlighted_text": "#ffffff",
                "link": "#2b7cff",
                "placeholder": "#6c7280",
            }
        ),
    ),
    "modern_dark": Theme(
        key="modern_dark",
        name="Modern Dark",
        qss=_qss_base(radius=12, padding=9) + r"""
        QWidget { background: #0f1115; color: #e8eaf0; }
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background: #141821;
            border: 1px solid rgba(255,255,255,0.15);
        }
        QPushButton { background: #7c5cff; color: white; }
        QPushButton:hover { background: #6a4cff; }
        QPushButton:pressed { background: #563adf; }
        QPushButton#secondary { background: rgba(255,255,255,0.06); color: #e8eaf0; }
        QPushButton#secondary:hover { background: rgba(255,255,255,0.10); }
        QPushButton#danger { background: #ff4d4f; color: white; }
        QPushButton#danger:hover { background: #e64547; }
        QHeaderView::section { background: rgba(255,255,255,0.06); }
        QGroupBox { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.10); }
        QTableView { background: #141821; border: 1px solid rgba(255,255,255,0.10); }
        """,
        palette_builder=_palette_builder(
            {
                "window": "#0f1115",
                "window_text": "#e8eaf0",
                "base": "#141821",
                "text": "#e8eaf0",
                "button": "#0f1115",
                "button_text": "#e8eaf0",
                "highlight": "#7c5cff",
                "highlighted_text": "#0f1115",
                "link": "#a08bff",
                "placeholder": "#9aa3b2",
            }
        ),
    ),
    "retro_neon": Theme(
        key="retro_neon",
        name="Retro Neon",
        qss=_qss_base(radius=8, padding=8) + r"""
        QWidget { background: #0b0f14; color: #d8faff; }
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background: #0f1620;
            border: 1px solid rgba(0,245,212,0.45);
        }
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #ff2bd6, stop:1 #00f5d4);
            color: #061018;
            border: 1px solid rgba(0,245,212,0.45);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        QPushButton:hover { opacity: 0.92; }
        QPushButton:pressed { opacity: 0.86; }
        QPushButton#secondary {
            background: transparent;
            color: #d8faff;
            border: 1px dashed rgba(255,43,214,0.55);
        }
        QPushButton#secondary:hover { background: rgba(255,43,214,0.10); }
        QPushButton#danger { background: #ff4d4f; color: #0b0f14; border: 1px solid rgba(255,77,79,0.75); }
        QGroupBox { background: rgba(0,245,212,0.06); border: 1px solid rgba(0,245,212,0.25); }
        QHeaderView::section { background: rgba(255,43,214,0.10); border-bottom: 1px solid rgba(0,245,212,0.25); }
        QTableView {
            background: #0f1620;
            border: 1px solid rgba(0,245,212,0.25);
            selection-background-color: rgba(0,245,212,0.25);
            selection-color: #d8faff;
        }
        """,
        palette_builder=_palette_builder(
            {
                "window": "#0b0f14",
                "window_text": "#d8faff",
                "base": "#0f1620",
                "text": "#d8faff",
                "button": "#0b0f14",
                "button_text": "#d8faff",
                "highlight": "#00f5d4",
                "highlighted_text": "#061018",
                "link": "#00f5d4",
                "placeholder": "#86a1ad",
            }
        ),
    ),
    "crt_green": Theme(
        key="crt_green",
        name="CRT Green",
        palette_builder=_palette_builder(
            {
                "window": "#06110b",
                "window_text": "#b6ffb6",
                "base": "#07160e",
                "text": "#b6ffb6",
                "button": "#06110b",
                "button_text": "#b6ffb6",
                "highlight": "#39ff14",
                "highlighted_text": "#06110b",
                "link": "#39ff14",
                "placeholder": "#5f8f6a",
            }
        ),
        qss=_qss_base(radius=6, padding=7) + r"""
        QWidget { background: #06110b; color: #b6ffb6; }
        QFrame#card, QGroupBox, QTableView, QPlainTextEdit, QTextEdit {
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(57,255,20,0.06),
                stop:0.08 rgba(0,0,0,0.00),
                stop:0.16 rgba(57,255,20,0.04),
                stop:1 rgba(0,0,0,0.00)
            );
            border: 1px solid rgba(57,255,20,0.25);
        }
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background: #07160e;
            border: 1px solid rgba(57,255,20,0.45);
            color: #b6ffb6;
            selection-background-color: rgba(57,255,20,0.30);
            selection-color: #b6ffb6;
        }
        QPushButton {
            background: transparent;
            color: #b6ffb6;
            border: 1px solid rgba(57,255,20,0.55);
            border-radius: 6px;
            padding: 7px 14px;
            font-weight: 800;
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        QPushButton:hover { background: rgba(57,255,20,0.10); }
        QPushButton:pressed { background: rgba(57,255,20,0.18); }
        QPushButton#secondary {
            border: 1px dashed rgba(57,255,20,0.45);
            background: rgba(0,0,0,0.15);
        }
        QPushButton#danger {
            border: 1px solid rgba(255,80,80,0.75);
            color: #ffb0b0;
        }
        QPushButton#danger:hover { background: rgba(255,80,80,0.12); }
        QHeaderView::section {
            background: rgba(57,255,20,0.08);
            color: #b6ffb6;
            border-bottom: 1px solid rgba(57,255,20,0.25);
            font-weight: 900;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }
        QTableView {
            background: #07160e;
            gridline-color: rgba(57,255,20,0.18);
            selection-background-color: rgba(57,255,20,0.25);
            selection-color: #b6ffb6;
            border: 1px solid rgba(57,255,20,0.25);
        }
        QLabel { color: #b6ffb6; }
        """,
        base_font_family="'Press Start 2P', 'Consolas', monospace",
        base_font_size=9,
    ),
    "gameboy_dmg": Theme(
        key="gameboy_dmg",
        name="GameBoy DMG",
        palette_builder=_palette_builder(
            {
                "window": "#d6d2c4",
                "window_text": "#1f2a1f",
                "base": "#c8ccb8",
                "text": "#1f2a1f",
                "button": "#d6d2c4",
                "button_text": "#1f2a1f",
                "highlight": "#5b7f3a",
                "highlighted_text": "#1f2a1f",
                "link": "#5b7f3a",
                "placeholder": "#4c5a4c",
            }
        ),
        qss=_qss_base(radius=10, padding=8) + r"""
        QWidget { background: #d6d2c4; color: #1f2a1f; }
        QGroupBox {
            background: rgba(255,255,255,0.22);
            border: 2px solid rgba(31,42,31,0.28);
            border-radius: 12px;
        }
        QGroupBox::title {
            font-weight: 900;
            letter-spacing: 0.3px;
        }
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background: #c8ccb8;
            border: 2px solid rgba(31,42,31,0.25);
            border-radius: 10px;
            color: #1f2a1f;
        }
        QHeaderView::section {
            background: rgba(31,42,31,0.07);
            border-bottom: 2px solid rgba(31,42,31,0.22);
            font-weight: 900;
        }
        QTableView {
            background: #c8ccb8;
            border: 2px solid rgba(31,42,31,0.22);
            gridline-color: rgba(31,42,31,0.18);
            selection-background-color: rgba(91,127,58,0.35);
            selection-color: #1f2a1f;
            border-radius: 12px;
        }
        QPushButton {
            background: #b0b0aa;
            color: #1f2a1f;
            border: 2px solid rgba(31,42,31,0.25);
            border-radius: 12px;
            padding: 10px 16px;
            font-weight: 900;
        }
        QPushButton:hover { background: #a7a7a0; }
        QPushButton:pressed { background: #9e9e97; }
        QPushButton#secondary { background: #c0c0ba; }
        QPushButton#danger {
            background: #7a2c2c;
            color: #f3e7e7;
            border: 2px solid rgba(31,42,31,0.25);
        }
        QPushButton#danger:hover { background: #6c2626; }
        """,
        base_font_family="'Press Start 2P', 'Consolas', monospace",
        base_font_size=9,
    ),
    "graphite": Theme(
        key="graphite",
        name="Graphite",
        qss=_qss_base(radius=8, padding=7) + r"""
        QWidget { background: #1f2228; color: #e6e9ef; }
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background: #2a2e36;
            border: 1px solid rgba(230,233,239,0.15);
        }
        QPushButton { background: #5d8efb; color: #0b1220; }
        QPushButton:hover { background: #6fa0ff; }
        QGroupBox { background: rgba(46,52,64,0.35); border: 1px solid rgba(230,233,239,0.12); }
        """,
        palette_builder=_palette_builder(
            {
                "window": "#1f2228",
                "window_text": "#e6e9ef",
                "base": "#2a2e36",
                "text": "#e6e9ef",
                "button": "#2f3541",
                "button_text": "#e6e9ef",
                "highlight": "#5d8efb",
                "highlighted_text": "#0b1220",
                "link": "#7aa4ff",
                "placeholder": "#9aa3b2",
            }
        ),
        base_font_family="'Segoe UI', 'Inter', sans-serif",
        base_font_size=10,
    ),
}


class ThemeManager:
    def __init__(self, _app: Optional[object] = None) -> None:
        self._app = _app

    def available(self):
        return THEMES

    def apply(self, key: str) -> bool:
        theme = THEMES.get(key)
        if theme is None:
            return False
        QtGui, QtWidgets, _QtCore = _try_import_qt()
        if QtGui is None or QtWidgets is None:
            return False
        app: Any = self._app or QtWidgets.QApplication.instance()
        if app is None:
            return False
        try:
            if theme.font_path:
                family = try_load_font(theme.font_path)
                if family:
                    set_app_font(family, theme.base_font_size)
                elif theme.base_font_family:
                    set_app_font(theme.base_font_family, theme.base_font_size)
            elif theme.base_font_family:
                set_app_font(theme.base_font_family, theme.base_font_size)
            if theme.palette_builder is not None:
                palette = theme.palette_builder(QtGui, _QtCore)
                app.setPalette(palette)
            if theme.qss:
                app.setStyleSheet(theme.qss)
            return True
        except Exception:
            return False


__all__ = ["Theme", "ThemeManager", "THEMES"]
