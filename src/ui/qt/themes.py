from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, cast

try:
    from PySide6.QtGui import QPalette, QColor, QFontDatabase  # noqa: F401
    from PySide6.QtWidgets import QApplication
except Exception:
    from PyQt5.QtGui import QPalette, QColor, QFontDatabase  # noqa: F401
    from PyQt5.QtWidgets import QApplication


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    qss: str
    palette: Optional[QPalette] = None
    base_font_family: Optional[str] = None
    base_font_size: int = 10


def _mk_palette(bg: str, fg: str, base: str, text: str, highlight: str) -> QPalette:
    def _role(name: str) -> Any:
        role_enum = getattr(QPalette, "ColorRole", None)
        if role_enum is not None and hasattr(role_enum, name):
            return getattr(role_enum, name)
        return getattr(QPalette, name)

    p = QPalette()
    p.setColor(cast(Any, _role("Window")), QColor(bg))
    p.setColor(cast(Any, _role("WindowText")), QColor(fg))
    p.setColor(cast(Any, _role("Base")), QColor(base))
    p.setColor(cast(Any, _role("AlternateBase")), QColor(bg))
    p.setColor(cast(Any, _role("Text")), QColor(text))
    p.setColor(cast(Any, _role("Button")), QColor(bg))
    p.setColor(cast(Any, _role("ButtonText")), QColor(fg))
    p.setColor(cast(Any, _role("Highlight")), QColor(highlight))
    p.setColor(cast(Any, _role("HighlightedText")), QColor("#ffffff"))
    p.setColor(cast(Any, _role("ToolTipBase")), QColor(base))
    p.setColor(cast(Any, _role("ToolTipText")), QColor(text))
    return p


# ---------- QSS helpers ----------

def _qss_base(radius: int = 10, padding: int = 8) -> str:
    return f"""
    * {{
        font-size: 10pt;
    }}
    QWidget {{
        border: none;
    }}

    /* Inputs */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        border-radius: {radius}px;
        padding: {padding}px;
        border: 1px solid rgba(127,127,127,0.35);
    }}
    QComboBox::drop-down {{
        border: none;
        width: 26px;
    }}

    /* Buttons */
    QPushButton {{
        border-radius: {radius}px;
        padding: {padding}px 14px;
        font-weight: 600;
    }}
    QPushButton:disabled {{
        opacity: 0.55;
    }}

    /* Grouping */
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

    /* Tables */
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

    /* Scrollbar */
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

    /* Toolbars / top bars */
    QToolBar {{
        spacing: 8px;
        padding: 6px;
    }}
    """


THEMES: Dict[str, Theme] = {}

# ---------- Modern Light ----------
THEMES["modern_light"] = Theme(
    key="modern_light",
    name="Modern Light",
    palette=_mk_palette(bg="#f7f7fb", fg="#12131a", base="#ffffff", text="#12131a", highlight="#2b7cff"),
    qss=_qss_base(radius=10, padding=8) + r"""
    QWidget { background: #f7f7fb; color: #12131a; }
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #ffffff; }

    QPushButton { background: #2b7cff; color: white; }
    QPushButton:hover { background: #1f6ef5; }
    QPushButton:pressed { background: #1b5fce; }

    /* Secondary button */
    QPushButton#secondary { background: rgba(18,19,26,0.06); color: #12131a; }
    QPushButton#secondary:hover { background: rgba(18,19,26,0.10); }

    /* Danger */
    QPushButton#danger { background: #e5484d; color: white; }
    QPushButton#danger:hover { background: #d63e43; }

    QHeaderView::section { background: rgba(18,19,26,0.04); }
    QGroupBox { background: rgba(255,255,255,0.55); }
    """,
)

# ---------- Modern Dark ----------
THEMES["modern_dark"] = Theme(
    key="modern_dark",
    name="Modern Dark",
    palette=_mk_palette(bg="#0f1115", fg="#e8eaf0", base="#141821", text="#e8eaf0", highlight="#7c5cff"),
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
)

