from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, cast

try:
    from PySide6.QtCore import Qt, Signal  # noqa: F401
    from PySide6.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QFrame,
        QLabel,
        QPushButton,
        QComboBox,
        QStackedWidget,
        QListWidget,
        QSplitter,
        QLineEdit,
        QTabWidget,
    )
except Exception:
    from PyQt5.QtCore import Qt, pyqtSignal as Signal  # noqa: F401
    from PyQt5.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QFrame,
        QLabel,
        QPushButton,
        QComboBox,
        QStackedWidget,
        QListWidget,
        QSplitter,
        QLineEdit,
        QTabWidget,
    )

from .assets import label


@dataclass(frozen=True)
class LayoutSpec:
    key: str
    name: str
    builder: Callable[..., QWidget]


def _card(title: str, subtitle: str = "") -> QFrame:
    c = QFrame()
    c.setObjectName("card")
    lay = QVBoxLayout(c)
    lay.setContentsMargins(14, 14, 14, 14)
    lay.setSpacing(6)

    t = QLabel(title)
    t.setStyleSheet("font-size: 14pt; font-weight: 800;")
    lay.addWidget(t)

    if subtitle:
        s = QLabel(subtitle)
        s.setStyleSheet("opacity: 0.75;")
        lay.addWidget(s)

    return c


def _set_horizontal(splitter: QSplitter) -> None:
    orient = getattr(Qt, "Horizontal", None)
    if orient is None:
        orient = getattr(getattr(Qt, "Orientation", None), "Horizontal", None)
    splitter.setOrientation(cast(Any, orient or 1))


def _add_to_card(card: QFrame, widget: QWidget) -> None:
    layout = card.layout()
    if layout is not None:
        layout.addWidget(widget)


def build_shell_classic_tabs(
    pages: Dict[str, Any],
    on_action_scan: Callable[[], None],
    on_action_preview: Callable[[], None],
    on_action_execute: Callable[[], None],
    on_action_cancel: Callable[[], None],
    theme_combo: Any,
    layout_combo: Any,
) -> QWidget:
    root = QWidget()
    outer = QVBoxLayout(root)
    outer.setContentsMargins(12, 12, 12, 12)
    outer.setSpacing(10)

    top = QFrame()
    top_l = QHBoxLayout(top)
    top_l.setContentsMargins(8, 8, 8, 8)
    top_l.setSpacing(8)

    brand = QLabel("ROM Sorter Pro")
    brand.setStyleSheet("font-size: 16pt; font-weight: 900;")
    top_l.addWidget(brand)
    top_l.addSpacing(10)

    btn_scan = QPushButton(label("Scan", "scan"))
    btn_scan.clicked.connect(on_action_scan)
    top_l.addWidget(btn_scan)

    btn_prev = QPushButton(label("Preview", "preview"))
    btn_prev.setObjectName("secondary")
    btn_prev.clicked.connect(on_action_preview)
    top_l.addWidget(btn_prev)

    btn_exec = QPushButton(label("Execute", "execute"))
    btn_exec.setObjectName("primary")
    btn_exec.clicked.connect(on_action_execute)
    top_l.addWidget(btn_exec)

    btn_cancel = QPushButton(label("Cancel", "cancel"))
    btn_cancel.setObjectName("danger")
    btn_cancel.clicked.connect(on_action_cancel)
    top_l.addWidget(btn_cancel)

    top_l.addStretch(1)
    top_l.addWidget(QLabel("Theme:"))
    top_l.addWidget(theme_combo)
    top_l.addWidget(QLabel("Layout:"))
    top_l.addWidget(layout_combo)

    outer.addWidget(top)

    tabs = QTabWidget()
    for k, widget in pages.items():
        tabs.addTab(widget, str(k))
    outer.addWidget(tabs, 1)
    return root


