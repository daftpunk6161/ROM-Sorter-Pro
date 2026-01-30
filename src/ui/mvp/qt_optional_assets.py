"""Optional Qt assets loader for MVP Qt UI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any


@dataclass(frozen=True)
class QtOptionalAssets:
    label: Callable[[str, str], str]
    layouts: Dict[str, Any]
    qt_palette_theme_manager: Optional[type]
    qt_palette_themes: Dict[str, Any]
    ui_shell_controller: Optional[type]
    shell_theme_manager: Optional[type]


def _fallback_label(text: str, _icon_key: str) -> str:
    return text


def load_optional_qt_assets(logger: logging.Logger) -> QtOptionalAssets:
    label_fn: Callable[[str, str], str] = _fallback_label
    layouts: Dict[str, Any] = {}
    qt_palette_theme_manager: Optional[type] = None
    qt_palette_themes: Dict[str, Any] = {}
    ui_shell_controller: Optional[type] = None
    shell_theme_manager: Optional[type] = None

    try:
        from ...ui.qt.assets import label as qt_label

        label_fn = qt_label
    except Exception as exc:
        logger.debug("Optional Qt assets import failed: %s", exc)

    try:
        from ...ui.qt.layouts import LAYOUTS as qt_layouts

        layouts = qt_layouts
    except Exception as exc:
        logger.debug("Optional Qt layouts import failed: %s", exc)

    try:
        from ...ui.qt.themes import ThemeManager as QtPaletteThemeManager, THEMES as QT_PALETTE_THEMES

        qt_palette_theme_manager = QtPaletteThemeManager
        qt_palette_themes = QT_PALETTE_THEMES
    except Exception as exc:
        logger.debug("Optional Qt themes import failed: %s", exc)

    try:
        from ...ui.qt.shell import UIShellController
        from ...ui.qt.themes import ThemeManager as ShellThemeManager

        ui_shell_controller = UIShellController
        shell_theme_manager = ShellThemeManager
    except Exception as exc:
        logger.debug("Optional Qt shell import failed: %s", exc)

    return QtOptionalAssets(
        label=label_fn,
        layouts=layouts,
        qt_palette_theme_manager=qt_palette_theme_manager,
        qt_palette_themes=qt_palette_themes,
        ui_shell_controller=ui_shell_controller,
        shell_theme_manager=shell_theme_manager,
    )
