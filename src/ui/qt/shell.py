"""Optional Qt shell controller for alternate layouts.

This module avoids importing Qt at import time to keep tests stable.
"""

from __future__ import annotations

import importlib
from typing import Any, Callable, Optional, cast

from .layouts import LAYOUTS, LayoutContext


def _try_import_qt():
	for base in ("PySide6", "PyQt5"):
		try:
			QtWidgets = importlib.import_module(f"{base}.QtWidgets")
			QtCore = importlib.import_module(f"{base}.QtCore")
			return QtWidgets, QtCore
		except Exception:
			continue
	return None, None


class UIShellController:
	def __init__(
		self,
		*,
		theme_mgr: Optional[object],
		pages: dict[str, Any],
		on_action_scan: Optional[Callable[[], None]] = None,
		on_action_preview: Optional[Callable[[], None]] = None,
		on_action_execute: Optional[Callable[[], None]] = None,
		on_action_cancel: Optional[Callable[[], None]] = None,
	) -> None:
		self.theme_mgr = theme_mgr
		self.pages = pages
		self.on_action_scan = on_action_scan
		self.on_action_preview = on_action_preview
		self.on_action_execute = on_action_execute
		self.on_action_cancel = on_action_cancel

		self.layout_combo: Optional[Any] = None
		self.layout_key = self._load_layout_key()
		self._init_layout_combo()

	def _load_layout_key(self) -> str:
		QtWidgets, QtCore = _try_import_qt()
		if QtCore is None:
			return "sidebar_cmd"
		try:
			setting = QtCore.QSettings("ROM-Sorter-Pro", "ROM-Sorter-Pro").value(
				"ui/layout", "sidebar_cmd"
			)
			key = str(setting).strip() if setting is not None else "sidebar_cmd"
		except Exception:
			key = "sidebar_cmd"
		return key if key in LAYOUTS else next(iter(LAYOUTS.keys()), "sidebar_cmd")

	def _save_layout_key(self, key: str) -> None:
		QtWidgets, QtCore = _try_import_qt()
		if QtCore is None:
			return
		try:
			QtCore.QSettings("ROM-Sorter-Pro", "ROM-Sorter-Pro").setValue("ui/layout", key)
		except Exception:
			return

	def _init_layout_combo(self) -> None:
		if not LAYOUTS:
			return
		QtWidgets, _QtCore = _try_import_qt()
		if QtWidgets is None:
			return
		combo = QtWidgets.QComboBox()
		for key, spec in LAYOUTS.items():
			combo.addItem(spec.name, key)
		idx = combo.findData(self.layout_key)
		combo.setCurrentIndex(idx if idx >= 0 else 0)
		combo.currentIndexChanged.connect(self._on_layout_changed)
		self.layout_combo = combo

	def set_layout_key(self, key: str) -> None:
		if not key:
			return
		if key not in LAYOUTS:
			return
		self.layout_key = key
		self._save_layout_key(key)
		combo = cast(Optional[Any], self.layout_combo)
		if combo is None:
			return
		try:
			idx = combo.findData(key)
			if idx >= 0 and combo.currentIndex() != idx:
				combo.setCurrentIndex(idx)
		except Exception:
			return

	def _on_layout_changed(self, idx: int) -> None:
		combo = cast(Optional[Any], self.layout_combo)
		if combo is None:
			return
		key = str(combo.itemData(idx) or "").strip()
		if not key:
			return
		self.layout_key = key
		self._save_layout_key(key)

	def build_root(self) -> Optional[object]:
		if not LAYOUTS:
			return None
		spec = LAYOUTS.get(self.layout_key) or next(iter(LAYOUTS.values()), None)
		if spec is None:
			return None
		context = LayoutContext(
			pages=self.pages,
			on_action_scan=self.on_action_scan,
			on_action_preview=self.on_action_preview,
			on_action_execute=self.on_action_execute,
			on_action_cancel=self.on_action_cancel,
			layout_combo=self.layout_combo,
		)
		try:
			return spec.builder(context)
		except Exception:
			return None


__all__ = ["UIShellController"]
