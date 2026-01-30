from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List


@dataclass(frozen=True)
class HeaderUI:
    header_bar: Any
    progress_header: Any
    header_progress: Any
    header_progress_label: Any
    header_btn_scan: Any
    header_btn_preview: Any
    header_btn_execute: Any
    header_btn_cancel: Any
    header_cmd_btn: Any
    header_log_btn: Any
    header_theme_combo: Any
    review_gate_checkbox: Any
    external_tools_checkbox: Any
    pill_status: Any
    pill_queue: Any
    pill_dat: Any
    pill_safety: Any
    status_bar: Any


def build_header_ui(
    QtWidgets,
    QtCore,
    label_func,
    theme_names: Iterable[str],
    parent,
    app_version: str,
) -> HeaderUI:
    header_bar = QtWidgets.QWidget()
    header_layout = QtWidgets.QHBoxLayout(header_bar)
    header_layout.setContentsMargins(8, 8, 8, 8)
    header_layout.setSpacing(10)

    app_title = QtWidgets.QLabel("ROM Sorter Pro")
    app_title.setStyleSheet("font-size: 18px; font-weight: 700;")
    app_version_label = QtWidgets.QLabel(f"v{app_version}")
    app_version_label.setStyleSheet("color: #777;")

    header_btn_scan = QtWidgets.QPushButton(label_func("Scan", "scan"))
    header_btn_preview = QtWidgets.QPushButton(label_func("Preview", "preview"))
    header_btn_execute = QtWidgets.QPushButton(label_func("Execute", "execute"))
    header_btn_cancel = QtWidgets.QPushButton(label_func("Cancel", "cancel"))
    header_btn_preview.setObjectName("secondary")
    header_btn_execute.setObjectName("primary")
    header_btn_cancel.setObjectName("danger")
    header_btn_cancel.setEnabled(False)

    header_cmd_btn = QtWidgets.QPushButton("⌘")
    header_log_btn = QtWidgets.QPushButton("Log")

    header_theme_combo = QtWidgets.QComboBox()
    header_theme_combo.addItems(list(theme_names))
    header_theme_combo.setVisible(False)

    review_gate_checkbox = QtWidgets.QCheckBox("Review Gate")
    review_gate_checkbox.setChecked(True)
    external_tools_checkbox = QtWidgets.QCheckBox("External Tools")
    external_tools_checkbox.setChecked(False)

    pill_status = QtWidgets.QLabel("Bereit")
    pill_queue = QtWidgets.QLabel("Queue: 0")
    pill_dat = QtWidgets.QLabel("DAT: -")
    pill_safety = QtWidgets.QLabel("Safe")
    for pill in (pill_status, pill_queue, pill_dat, pill_safety):
        pill.setStyleSheet("padding: 2px 8px; border-radius: 10px; background: #e8e8e8;")

    header_layout.addWidget(app_title)
    header_layout.addWidget(app_version_label)
    header_layout.addStretch(1)
    header_layout.addWidget(header_btn_scan)
    header_layout.addWidget(header_btn_preview)
    header_layout.addWidget(header_btn_execute)
    header_layout.addWidget(header_btn_cancel)

    progress_header = QtWidgets.QWidget()
    progress_layout = QtWidgets.QHBoxLayout(progress_header)
    progress_layout.setContentsMargins(8, 0, 8, 6)
    progress_layout.setSpacing(8)
    header_progress_label = QtWidgets.QLabel("Bereit")
    header_progress = QtWidgets.QProgressBar()
    header_progress.setRange(0, 100)
    header_progress.setValue(0)
    progress_layout.addWidget(header_progress)
    progress_layout.addWidget(header_progress_label)

    status_bar = QtWidgets.QStatusBar(parent)
    parent.setStatusBar(status_bar)
    status_bar.addWidget(pill_status)
    status_bar.addWidget(pill_dat)
    status_bar.addWidget(pill_queue)
    status_bar.addWidget(pill_safety)
    status_bar.addPermanentWidget(header_log_btn)
    status_bar.addPermanentWidget(header_cmd_btn)

    return HeaderUI(
        header_bar=header_bar,
        progress_header=progress_header,
        header_progress=header_progress,
        header_progress_label=header_progress_label,
        header_btn_scan=header_btn_scan,
        header_btn_preview=header_btn_preview,
        header_btn_execute=header_btn_execute,
        header_btn_cancel=header_btn_cancel,
        header_cmd_btn=header_cmd_btn,
        header_log_btn=header_log_btn,
        header_theme_combo=header_theme_combo,
        review_gate_checkbox=review_gate_checkbox,
        external_tools_checkbox=external_tools_checkbox,
        pill_status=pill_status,
        pill_queue=pill_queue,
        pill_dat=pill_dat,
        pill_safety=pill_safety,
        status_bar=status_bar,
    )