def build_shell_sidebar_pages(
    pages: Dict[str, Any],
    on_action_scan: Callable[[], None],
    on_action_preview: Callable[[], None],
    on_action_execute: Callable[[], None],
    on_action_cancel: Callable[[], None],
    theme_combo: Any,
    layout_combo: Any,
) -> QWidget:
    root = QWidget()
    outer = QVBoxLayout(root)
    outer.setContentsMargins(12, 12, 12, 12)
    outer.setSpacing(10)

    top = QFrame()
    top_l = QHBoxLayout(top)
    top_l.setContentsMargins(8, 8, 8, 8)
    top_l.setSpacing(8)

    brand = QLabel("ROM Sorter Pro")
    brand.setStyleSheet("font-size: 16pt; font-weight: 900;")
    top_l.addWidget(brand)
    top_l.addStretch(1)
    top_l.addWidget(QLabel("Theme:"))
    top_l.addWidget(theme_combo)
    top_l.addWidget(QLabel("Layout:"))
    top_l.addWidget(layout_combo)
    outer.addWidget(top)

    main = QSplitter()
    _set_horizontal(main)

    sidebar = QFrame()
    sidebar.setMinimumWidth(210)
    s_l = QVBoxLayout(sidebar)
    s_l.setContentsMargins(8, 8, 8, 8)
    s_l.setSpacing(10)

    nav = QListWidget()
    nav.setSpacing(4)
    s_l.addWidget(nav, 1)

    stack = QStackedWidget()

    keys = list(pages.keys())
    for k in keys:
        nav.addItem(str(k))
        stack.addWidget(pages[k])

    nav.setCurrentRow(0)
    nav.currentRowChanged.connect(stack.setCurrentIndex)

    main.addWidget(sidebar)
    main.addWidget(stack)
    main.setStretchFactor(1, 1)

    outer.addWidget(main, 1)
    return root


def build_shell_sidebar_commandbar(
    pages: Dict[str, Any],
    on_action_scan: Callable[[], None],
    on_action_preview: Callable[[], None],
    on_action_execute: Callable[[], None],
    on_action_cancel: Callable[[], None],
    theme_combo: Any,
    layout_combo: Any,
) -> QWidget:
    root = QWidget()
    outer = QVBoxLayout(root)
    outer.setContentsMargins(12, 12, 12, 12)
    outer.setSpacing(10)

    top = QFrame()
    top_l = QHBoxLayout(top)
    top_l.setContentsMargins(8, 8, 8, 8)
    top_l.setSpacing(8)

    brand = QLabel("ROM Sorter Pro")
    brand.setStyleSheet("font-size: 16pt; font-weight: 900;")
    top_l.addWidget(brand)

    top_l.addSpacing(12)

    btn_scan = QPushButton(label("Scan", "scan"))
    btn_scan.clicked.connect(on_action_scan)
    top_l.addWidget(btn_scan)

    btn_prev = QPushButton(label("Preview", "preview"))
    btn_prev.setObjectName("secondary")
    btn_prev.clicked.connect(on_action_preview)
    top_l.addWidget(btn_prev)

    btn_exec = QPushButton(label("Execute", "execute"))
    btn_exec.setObjectName("primary")
    btn_exec.clicked.connect(on_action_execute)
    top_l.addWidget(btn_exec)

    btn_cancel = QPushButton(label("Cancel", "cancel"))
    btn_cancel.setObjectName("danger")
    btn_cancel.clicked.connect(on_action_cancel)
    top_l.addWidget(btn_cancel)

    top_l.addStretch(1)

    top_l.addWidget(QLabel("Theme:"))
    top_l.addWidget(theme_combo)
    top_l.addWidget(QLabel("Layout:"))
    top_l.addWidget(layout_combo)

    outer.addWidget(top)

    main = QSplitter()
    _set_horizontal(main)

    sidebar = QFrame()
    sidebar.setMinimumWidth(210)
    s_l = QVBoxLayout(sidebar)
    s_l.setContentsMargins(8, 8, 8, 8)
    s_l.setSpacing(10)

    search = QLineEdit()
    search.setPlaceholderText("Suche Feature…")
    s_l.addWidget(search)

    nav = QListWidget()
    nav.setSpacing(4)
    s_l.addWidget(nav, 1)

    stack = QStackedWidget()

    keys = list(pages.keys())
    for k in keys:
        nav.addItem(str(k))
        stack.addWidget(pages[k])

    nav.setCurrentRow(0)

    def _filter(text: str) -> None:
        t = text.lower().strip()
        for i in range(nav.count()):
            it = nav.item(i)
            if it is not None:
                it.setHidden(t not in it.text().lower())

    search.textChanged.connect(_filter)
    nav.currentRowChanged.connect(stack.setCurrentIndex)

    main.addWidget(sidebar)
    main.addWidget(stack)
    main.setStretchFactor(1, 1)

    outer.addWidget(main, 1)
    return root


