"""Optional Qt shell layouts.

Layouts are built lazily to avoid Qt import errors during tests.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
from typing import Any, Callable, Optional

from .assets import ICONS, label


def _try_import_qt():
	for base in ("PySide6", "PyQt5"):
		try:
			QtWidgets = importlib.import_module(f"{base}.QtWidgets")
			QtCore = importlib.import_module(f"{base}.QtCore")
			return QtWidgets, QtCore
		except Exception:
			continue
	return None, None


@dataclass(frozen=True)
class LayoutContext:
	pages: dict[str, object]
	on_action_scan: Optional[Callable[[], None]] = None
	on_action_preview: Optional[Callable[[], None]] = None
	on_action_execute: Optional[Callable[[], None]] = None
	on_action_cancel: Optional[Callable[[], None]] = None
	layout_combo: Optional[object] = None


@dataclass(frozen=True)
class LayoutSpec:
	key: str
	name: str
	description: str
	builder: Callable[[LayoutContext], object]


def _make_action_bar(ctx: LayoutContext, QtWidgets) -> object:
	bar = QtWidgets.QHBoxLayout()
	title = QtWidgets.QLabel("ROM Sorter Pro")
	title.setStyleSheet("font-size: 15px; font-weight: 600;")
	bar.addWidget(title)
	bar.addStretch(1)

	def _add_btn(text: str, handler: Optional[Callable[[], None]], object_name: Optional[str] = None) -> None:
		btn = QtWidgets.QPushButton(text)
		if object_name:
			btn.setObjectName(object_name)
		if handler is not None:
			btn.clicked.connect(handler)
		bar.addWidget(btn)

	_add_btn(label("Scan", "scan"), ctx.on_action_scan)
	_add_btn(label("Preview", "preview"), ctx.on_action_preview, "secondary")
	_add_btn(label("Execute", "execute"), ctx.on_action_execute)
	_add_btn(label("Cancel", "cancel"), ctx.on_action_cancel, "danger")

	if ctx.layout_combo is not None:
		bar.addSpacing(8)
		bar.addWidget(QtWidgets.QLabel("Layout:"))
		bar.addWidget(ctx.layout_combo)

	return bar


def _build_modern_glass_ops(ctx: LayoutContext) -> object:
	QtWidgets, QtCore = _try_import_qt()
	if QtWidgets is None:
		raise RuntimeError("Qt not available")
	root = QtWidgets.QWidget()
	outer = QtWidgets.QVBoxLayout(root)
	outer.setContentsMargins(12, 12, 12, 12)
	outer.setSpacing(10)

	toolbar = QtWidgets.QFrame()
	toolbar_layout = QtWidgets.QHBoxLayout(toolbar)
	toolbar_layout.setContentsMargins(10, 10, 10, 10)
	brand = QtWidgets.QLabel("ROM Sorter Pro")
	brand.setStyleSheet("font-size: 16px; font-weight: 700;")
	toolbar_layout.addWidget(brand)
	toolbar_layout.addStretch(1)
	for text, key, handler, name in (
		("Scan", "scan", ctx.on_action_scan, None),
		("Preview", "preview", ctx.on_action_preview, "secondary"),
		("Execute", "execute", ctx.on_action_execute, None),
		("Cancel", "cancel", ctx.on_action_cancel, "danger"),
	):
		btn = QtWidgets.QPushButton(label(text, key))
		if name:
			btn.setObjectName(name)
		if handler is not None:
			btn.clicked.connect(handler)
		toolbar_layout.addWidget(btn)
	outer.addWidget(toolbar)

	cards = QtWidgets.QFrame()
	cards_layout = QtWidgets.QHBoxLayout(cards)
	cards_layout.setContentsMargins(0, 0, 0, 0)
	cards_layout.setSpacing(10)
	cards.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

	def _glass_card(step: str, title: str, subtitle: str, icon_key: str) -> Any:
		card = QtWidgets.QFrame()
		card.setObjectName("wizard_card")
		layout = QtWidgets.QVBoxLayout(card)
		layout.setContentsMargins(16, 16, 16, 16)
		layout.setSpacing(8)
		header = QtWidgets.QHBoxLayout()
		label_step = QtWidgets.QLabel(step)
		label_step.setObjectName("wizard_step")
		header.addWidget(label_step)
		header.addStretch(1)
		icon = QtWidgets.QLabel(ICONS.get(icon_key, ""))
		icon.setObjectName("wizard_icon")
		header.addWidget(icon)
		layout.addLayout(header)
		label_title = QtWidgets.QLabel(title)
		label_title.setObjectName("wizard_title")
		layout.addWidget(label_title)
		label_sub = QtWidgets.QLabel(subtitle)
		label_sub.setObjectName("wizard_subtitle")
		label_sub.setWordWrap(True)
		layout.addWidget(label_sub)
		layout.addStretch(1)
		return card

	cards_layout.addWidget(_glass_card("1", "Choose Source", "Quelle auswählen", "folder"), 1)
	cards_layout.addWidget(_glass_card("2", "Choose Destination", "Ziel festlegen", "folder"), 1)
	cards_layout.addWidget(_glass_card("3", "Scan", "Erfassung starten", "scan"), 1)
	cards_layout.addWidget(_glass_card("4", "Preview", "Dry-run prüfen", "preview"), 1)
	cards_layout.addWidget(_glass_card("5", "Execute", "Sortierung ausführen", "execute"), 1)
	outer.addWidget(cards)

	content = QtWidgets.QSplitter()
	if QtCore is not None:
		content.setOrientation(QtCore.Qt.Horizontal)
	left = QtWidgets.QListWidget()
	left.setMinimumWidth(200)
	stack = QtWidgets.QStackedWidget()
	for name, widget in ctx.pages.items():
		left.addItem(name)
		stack.addWidget(widget)
	if left.count():
		left.setCurrentRow(0)
	left.currentRowChanged.connect(stack.setCurrentIndex)
	content.addWidget(left)
	content.addWidget(stack)
	content.setStretchFactor(1, 1)
	outer.addWidget(content, 1)
	return root


def _build_mission_control(ctx: LayoutContext) -> object:
	QtWidgets, QtCore = _try_import_qt()
	if QtWidgets is None:
		raise RuntimeError("Qt not available")
	root = QtWidgets.QWidget()
	outer = QtWidgets.QVBoxLayout(root)
	outer.setContentsMargins(12, 12, 12, 12)
	outer.setSpacing(10)

	bar = QtWidgets.QFrame()
	bar_layout = QtWidgets.QHBoxLayout(bar)
	bar_layout.setContentsMargins(10, 10, 10, 10)
	brand = QtWidgets.QLabel("ROM Sorter Pro")
	brand.setStyleSheet("font-size: 16px; font-weight: 700;")
	bar_layout.addWidget(brand)
	bar_layout.addStretch(1)
	for text, key, handler, name in (
		("Scan", "scan", ctx.on_action_scan, None),
		("Preview", "preview", ctx.on_action_preview, "secondary"),
		("Execute", "execute", ctx.on_action_execute, None),
		("Cancel", "cancel", ctx.on_action_cancel, "danger"),
	):
		btn = QtWidgets.QPushButton(label(text, key))
		if name:
			btn.setObjectName(name)
		if handler is not None:
			btn.clicked.connect(handler)
		bar_layout.addWidget(btn)
	outer.addWidget(bar)

	split = QtWidgets.QSplitter()
	if QtCore is not None:
		split.setOrientation(QtCore.Qt.Horizontal)
	left = QtWidgets.QTabWidget()
	for name, widget in ctx.pages.items():
		left.addTab(widget, name)
	left.setDocumentMode(True)

	right = QtWidgets.QFrame()
	right.setObjectName("wizard_card")
	right_layout = QtWidgets.QVBoxLayout(right)
	right_layout.setContentsMargins(12, 12, 12, 12)
	right_layout.setSpacing(8)
	panel_title = QtWidgets.QLabel("Details")
	panel_title.setStyleSheet("font-weight: 700;")
	right_layout.addWidget(panel_title)
	for label_text in ("Hash", "Region", "Language", "Matched DAT", "Confidence"):
		row = QtWidgets.QHBoxLayout()
		row.addWidget(QtWidgets.QLabel(label_text + ":"))
		value = QtWidgets.QLabel("—")
		value.setStyleSheet("opacity: 0.7;")
		row.addStretch(1)
		row.addWidget(value)
		right_layout.addLayout(row)

	split.addWidget(left)
	split.addWidget(right)
	split.setStretchFactor(0, 1)
	outer.addWidget(split, 1)
	return root


def _build_beginner_wizard(ctx: LayoutContext) -> object:
	QtWidgets, QtCore = _try_import_qt()
	if QtWidgets is None:
		raise RuntimeError("Qt not available")
	root = QtWidgets.QWidget()
	outer = QtWidgets.QVBoxLayout(root)
	outer.setContentsMargins(12, 12, 12, 12)
	outer.setSpacing(10)

	content = QtWidgets.QSplitter()
	if QtCore is not None:
		content.setOrientation(QtCore.Qt.Horizontal)
	nav = QtWidgets.QListWidget()
	nav.setProperty("ui_base_min_width", 200)
	nav.setMinimumWidth(200)
	stack = QtWidgets.QStackedWidget()
	for name, widget in ctx.pages.items():
		nav.addItem(name)
		stack.addWidget(widget)
	if nav.count():
		nav.setCurrentRow(0)
	nav.currentRowChanged.connect(stack.setCurrentIndex)
	content.addWidget(nav)
	content.addWidget(stack)
	content.setStretchFactor(1, 1)
	outer.addWidget(content, 1)
	return root


LAYOUTS = {
	"beginner_wizard": LayoutSpec(
		key="beginner_wizard",
		name="Beginner Wizard",
		description="Step-by-step onboarding layout.",
		builder=_build_beginner_wizard,
	),
}

__all__ = ["LayoutContext", "LayoutSpec", "LAYOUTS"]
