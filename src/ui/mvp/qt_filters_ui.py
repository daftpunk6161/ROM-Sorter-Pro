"""Filter UI builder for MVP Qt UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple


@dataclass(frozen=True)
class FilterWidgets:
    console_filter: Any
    lang_filter: Any
    ver_filter: Any
    region_filter: Any
    ext_filter_edit: Any
    min_size_edit: Any
    max_size_edit: Any
    btn_clear_filters: Any
    dedupe_checkbox: Any
    hide_unknown_checkbox: Any


def build_filters_ui(QtWidgets, QtCore, QtGui) -> Tuple[Any, FilterWidgets]:
    filters_group = QtWidgets.QGroupBox("")
    filters_group.setFlat(True)
    filters_group.setMinimumWidth(320)
    filters_group.setMaximumWidth(520)

    filters_layout = QtWidgets.QGridLayout(filters_group)
    filters_layout.setHorizontalSpacing(10)
    filters_layout.setVerticalSpacing(6)

    lang_filter = QtWidgets.QListWidget()
    lang_filter.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
    lang_filter.addItems(["All"])
    lang_filter.setMinimumWidth(200)
    lang_filter.setMaximumHeight(90)

    console_filter = QtWidgets.QListWidget()
    console_filter.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
    console_filter.addItems(["All"])
    console_filter.setMinimumWidth(200)
    console_filter.setMaximumHeight(90)

    ver_filter = QtWidgets.QComboBox()
    ver_filter.addItems(["All"])
    ver_filter.setMinimumWidth(200)

    region_filter = QtWidgets.QListWidget()
    region_filter.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
    region_filter.addItems(["All"])
    region_filter.setMinimumWidth(200)
    region_filter.setMaximumHeight(90)

    ext_filter_edit = QtWidgets.QLineEdit()
    ext_filter_edit.setPlaceholderText(".iso,.chd,.zip")
    min_size_edit = QtWidgets.QLineEdit()
    min_size_edit.setPlaceholderText("Min MB")
    max_size_edit = QtWidgets.QLineEdit()
    max_size_edit.setPlaceholderText("Max MB")
    min_size_edit.setFixedWidth(90)
    max_size_edit.setFixedWidth(90)
    size_validator = QtGui.QDoubleValidator(0.0, 1_000_000_000.0, 3)
    size_validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
    min_size_edit.setValidator(size_validator)
    max_size_edit.setValidator(size_validator)

    btn_clear_filters = QtWidgets.QPushButton("Filter zurücksetzen")

    dedupe_checkbox = QtWidgets.QCheckBox("Duplikate vermeiden")
    dedupe_checkbox.setChecked(True)
    hide_unknown_checkbox = QtWidgets.QCheckBox("Unbekannt ausblenden (niedrige Sicherheit)")
    hide_unknown_checkbox.setChecked(False)

    filter_left = QtWidgets.QFormLayout()
    filter_left.setLabelAlignment(QtCore.Qt.AlignLeft)
    filter_left.setFormAlignment(QtCore.Qt.AlignLeft)
    filter_left.setHorizontalSpacing(10)
    filter_left.setVerticalSpacing(6)
    filter_left.addRow("Konsole:", console_filter)
    filter_left.addRow("Region:", region_filter)

    filter_right = QtWidgets.QFormLayout()
    filter_right.setLabelAlignment(QtCore.Qt.AlignLeft)
    filter_right.setFormAlignment(QtCore.Qt.AlignLeft)
    filter_right.setHorizontalSpacing(10)
    filter_right.setVerticalSpacing(6)
    filter_right.addRow("Sprache:", lang_filter)
    filter_right.addRow("Version:", ver_filter)

    filters_layout.addLayout(filter_left, 1, 0)
    filters_layout.addLayout(filter_right, 1, 1)

    options_box = QtWidgets.QVBoxLayout()
    options_box.addWidget(dedupe_checkbox)
    options_box.addWidget(hide_unknown_checkbox)
    filters_layout.addLayout(options_box, 2, 0, 1, 2)

    filters_layout.addWidget(QtWidgets.QLabel("Erweiterungen:"), 3, 0)
    filters_layout.addWidget(ext_filter_edit, 3, 1)

    size_row = QtWidgets.QHBoxLayout()
    size_row.addWidget(QtWidgets.QLabel("Min (MB):"))
    size_row.addWidget(min_size_edit)
    size_row.addSpacing(10)
    size_row.addWidget(QtWidgets.QLabel("Max (MB):"))
    size_row.addWidget(max_size_edit)
    size_row.addStretch(1)
    filters_layout.addLayout(size_row, 4, 0, 1, 2)

    filters_layout.addWidget(btn_clear_filters, 5, 0, 1, 2, QtCore.Qt.AlignLeft)

    widgets = FilterWidgets(
        console_filter=console_filter,
        lang_filter=lang_filter,
        ver_filter=ver_filter,
        region_filter=region_filter,
        ext_filter_edit=ext_filter_edit,
        min_size_edit=min_size_edit,
        max_size_edit=max_size_edit,
        btn_clear_filters=btn_clear_filters,
        dedupe_checkbox=dedupe_checkbox,
        hide_unknown_checkbox=hide_unknown_checkbox,
    )
    return filters_group, widgets
