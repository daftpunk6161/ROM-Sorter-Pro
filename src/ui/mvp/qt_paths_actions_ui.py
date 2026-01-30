"""Paths and actions UI builder for MVP Qt UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from ..i18n import translate


@dataclass(frozen=True)
class PathsActionsUI:
    paths_group: Any
    actions_group: Any
    actions_layout: Any
    source_edit: Any
    dest_edit: Any
    btn_source: Any
    btn_dest: Any
    btn_open_dest: Any
    mode_combo: Any
    conflict_combo: Any
    rebuild_checkbox: Any
    chk_console_folders: Any
    chk_region_subfolders: Any
    chk_preserve_structure: Any
    actions_advanced_toggle: Any
    actions_advanced_group: Any
    default_mode_combo: Any
    default_conflict_combo: Any


def build_paths_actions_ui(
    QtWidgets,
    QtCore,
    DropLineEdit,
    dnd_enabled: bool,
    on_drop_source,
    on_drop_dest,
) -> PathsActionsUI:
    paths_group = QtWidgets.QGroupBox(translate("paths"))
    actions_group = QtWidgets.QGroupBox("")
    actions_group.setFlat(True)

    paths_layout = QtWidgets.QGridLayout(paths_group)
    actions_layout = QtWidgets.QGridLayout(actions_group)

    for grid_layout in (paths_layout, actions_layout):
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(6)

    source_edit = DropLineEdit(on_drop_source, enabled=dnd_enabled)
    dest_edit = DropLineEdit(on_drop_dest, enabled=dnd_enabled)
    source_edit.setPlaceholderText(translate("choose_source"))
    dest_edit.setPlaceholderText(translate("choose_dest"))

    btn_source = QtWidgets.QPushButton(translate("choose_source"))
    btn_dest = QtWidgets.QPushButton(translate("choose_dest"))
    btn_source.setMinimumWidth(150)
    btn_dest.setMinimumWidth(150)
    btn_open_dest = QtWidgets.QPushButton(translate("open_dest"))

    paths_layout.addWidget(QtWidgets.QLabel(f"{translate('source')}:") , 0, 0)
    paths_layout.addWidget(source_edit, 0, 1)
    paths_layout.addWidget(btn_source, 0, 2)

    paths_layout.addWidget(QtWidgets.QLabel(f"{translate('dest')}:") , 1, 0)
    paths_layout.addWidget(dest_edit, 1, 1)
    paths_layout.addWidget(btn_dest, 1, 2)
    paths_layout.addWidget(btn_open_dest, 1, 3)

    paths_layout.setColumnStretch(1, 1)

    mode_combo = QtWidgets.QComboBox()
    mode_combo.addItems(["copy", "move"])

    conflict_combo = QtWidgets.QComboBox()
    conflict_combo.addItems(["rename", "skip", "overwrite"])

    rebuild_checkbox = QtWidgets.QCheckBox("Rebuilder-Modus (Copy-only, Konflikte überspringen)")
    chk_console_folders = QtWidgets.QCheckBox("Konsolenordner erstellen")
    chk_region_subfolders = QtWidgets.QCheckBox("Regionsordner erstellen")
    chk_preserve_structure = QtWidgets.QCheckBox("Quell-Unterordner beibehalten")

    default_mode_combo = QtWidgets.QComboBox()
    default_mode_combo.addItems(["copy", "move"])
    default_conflict_combo = QtWidgets.QComboBox()
    default_conflict_combo.addItems(["rename", "skip", "overwrite"])

    actions_layout.addWidget(QtWidgets.QLabel(f"{translate('action')}:") , 0, 0)
    actions_layout.addWidget(mode_combo, 0, 1)

    actions_layout.addWidget(QtWidgets.QLabel(f"{translate('conflicts')}:") , 1, 0)
    actions_layout.addWidget(conflict_combo, 1, 1)

    actions_layout.addWidget(rebuild_checkbox, 2, 1)
    actions_layout.addWidget(chk_console_folders, 3, 0, 1, 2)
    actions_layout.addWidget(chk_region_subfolders, 4, 0, 1, 2)
    actions_layout.addWidget(chk_preserve_structure, 5, 0, 1, 2)

    actions_advanced_toggle = QtWidgets.QCheckBox("Voreinstellungen anzeigen")
    actions_layout.addWidget(actions_advanced_toggle, 6, 0, 1, 2)

    actions_advanced_group = QtWidgets.QGroupBox("Voreinstellungen (optional)")
    actions_advanced_layout = QtWidgets.QGridLayout(actions_advanced_group)
    actions_advanced_layout.setHorizontalSpacing(6)
    actions_advanced_layout.setVerticalSpacing(6)
    actions_advanced_layout.addWidget(QtWidgets.QLabel("Standardmodus:"), 0, 0)
    actions_advanced_layout.addWidget(default_mode_combo, 0, 1)
    actions_advanced_layout.addWidget(QtWidgets.QLabel("Standard-Konflikte:"), 1, 0)
    actions_advanced_layout.addWidget(default_conflict_combo, 1, 1)
    actions_advanced_layout.setColumnStretch(1, 1)
    actions_advanced_group.setVisible(False)
    actions_layout.addWidget(actions_advanced_group, 7, 0, 1, 2)

    actions_layout.setColumnStretch(1, 1)

    actions_advanced_toggle.toggled.connect(actions_advanced_group.setVisible)

    return PathsActionsUI(
        paths_group=paths_group,
        actions_group=actions_group,
        actions_layout=actions_layout,
        source_edit=source_edit,
        dest_edit=dest_edit,
        btn_source=btn_source,
        btn_dest=btn_dest,
        btn_open_dest=btn_open_dest,
        mode_combo=mode_combo,
        conflict_combo=conflict_combo,
        rebuild_checkbox=rebuild_checkbox,
        chk_console_folders=chk_console_folders,
        chk_region_subfolders=chk_region_subfolders,
        chk_preserve_structure=chk_preserve_structure,
        actions_advanced_toggle=actions_advanced_toggle,
        actions_advanced_group=actions_advanced_group,
        default_mode_combo=default_mode_combo,
        default_conflict_combo=default_conflict_combo,
    )
