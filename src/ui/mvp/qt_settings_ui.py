"""Settings UI builder for MVP Qt UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class SettingsInputs:
    theme_combo: Any
    review_gate_checkbox: Any
    external_tools_checkbox: Any
    btn_open_overrides: Any
    tools_group: Any
    tools_status_hint: Any
    dat_status: Any
    btn_add_dat: Any
    btn_refresh_dat: Any
    btn_cancel_dat: Any
    btn_manage_dat: Any
    dat_auto_load_checkbox: Any
    btn_clear_dat_cache: Any
    db_status: Any
    btn_db_manager: Any


@dataclass(frozen=True)
class SettingsUI:
    layout_combo: Any
    log_visible_checkbox: Any
    remember_window_checkbox: Any
    drag_drop_checkbox: Any


def build_settings_ui(QtWidgets, QtCore, settings_layout, layouts: Dict[str, Any], inputs: SettingsInputs) -> SettingsUI:
    settings_intro = QtWidgets.QLabel(
        "Allgemeine Einstellungen. Weitere Optionen können später ergänzt werden."
    )
    settings_intro.setWordWrap(True)
    settings_layout.addWidget(settings_intro)

    general_group = QtWidgets.QGroupBox("Allgemein")
    general_layout = QtWidgets.QGridLayout(general_group)
    general_layout.setHorizontalSpacing(10)
    general_layout.setVerticalSpacing(6)

    general_layout.addWidget(QtWidgets.QLabel("Theme:"), 0, 0)
    general_layout.addWidget(inputs.theme_combo, 0, 1)

    layout_combo = None
    if layouts:
        layout_combo = QtWidgets.QComboBox()
        for key, spec in layouts.items():
            layout_combo.addItem(spec.name, key)
        try:
            layout_setting = QtCore.QSettings("ROM-Sorter-Pro", "ROM-Sorter-Pro").value("ui/layout", "sidebar_cmd")
            layout_key = str(layout_setting).strip() if layout_setting is not None else "sidebar_cmd"
        except Exception:
            layout_key = "sidebar_cmd"
        idx_layout = layout_combo.findData(layout_key)
        layout_combo.setCurrentIndex(idx_layout if idx_layout >= 0 else 0)
        general_layout.addWidget(QtWidgets.QLabel("Layout:"), 1, 0)
        general_layout.addWidget(layout_combo, 1, 1)
    general_layout.setColumnStretch(1, 1)

    log_visible_checkbox = QtWidgets.QCheckBox("Log standardmäßig anzeigen")
    remember_window_checkbox = QtWidgets.QCheckBox("Fenstergröße merken")
    drag_drop_checkbox = QtWidgets.QCheckBox("Drag & Drop aktivieren")
    log_row = 2 if layout_combo is not None else 1
    general_layout.addWidget(log_visible_checkbox, log_row, 1)
    general_layout.addWidget(remember_window_checkbox, log_row + 1, 1)
    general_layout.addWidget(drag_drop_checkbox, log_row + 2, 1)

    settings_layout.addWidget(general_group)

    db_intro = QtWidgets.QLabel("Datenbank- und DAT-Index-Verwaltung.")
    db_intro.setWordWrap(True)
    settings_layout.addWidget(db_intro)

    dat_hint = QtWidgets.QLabel(
        "DAT-Index wird als SQLite unter data/index/romsorter_dat_index.sqlite gespeichert. "
        "Lege DAT-Dateien in einem eigenen Ordner ab und baue den Index bei Änderungen neu."
    )
    dat_hint.setWordWrap(True)
    settings_layout.addWidget(dat_hint)

    db_form = QtWidgets.QGridLayout()
    db_form.setHorizontalSpacing(10)
    db_form.setVerticalSpacing(6)
    settings_layout.addLayout(db_form)

    db_form.addWidget(inputs.dat_status, 0, 0)
    db_form.addWidget(inputs.btn_add_dat, 0, 1)
    db_form.addWidget(inputs.btn_refresh_dat, 0, 2)
    db_form.addWidget(inputs.btn_cancel_dat, 0, 3)
    db_form.addWidget(inputs.btn_manage_dat, 0, 4)

    db_form.addWidget(inputs.dat_auto_load_checkbox, 1, 0, 1, 2)
    db_form.addWidget(inputs.btn_clear_dat_cache, 1, 2)

    db_form.addWidget(inputs.db_status, 2, 0)
    db_form.addWidget(inputs.btn_db_manager, 2, 1)
    db_form.setColumnStretch(1, 1)

    advanced_group = QtWidgets.QGroupBox("Erweitert")
    advanced_layout = QtWidgets.QVBoxLayout(advanced_group)
    advanced_hint = QtWidgets.QLabel(
        "Optionen für Bestätigungs- und Tool-Integration."
    )
    advanced_hint.setWordWrap(True)
    advanced_layout.addWidget(advanced_hint)
    advanced_layout.addWidget(inputs.review_gate_checkbox)
    advanced_layout.addWidget(inputs.external_tools_checkbox)
    advanced_layout.addWidget(inputs.btn_open_overrides)
    advanced_layout.addWidget(inputs.tools_group)
    advanced_layout.addWidget(inputs.tools_status_hint)
    advanced_layout.addStretch(1)
    settings_layout.addWidget(advanced_group)

    return SettingsUI(
        layout_combo=layout_combo,
        log_visible_checkbox=log_visible_checkbox,
        remember_window_checkbox=remember_window_checkbox,
        drag_drop_checkbox=drag_drop_checkbox,
    )