def build_shell_stepper_wizard(
    pages: Dict[str, Any],
    on_action_scan: Callable[[], None],
    on_action_preview: Callable[[], None],
    on_action_execute: Callable[[], None],
    on_action_cancel: Callable[[], None],
    theme_combo: Any,
    layout_combo: Any,
) -> QWidget:
    root = QWidget()
    outer = QVBoxLayout(root)
    outer.setContentsMargins(12, 12, 12, 12)
    outer.setSpacing(10)

    header = QFrame()
    h = QHBoxLayout(header)
    h.setContentsMargins(10, 10, 10, 10)
    h.setSpacing(10)

    title = QLabel("Workflow")
    title.setStyleSheet("font-size: 16pt; font-weight: 900;")
    h.addWidget(title)

    step = QLabel("1) Scan   →   2) Preview/Plan   →   3) Execute")
    step.setStyleSheet("font-size: 11pt; font-weight: 700; opacity: 0.8;")
    h.addWidget(step)
    h.addStretch(1)

    h.addWidget(QLabel("Theme:"))
    h.addWidget(theme_combo)
    h.addWidget(QLabel("Layout:"))
    h.addWidget(layout_combo)
    outer.addWidget(header)

    actions = QFrame()
    a = QHBoxLayout(actions)
    a.setContentsMargins(10, 10, 10, 10)
    a.setSpacing(10)

    b1 = QPushButton(label("Scan (1)", "scan"))
    b1.clicked.connect(on_action_scan)
    a.addWidget(b1)

    b2 = QPushButton(label("Preview/Plan (2)", "preview"))
    b2.setObjectName("secondary")
    b2.clicked.connect(on_action_preview)
    a.addWidget(b2)

    b3 = QPushButton(label("Execute (3)", "execute"))
    b3.setObjectName("primary")
    b3.clicked.connect(on_action_execute)
    a.addWidget(b3)

    b4 = QPushButton(label("Cancel", "cancel"))
    b4.setObjectName("danger")
    b4.clicked.connect(on_action_cancel)
    a.addWidget(b4)

    a.addStretch(1)
    outer.addWidget(actions)

    split = QSplitter()
    _set_horizontal(split)

    step_stack = QStackedWidget()
    ordered = []
    for k in ("Dashboard", "Sortierung", "Konvertierungen", "IGIR"):
        if k in pages:
            ordered.append(k)
    for k in pages.keys():
        if k not in ordered:
            ordered.append(k)

    for k in ordered:
        step_stack.addWidget(pages[k])

    nav_frame = QFrame()
    nv = QVBoxLayout(nav_frame)
    nv.setContentsMargins(8, 8, 8, 8)
    nv.setSpacing(8)

    nav_lbl = QLabel("Bereiche")
    nav_lbl.setStyleSheet("font-weight: 800;")
    nv.addWidget(nav_lbl)

    nav = QListWidget()
    for k in ordered:
        nav.addItem(str(k))
    nav.setCurrentRow(0)
    nav.currentRowChanged.connect(step_stack.setCurrentIndex)
    nv.addWidget(nav, 1)

    split.addWidget(step_stack)
    split.addWidget(nav_frame)
    split.setStretchFactor(0, 1)
    outer.addWidget(split, 1)

    return root


