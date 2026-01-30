from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IgirInputs:
    igir_exe_edit: Any
    igir_args_edit: Any
    igir_templates_view: Any
    igir_template_combo: Any
    btn_igir_apply_template: Any
    igir_profile_combo: Any
    btn_igir_apply_profile: Any
    btn_igir_browse: Any
    btn_igir_save: Any
    btn_igir_probe: Any
    btn_igir_plan: Any
    btn_igir_execute: Any
    btn_igir_cancel: Any
    igir_status_label: Any
    igir_copy_first_checkbox: Any
    igir_source_edit: Any
    igir_dest_edit: Any


def build_igir_inputs_ui(QtWidgets) -> IgirInputs:
    igir_exe_edit = QtWidgets.QLineEdit()
    igir_args_edit = QtWidgets.QPlainTextEdit()
    igir_args_edit.setPlaceholderText("One argument per line. Use {input} and {output_dir}.")

    igir_templates_view = QtWidgets.QPlainTextEdit()
    igir_templates_view.setReadOnly(True)
    igir_templates_view.setPlaceholderText("Templates from igir.yaml (read-only)")

    igir_template_combo = QtWidgets.QComboBox()
    igir_template_combo.addItem("-")
    btn_igir_apply_template = QtWidgets.QPushButton("Template übernehmen")

    igir_profile_combo = QtWidgets.QComboBox()
    igir_profile_combo.addItem("-")
    btn_igir_apply_profile = QtWidgets.QPushButton("Profil aktivieren")

    btn_igir_browse = QtWidgets.QPushButton("IGIR wählen…")
    btn_igir_save = QtWidgets.QPushButton("IGIR speichern")
    btn_igir_probe = QtWidgets.QPushButton("IGIR prüfen")
    btn_igir_plan = QtWidgets.QPushButton("Plan erstellen")
    btn_igir_execute = QtWidgets.QPushButton("Ausführen")
    btn_igir_execute.setEnabled(False)
    btn_igir_cancel = QtWidgets.QPushButton("IGIR abbrechen")
    btn_igir_cancel.setEnabled(False)

    igir_status_label = QtWidgets.QLabel("Status: -")
    igir_copy_first_checkbox = QtWidgets.QCheckBox("Copy-first (Staging)")

    igir_source_edit = QtWidgets.QLineEdit()
    igir_dest_edit = QtWidgets.QLineEdit()
    igir_source_edit.setPlaceholderText("Quelle (aus Haupt-Tab)")
    igir_dest_edit.setPlaceholderText("Ziel (aus Haupt-Tab)")
    igir_source_edit.setReadOnly(True)
    igir_dest_edit.setReadOnly(True)

    return IgirInputs(
        igir_exe_edit=igir_exe_edit,
        igir_args_edit=igir_args_edit,
        igir_templates_view=igir_templates_view,
        igir_template_combo=igir_template_combo,
        btn_igir_apply_template=btn_igir_apply_template,
        igir_profile_combo=igir_profile_combo,
        btn_igir_apply_profile=btn_igir_apply_profile,
        btn_igir_browse=btn_igir_browse,
        btn_igir_save=btn_igir_save,
        btn_igir_probe=btn_igir_probe,
        btn_igir_plan=btn_igir_plan,
        btn_igir_execute=btn_igir_execute,
        btn_igir_cancel=btn_igir_cancel,
        igir_status_label=igir_status_label,
        igir_copy_first_checkbox=igir_copy_first_checkbox,
        igir_source_edit=igir_source_edit,
        igir_dest_edit=igir_dest_edit,
    )
