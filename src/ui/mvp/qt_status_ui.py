"""Status tab UI builder for MVP Qt UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StatusUI:
    main_status_group: Any
    main_source_label: Any
    main_dest_label: Any
    progress: Any
    status_label: Any
    summary_label: Any


def build_status_ui(QtWidgets, binding: str) -> StatusUI:
    main_status_group = QtWidgets.QGroupBox("Status")
    main_status_layout = QtWidgets.QGridLayout(main_status_group)
    main_status_layout.setHorizontalSpacing(6)
    main_status_layout.setVerticalSpacing(4)

    main_source_label = QtWidgets.QLabel("-")
    main_source_label.setWordWrap(True)
    main_dest_label = QtWidgets.QLabel("-")
    main_dest_label.setWordWrap(True)

    progress = QtWidgets.QProgressBar()
    progress.setRange(0, 100)
    progress.setValue(0)
    status_label = QtWidgets.QLabel(f"Bereit ({binding})")
    summary_label = QtWidgets.QLabel("-")

    main_status_layout.addWidget(QtWidgets.QLabel("Quelle:"), 0, 0)
    main_status_layout.addWidget(main_source_label, 0, 1)
    main_status_layout.addWidget(QtWidgets.QLabel("Ziel:"), 1, 0)
    main_status_layout.addWidget(main_dest_label, 1, 1)
    main_status_layout.addWidget(progress, 2, 0, 1, 2)
    main_status_layout.addWidget(status_label, 3, 0, 1, 2)
    main_status_layout.addWidget(summary_label, 4, 0, 1, 2)
    main_status_layout.setColumnStretch(1, 1)

    return StatusUI(
        main_status_group=main_status_group,
        main_source_label=main_source_label,
        main_dest_label=main_dest_label,
        progress=progress,
        status_label=status_label,
        summary_label=summary_label,
    )