# ---------- Retro Neon ----------
THEMES["retro_neon"] = Theme(
    key="retro_neon",
    name="Retro Neon",
    palette=_mk_palette(bg="#0b0f14", fg="#d8faff", base="#0f1620", text="#d8faff", highlight="#00f5d4"),
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

    QPushButton#danger {
        background: #ff4d4f; color: #0b0f14;
        border: 1px solid rgba(255,77,79,0.75);
    }

    QGroupBox {
        background: rgba(0,245,212,0.06);
        border: 1px solid rgba(0,245,212,0.25);
    }
    QHeaderView::section {
        background: rgba(255,43,214,0.10);
        border-bottom: 1px solid rgba(0,245,212,0.25);
    }
    QTableView {
        background: #0f1620;
        border: 1px solid rgba(0,245,212,0.25);
        selection-background-color: rgba(0,245,212,0.25);
        selection-color: #d8faff;
    }
    """,
    base_font_family=None,
)

# ---------- Nord Frost ----------
THEMES["nord_frost"] = Theme(
    key="nord_frost",
    name="Nord Frost",
    palette=_mk_palette(bg="#2e3440", fg="#eceff4", base="#3b4252", text="#eceff4", highlight="#88c0d0"),
    qss=_qss_base(radius=12, padding=9) + r"""
    QWidget { background: #2e3440; color: #eceff4; }
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
        background: #3b4252;
        border: 1px solid rgba(236,239,244,0.14);
    }
    QPushButton { background: #88c0d0; color: #2e3440; }
    QPushButton:hover { background: #7fb6c7; }
    QPushButton#secondary { background: rgba(236,239,244,0.08); color: #eceff4; }
    QPushButton#danger { background: #bf616a; color: #2e3440; }

    QGroupBox { background: rgba(59,66,82,0.55); border: 1px solid rgba(236,239,244,0.10); }
    QHeaderView::section { background: rgba(236,239,244,0.06); }
    """,
)

# ---------- Solar Light ----------
THEMES["solar_light"] = Theme(
    key="solar_light",
    name="Solar Light",
    palette=_mk_palette(bg="#fff7e6", fg="#2b1b0e", base="#ffffff", text="#2b1b0e", highlight="#ff8f00"),
    qss=_qss_base(radius=10, padding=8) + r"""
    QWidget { background: #fff7e6; color: #2b1b0e; }
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #ffffff; }

    QPushButton { background: #ff8f00; color: #2b1b0e; }
    QPushButton:hover { background: #f08600; }
    QPushButton#secondary { background: rgba(43,27,14,0.06); color: #2b1b0e; }
    QPushButton#danger { background: #d32f2f; color: white; }

    QGroupBox { background: rgba(255,255,255,0.55); }
    QHeaderView::section { background: rgba(43,27,14,0.04); }
    """,
)

# --- CRT Green (Terminal/CRT Look) ---
THEMES["crt_green"] = Theme(
    key="crt_green",
    name="CRT Green",
    palette=_mk_palette(bg="#06110b", fg="#b6ffb6", base="#07160e", text="#b6ffb6", highlight="#39ff14"),
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

    QLabel {
        color: #b6ffb6;
    }
    """,
)

# --- GameBoy DMG (classic grey-green handheld vibe) ---
THEMES["gameboy_dmg"] = Theme(
    key="gameboy_dmg",
    name="GameBoy DMG",
    palette=_mk_palette(bg="#d6d2c4", fg="#1f2a1f", base="#c8ccb8", text="#1f2a1f", highlight="#5b7f3a"),
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

    QPushButton#secondary {
        background: #c0c0ba;
    }

    QPushButton#danger {
        background: #7a2c2c;
        color: #f3e7e7;
        border: 2px solid rgba(31,42,31,0.25);
    }
    QPushButton#danger:hover { background: #6c2626; }
    """,
)


class ThemeManager:
    def __init__(self, app: QApplication):
        self.app = app
        self.current_key: str = "modern_light"

    def available(self) -> Dict[str, Theme]:
        return THEMES

    def apply(self, key: str) -> None:
        theme = THEMES.get(key, THEMES["modern_light"])
        self.current_key = theme.key

        if theme.palette is not None:
            self.app.setPalette(theme.palette)

        if theme.base_font_family:
            f = self.app.font()
            f.setFamily(theme.base_font_family)
            f.setPointSize(theme.base_font_size)
            self.app.setFont(f)

        self.app.setStyleSheet(theme.qss)
