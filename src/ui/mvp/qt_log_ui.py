"""Log dock UI builder for MVP Qt UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LogUI:
    log_view: Any
    log_toggle_btn: Any
    log_filter_edit: Any
    log_filter_clear_btn: Any
    log_autoscroll_checkbox: Any
    log_dock: Any


def build_log_ui(QtWidgets, QtCore, parent) -> LogUI:
    log_view = QtWidgets.QPlainTextEdit()
    log_view.setReadOnly(True)

    log_title = QtWidgets.QLabel("Log")
    log_title.setStyleSheet("font-weight: 600;")
    log_toggle_btn = QtWidgets.QPushButton("Log ausblenden")
    log_toggle_btn.setMinimumWidth(140)
    log_filter_edit = QtWidgets.QLineEdit()
    log_filter_edit.setPlaceholderText("Log filtern…")
    log_filter_clear_btn = QtWidgets.QPushButton("Filter löschen")
    log_autoscroll_checkbox = QtWidgets.QCheckBox("Auto-Scroll")
    log_autoscroll_checkbox.setChecked(True)

    log_header = QtWidgets.QHBoxLayout()
    log_header.addWidget(log_title)
    log_header.addWidget(log_filter_edit)
    log_header.addWidget(log_filter_clear_btn)
    log_header.addWidget(log_autoscroll_checkbox)
    log_header.addStretch(1)
    log_header.addWidget(log_toggle_btn)

    log_container = QtWidgets.QWidget()
    log_layout = QtWidgets.QVBoxLayout(log_container)
    log_layout.addLayout(log_header)
    log_layout.addWidget(log_view, 1)

    log_dock = QtWidgets.QDockWidget("Log", parent)
    log_dock.setWidget(log_container)
    log_dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea)

    return LogUI(
        log_view=log_view,
        log_toggle_btn=log_toggle_btn,
        log_filter_edit=log_filter_edit,
        log_filter_clear_btn=log_filter_clear_btn,
        log_autoscroll_checkbox=log_autoscroll_checkbox,
        log_dock=log_dock,
    )
