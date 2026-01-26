from __future__ import annotations

from typing import Dict, Callable

try:
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QWidget, QComboBox
except Exception:
    from PyQt5.QtCore import QSettings
    from PyQt5.QtWidgets import QWidget, QComboBox

from .themes import ThemeManager
from .layouts import LAYOUTS


class UIShellController:
    """Hält Theme/Layout Auswahl und baut Root-Widget neu, ohne App Neustart."""

    def __init__(
        self,
        theme_mgr: ThemeManager,
        pages: Dict[str, QWidget],
        on_action_scan: Callable[[], None],
        on_action_preview: Callable[[], None],
        on_action_execute: Callable[[], None],
        on_action_cancel: Callable[[], None],
    ):
        self.theme_mgr = theme_mgr
        self.pages = pages
        self.on_action_scan = on_action_scan
        self.on_action_preview = on_action_preview
        self.on_action_execute = on_action_execute
        self.on_action_cancel = on_action_cancel

        self.settings = QSettings("ROM-Sorter-Pro", "ROM-Sorter-Pro")
        self.theme_key = self._as_str(self.settings.value("ui/theme", "modern_light"), "modern_light")
        self.layout_key = self._as_str(self.settings.value("ui/layout", "sidebar_cmd"), "sidebar_cmd")

        self.theme_combo = QComboBox()
        for k, t in self.theme_mgr.available().items():
            self.theme_combo.addItem(t.name, k)

        self.layout_combo = QComboBox()
        for k, spec in LAYOUTS.items():
            self.layout_combo.addItem(spec.name, k)

        self._select_combo(self.theme_combo, self.theme_key)
        self._select_combo(self.layout_combo, self.layout_key)

        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self.layout_combo.currentIndexChanged.connect(self._on_layout_changed)

        self.theme_mgr.apply(self.theme_key)

    def _as_str(self, value: object, fallback: str) -> str:
        if value is None:
            return fallback
        text = str(value).strip()
        return text or fallback

    def _select_combo(self, combo: QComboBox, key: str) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == key:
                combo.setCurrentIndex(i)
                return

    def _on_theme_changed(self, idx: int) -> None:
        key = self._as_str(self.theme_combo.itemData(idx), "modern_light")
        self.theme_key = key
        self.settings.setValue("ui/theme", key)
        self.theme_mgr.apply(key)

    def _on_layout_changed(self, idx: int) -> None:
        key = self._as_str(self.layout_combo.itemData(idx), "sidebar_cmd")
        self.layout_key = key
        self.settings.setValue("ui/layout", key)

    def build_root(self) -> QWidget:
        spec = LAYOUTS.get(self.layout_key, LAYOUTS["sidebar_cmd"])
        return spec.builder(
            pages=self.pages,
            on_action_scan=self.on_action_scan,
            on_action_preview=self.on_action_preview,
            on_action_execute=self.on_action_execute,
            on_action_cancel=self.on_action_cancel,
            theme_combo=self.theme_combo,
            layout_combo=self.layout_combo,
        )
