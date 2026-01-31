from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DatSourcesUI:
    list_widget: Any
    status_label: Any
    btn_add: Any
    btn_remove: Any
    btn_open: Any
    btn_refresh: Any
    btn_coverage: Any
    btn_close: Any


def build_dat_sources_ui(QtWidgets, parent) -> DatSourcesUI:
    layout = QtWidgets.QVBoxLayout(parent)

    list_widget = QtWidgets.QListWidget()
    layout.addWidget(list_widget)

    status_label = QtWidgets.QLabel("-")
    status_label.setWordWrap(True)
    layout.addWidget(status_label)

    controls = QtWidgets.QGridLayout()
    layout.addLayout(controls)

    btn_add = QtWidgets.QPushButton("Hinzufügen…")
    btn_remove = QtWidgets.QPushButton("Entfernen")
    btn_open = QtWidgets.QPushButton("Ordner öffnen")
    btn_refresh = QtWidgets.QPushButton("Integrität prüfen")
    btn_coverage = QtWidgets.QPushButton("Coverage anzeigen")
    btn_close = QtWidgets.QPushButton("Schließen")

    controls.addWidget(btn_add, 0, 0)
    controls.addWidget(btn_remove, 0, 1)
    controls.addWidget(btn_open, 0, 2)
    controls.addWidget(btn_refresh, 0, 3)
    controls.addWidget(btn_coverage, 1, 0)
    controls.addWidget(btn_close, 1, 3)
    controls.setColumnStretch(4, 1)

    return DatSourcesUI(
        list_widget=list_widget,
        status_label=status_label,
        btn_add=btn_add,
        btn_remove=btn_remove,
        btn_open=btn_open,
        btn_refresh=btn_refresh,
        btn_coverage=btn_coverage,
        btn_close=btn_close,
    )
