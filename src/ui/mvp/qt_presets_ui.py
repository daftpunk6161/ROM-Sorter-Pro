"""Presets and queue UI builder for MVP Qt UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PresetsUI:
    presets_group: Any
    queue_group: Any
    preset_combo: Any
    preset_name_edit: Any
    btn_preset_apply: Any
    btn_preset_save: Any
    btn_preset_delete: Any
    btn_execute_selected: Any
    queue_mode_checkbox: Any
    queue_priority_combo: Any
    queue_pause_btn: Any
    queue_resume_btn: Any
    queue_clear_btn: Any
    queue_list: Any


def build_presets_queue_ui(QtWidgets) -> PresetsUI:
    presets_group = QtWidgets.QGroupBox("Presets & Auswahl")
    presets_layout = QtWidgets.QGridLayout(presets_group)
    presets_layout.setHorizontalSpacing(6)
    presets_layout.setVerticalSpacing(6)

    preset_combo = QtWidgets.QComboBox()
    preset_combo.addItem("-")
    preset_name_edit = QtWidgets.QLineEdit()
    preset_name_edit.setPlaceholderText("Preset-Name")
    btn_preset_apply = QtWidgets.QPushButton("Übernehmen")
    btn_preset_save = QtWidgets.QPushButton("Speichern")
    btn_preset_delete = QtWidgets.QPushButton("Löschen")
    btn_execute_selected = QtWidgets.QPushButton("Auswahl ausführen")

    presets_layout.addWidget(QtWidgets.QLabel("Preset:"), 0, 0)
    presets_layout.addWidget(preset_combo, 0, 1)
    presets_layout.addWidget(btn_preset_apply, 0, 2)
    presets_layout.addWidget(preset_name_edit, 1, 0, 1, 2)
    presets_layout.addWidget(btn_preset_save, 1, 2)
    presets_layout.addWidget(btn_preset_delete, 2, 2)
    presets_layout.addWidget(btn_execute_selected, 2, 0, 1, 2)
    presets_layout.setColumnStretch(1, 1)

    queue_group = QtWidgets.QGroupBox("Jobs")
    queue_layout = QtWidgets.QGridLayout(queue_group)
    queue_layout.setHorizontalSpacing(6)
    queue_layout.setVerticalSpacing(6)

    queue_mode_checkbox = QtWidgets.QCheckBox("Queue mode")
    queue_priority_combo = QtWidgets.QComboBox()
    queue_priority_combo.addItems(["Normal", "High", "Low"])
    queue_pause_btn = QtWidgets.QPushButton("Pause")
    queue_resume_btn = QtWidgets.QPushButton("Resume")
    queue_clear_btn = QtWidgets.QPushButton("Clear")
    queue_resume_btn.setEnabled(False)
    queue_list = QtWidgets.QListWidget()
    queue_list.setMaximumHeight(90)

    queue_layout.addWidget(QtWidgets.QLabel("Priorität:"), 0, 0)
    queue_layout.addWidget(queue_priority_combo, 0, 1)
    queue_layout.addWidget(queue_mode_checkbox, 0, 2)
    queue_layout.addWidget(queue_pause_btn, 1, 0)
    queue_layout.addWidget(queue_resume_btn, 1, 1)
    queue_layout.addWidget(queue_clear_btn, 1, 2)
    queue_layout.addWidget(queue_list, 2, 0, 1, 3)

    return PresetsUI(
        presets_group=presets_group,
        queue_group=queue_group,
        preset_combo=preset_combo,
        preset_name_edit=preset_name_edit,
        btn_preset_apply=btn_preset_apply,
        btn_preset_save=btn_preset_save,
        btn_preset_delete=btn_preset_delete,
        btn_execute_selected=btn_execute_selected,
        queue_mode_checkbox=queue_mode_checkbox,
        queue_priority_combo=queue_priority_combo,
        queue_pause_btn=queue_pause_btn,
        queue_resume_btn=queue_resume_btn,
        queue_clear_btn=queue_clear_btn,
        queue_list=queue_list,
    )