def build_shell_dashboard_cards(
    pages: Dict[str, Any],
    on_action_scan: Callable[[], None],
    on_action_preview: Callable[[], None],
    on_action_execute: Callable[[], None],
    on_action_cancel: Callable[[], None],
    theme_combo: Any,
    layout_combo: Any,
) -> QWidget:
    root = QWidget()
    outer = QVBoxLayout(root)
    outer.setContentsMargins(12, 12, 12, 12)
    outer.setSpacing(10)

    top = QFrame()
    tl = QHBoxLayout(top)
    tl.setContentsMargins(10, 10, 10, 10)
    tl.setSpacing(10)

    brand = QLabel("ROM Sorter Pro")
    brand.setStyleSheet("font-size: 18pt; font-weight: 950;")
    tl.addWidget(brand)
    tl.addStretch(1)

    tl.addWidget(QLabel("Theme:"))
    tl.addWidget(theme_combo)
    tl.addWidget(QLabel("Layout:"))
    tl.addWidget(layout_combo)
    outer.addWidget(top)

    cards = QFrame()
    cl = QHBoxLayout(cards)
    cl.setContentsMargins(0, 0, 0, 0)
    cl.setSpacing(10)

    c1 = _card("Scan", "ROMs analysieren, Konsole erkennen")
    c2 = _card("Preview", "Plan anzeigen (Dry-run), keine Writes")
    c3 = _card("Execute", "Plan ausführen + Report erzeugen")

    b1 = QPushButton(label("Scan", "scan"))
    b1.clicked.connect(on_action_scan)
    _add_to_card(c1, b1)

    b2 = QPushButton(label("Preview", "preview"))
    b2.setObjectName("secondary")
    b2.clicked.connect(on_action_preview)
    _add_to_card(c2, b2)

    b3 = QPushButton(label("Execute", "execute"))
    b3.setObjectName("primary")
    b3.clicked.connect(on_action_execute)
    _add_to_card(c3, b3)

    cl.addWidget(cast(Any, c1), 1)
    cl.addWidget(cast(Any, c2), 1)
    cl.addWidget(cast(Any, c3), 1)

    cancel = QPushButton(label("Cancel / Stop", "cancel"))
    cancel.setObjectName("danger")
    cancel.clicked.connect(on_action_cancel)
    cl.addWidget(cancel)

    outer.addWidget(cards)

    content = QSplitter()
    _set_horizontal(content)

    nav = QListWidget()
    nav.setMinimumWidth(220)
    stack = QStackedWidget()

    keys = list(pages.keys())
    for k in keys:
        nav.addItem(str(k))
        stack.addWidget(pages[k])
    nav.setCurrentRow(0)
    nav.currentRowChanged.connect(stack.setCurrentIndex)

    content.addWidget(nav)
    content.addWidget(stack)
    content.setStretchFactor(1, 1)

    outer.addWidget(content, 1)

    return root


LAYOUTS: Dict[str, LayoutSpec] = {
    "classic_tabs": LayoutSpec("classic_tabs", "Classic Tabs", build_shell_classic_tabs),
    "sidebar_pages": LayoutSpec("sidebar_pages", "Sidebar + Pages", build_shell_sidebar_pages),
    "sidebar_cmd": LayoutSpec("sidebar_cmd", "Command Bar", build_shell_sidebar_commandbar),
    "stepper": LayoutSpec("stepper", "Stepper / Wizard Flow", build_shell_stepper_wizard),
    "dashboard": LayoutSpec("dashboard", "Dashboard Cards", build_shell_dashboard_cards),
}
