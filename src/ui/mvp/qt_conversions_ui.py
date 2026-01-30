"""Conversion and IGIR UI builder for MVP Qt UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple


@dataclass(frozen=True)
class ConversionInputs:
    btn_execute_convert: Any
    btn_audit: Any
    igir_status_label: Any
    btn_igir_probe: Any
    btn_igir_plan: Any
    btn_igir_execute: Any
    igir_advanced_toggle: Any
    igir_exe_edit: Any
    btn_igir_browse: Any
    igir_args_edit: Any
    igir_templates_view: Any
    igir_template_combo: Any
    btn_igir_apply_template: Any
    igir_profile_combo: Any
    btn_igir_apply_profile: Any
    btn_igir_save: Any
    igir_source_edit: Any
    igir_dest_edit: Any
    btn_igir_cancel: Any
    igir_copy_first_checkbox: Any


@dataclass(frozen=True)
class ConversionUIRefs:
    conversion_source_label: Any
    conversion_dest_label: Any
    igir_cfg_group: Any
    btn_igir_open_diff_csv: Any
    btn_igir_open_diff_json: Any


def build_conversions_ui(
    QtWidgets,
    conversions_layout,
    inputs: ConversionInputs,
    source_text: str,
    dest_text: str,
) -> ConversionUIRefs:
    conversions_intro = QtWidgets.QLabel(
        "Konvertierungen sind optional. Empfohlen: 1) Prüfen → 2) Ausführen."
    )
    conversions_intro.setWordWrap(True)
    conversions_layout.addWidget(conversions_intro)

    conversions_steps = QtWidgets.QLabel(
        "• Prüfen erstellt einen Report (keine Änderungen)\n"
        "• Ausführen startet die Konvertierung (mit externen Tools)"
    )
    conversions_steps.setWordWrap(True)
    conversions_layout.addWidget(conversions_steps)

    conversions_quick = QtWidgets.QGroupBox("Schnellstart")
    conversions_quick_layout = QtWidgets.QHBoxLayout(conversions_quick)
    conversions_quick_layout.addWidget(inputs.btn_execute_convert)
    conversions_quick_layout.addWidget(inputs.btn_audit)
    conversions_quick_layout.addStretch(1)
    conversions_layout.addWidget(conversions_quick)

    conversions_paths = QtWidgets.QGroupBox("Pfade (aus Sortieren)")
    conversions_paths_layout = QtWidgets.QGridLayout(conversions_paths)
    conversions_paths_layout.setHorizontalSpacing(6)
    conversions_paths_layout.setVerticalSpacing(6)

    conversion_source_label = QtWidgets.QLabel("-")
    conversion_dest_label = QtWidgets.QLabel("-")
    conversion_source_label.setWordWrap(True)
    conversion_dest_label.setWordWrap(True)

    conversions_paths_layout.addWidget(QtWidgets.QLabel("Quelle:"), 0, 0)
    conversions_paths_layout.addWidget(conversion_source_label, 0, 1, 1, 3)
    conversions_paths_layout.addWidget(QtWidgets.QLabel("Ziel:"), 1, 0)
    conversions_paths_layout.addWidget(conversion_dest_label, 1, 1, 1, 3)
    conversions_paths_layout.setColumnStretch(1, 1)

    inputs.igir_source_edit.setText(source_text)
    inputs.igir_dest_edit.setText(dest_text)

    conversions_layout.addWidget(conversions_paths)

    igir_intro = QtWidgets.QLabel(
        "IGIR ist ein externes Tool. Erstellt zuerst einen Plan und führt dann aus (niemals im Dry-Run)."
    )
    igir_intro.setWordWrap(True)
    conversions_layout.addWidget(igir_intro)

    igir_status_row = QtWidgets.QHBoxLayout()
    igir_status_row.addWidget(inputs.igir_status_label)
    igir_status_row.addStretch(1)
    igir_status_row.addWidget(inputs.btn_igir_probe)
    conversions_layout.addLayout(igir_status_row)

    igir_quick = QtWidgets.QGroupBox("Schnellstart")
    igir_quick_layout = QtWidgets.QHBoxLayout(igir_quick)
    igir_quick_layout.addWidget(inputs.btn_igir_plan)
    igir_quick_layout.addWidget(inputs.btn_igir_execute)
    igir_quick_layout.addStretch(1)
    conversions_layout.addWidget(igir_quick)

    inputs.igir_advanced_toggle.setChecked(False)
    conversions_layout.addWidget(inputs.igir_advanced_toggle)

    igir_cfg_group = QtWidgets.QGroupBox("Erweitert: IGIR Konfiguration")
    igir_cfg_layout = QtWidgets.QGridLayout(igir_cfg_group)
    igir_cfg_layout.setHorizontalSpacing(6)
    igir_cfg_layout.setVerticalSpacing(6)
    igir_cfg_layout.addWidget(QtWidgets.QLabel("IGIR Executable:"), 0, 0)
    igir_cfg_layout.addWidget(inputs.igir_exe_edit, 0, 1)
    igir_cfg_layout.addWidget(inputs.btn_igir_browse, 0, 2)
    igir_cfg_layout.addWidget(QtWidgets.QLabel("Args Template:"), 1, 0)
    igir_cfg_layout.addWidget(inputs.igir_args_edit, 1, 1, 2, 2)
    igir_cfg_layout.addWidget(QtWidgets.QLabel("Standard Templates:"), 3, 0)
    igir_cfg_layout.addWidget(inputs.igir_templates_view, 3, 1, 2, 2)
    igir_cfg_layout.addWidget(QtWidgets.QLabel("Template übernehmen:"), 5, 0)
    igir_cfg_layout.addWidget(inputs.igir_template_combo, 5, 1)
    igir_cfg_layout.addWidget(inputs.btn_igir_apply_template, 5, 2)
    igir_cfg_layout.addWidget(QtWidgets.QLabel("Profil:"), 6, 0)
    igir_cfg_layout.addWidget(inputs.igir_profile_combo, 6, 1)
    igir_cfg_layout.addWidget(inputs.btn_igir_apply_profile, 6, 2)
    igir_cfg_layout.setColumnStretch(1, 1)
    igir_actions_row = QtWidgets.QHBoxLayout()
    igir_actions_row.addWidget(inputs.btn_igir_save)
    igir_actions_row.addStretch(1)
    igir_cfg_layout.addLayout(igir_actions_row, 7, 1, 1, 2)
    igir_cfg_group.setVisible(False)
    conversions_layout.addWidget(igir_cfg_group)

    igir_run_group = QtWidgets.QGroupBox("Ausführen")
    igir_run_layout = QtWidgets.QGridLayout(igir_run_group)
    igir_run_layout.setHorizontalSpacing(6)
    igir_run_layout.setVerticalSpacing(6)
    igir_run_layout.addWidget(QtWidgets.QLabel("Quelle:"), 0, 0)
    igir_run_layout.addWidget(inputs.igir_source_edit, 0, 1)
    igir_run_layout.addWidget(QtWidgets.QLabel("Ziel:"), 1, 0)
    igir_run_layout.addWidget(inputs.igir_dest_edit, 1, 1)
    igir_run_layout.addWidget(inputs.btn_igir_cancel, 2, 0)
    igir_run_layout.addWidget(inputs.igir_status_label, 3, 0, 1, 3)
    igir_run_layout.addWidget(inputs.igir_copy_first_checkbox, 4, 0, 1, 2)

    btn_igir_open_diff_csv = QtWidgets.QPushButton("Diff CSV öffnen")
    btn_igir_open_diff_json = QtWidgets.QPushButton("Diff JSON öffnen")
    btn_igir_open_diff_csv.setEnabled(False)
    btn_igir_open_diff_json.setEnabled(False)
    igir_run_layout.addWidget(btn_igir_open_diff_csv, 5, 0)
    igir_run_layout.addWidget(btn_igir_open_diff_json, 5, 1)
    igir_run_layout.setColumnStretch(1, 1)
    conversions_layout.addWidget(igir_run_group)

    conversions_layout.addStretch(1)

    return ConversionUIRefs(
        conversion_source_label=conversion_source_label,
        conversion_dest_label=conversion_dest_label,
        igir_cfg_group=igir_cfg_group,
        btn_igir_open_diff_csv=btn_igir_open_diff_csv,
        btn_igir_open_diff_json=btn_igir_open_diff_json,
    )
