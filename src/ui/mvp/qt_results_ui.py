"""Results and details UI builder for MVP Qt UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResultsUI:
    results_empty_label: Any
    details_group: Any
    details_input_label: Any
    details_target_label: Any
    details_status_label: Any
    details_system_label: Any
    details_reason_label: Any
    quick_filter_edit: Any
    quick_filter_clear_btn: Any
    btn_toggle_filters: Any


def build_results_ui(QtWidgets, QtCore, details_stack, results_stack) -> ResultsUI:
    results_empty_label = QtWidgets.QLabel(
        "Noch keine Ergebnisse. Starte mit Scan oder Vorschau, um Einträge zu sehen."
    )
    results_empty_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    results_empty_label.setStyleSheet("color: #777; padding: 8px;")
    results_stack.addWidget(results_empty_label)

    details_group = QtWidgets.QGroupBox("Details")
    details_layout = QtWidgets.QFormLayout(details_group)
    details_input_label = QtWidgets.QLabel("-")
    details_target_label = QtWidgets.QLabel("-")
    details_status_label = QtWidgets.QLabel("-")
    details_system_label = QtWidgets.QLabel("-")
    details_reason_label = QtWidgets.QLabel("-")
    for detail_label in (
        details_input_label,
        details_target_label,
        details_status_label,
        details_system_label,
        details_reason_label,
    ):
        detail_label.setWordWrap(True)
    details_layout.addRow("Eingabe:", details_input_label)
    details_layout.addRow("Ziel:", details_target_label)
    details_layout.addRow("Status:", details_status_label)
    details_layout.addRow("System:", details_system_label)
    details_layout.addRow("Grund:", details_reason_label)
    details_group.setVisible(False)
    details_stack.addWidget(details_group)

    results_toolbar = QtWidgets.QHBoxLayout()
    quick_filter_edit = QtWidgets.QLineEdit()
    quick_filter_edit.setPlaceholderText("Ergebnis-Filter…")
    quick_filter_clear_btn = QtWidgets.QPushButton("Filter löschen")
    btn_toggle_filters = QtWidgets.QPushButton("Filter")
    btn_toggle_filters.setCheckable(True)
    btn_toggle_filters.setChecked(False)
    btn_toggle_filters.setToolTip("Filter-Tab anzeigen/ausblenden")

    results_toolbar.addWidget(QtWidgets.QLabel("Schnellfilter:"))
    results_toolbar.addWidget(quick_filter_edit)
    results_toolbar.addWidget(quick_filter_clear_btn)
    results_toolbar.addWidget(btn_toggle_filters)
    results_stack.addLayout(results_toolbar)

    return ResultsUI(
        results_empty_label=results_empty_label,
        details_group=details_group,
        details_input_label=details_input_label,
        details_target_label=details_target_label,
        details_status_label=details_status_label,
        details_system_label=details_system_label,
        details_reason_label=details_reason_label,
        quick_filter_edit=quick_filter_edit,
        quick_filter_clear_btn=quick_filter_clear_btn,
        btn_toggle_filters=btn_toggle_filters,
    )
