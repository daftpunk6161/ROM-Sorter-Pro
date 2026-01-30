"""Dashboard (Home) UI builder for MVP Qt UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DashboardUI:
    btn_home_source: Any
    btn_home_dest: Any
    btn_home_go_sort: Any
    recent_paths_label: Any
    favorites_list: Any
    btn_fav_add: Any
    btn_fav_apply: Any
    btn_fav_remove: Any
    dashboard_source_label: Any
    dashboard_dest_label: Any
    dashboard_status_label: Any
    dashboard_progress: Any
    dashboard_dat_label: Any


def build_dashboard_ui(QtWidgets, dashboard_layout) -> DashboardUI:
    dashboard_hint = QtWidgets.QLabel(
        "Sortiere deine ROM-Sammlung in wenigen Schritten."
    )
    dashboard_hint.setWordWrap(True)
    dashboard_layout.addWidget(dashboard_hint)

    hero_group = QtWidgets.QGroupBox("Schnellstart")
    hero_layout = QtWidgets.QGridLayout(hero_group)
    hero_layout.setHorizontalSpacing(10)
    hero_layout.setVerticalSpacing(6)
    hero_layout.addWidget(
        QtWidgets.QLabel("1️⃣ Quelle wählen → 2️⃣ Ziel wählen → 3️⃣ Scannen → 4️⃣ Los!"),
        0,
        0,
        1,
        3,
    )
    btn_home_source = QtWidgets.QPushButton("📂 Quelle wählen…")
    btn_home_dest = QtWidgets.QPushButton("📂 Ziel wählen…")
    btn_home_go_sort = QtWidgets.QPushButton("▶ Zum Sortieren")
    btn_home_go_sort.setObjectName("primary")
    hero_layout.addWidget(btn_home_source, 1, 0)
    hero_layout.addWidget(btn_home_dest, 1, 1)
    hero_layout.addWidget(btn_home_go_sort, 1, 2)
    dashboard_layout.addWidget(hero_group)

    recent_group = QtWidgets.QGroupBox("Zuletzt verwendet")
    recent_layout = QtWidgets.QVBoxLayout(recent_group)
    recent_paths_label = QtWidgets.QLabel("Noch keine Pfade gespeichert.")
    recent_paths_label.setWordWrap(True)
    recent_layout.addWidget(recent_paths_label)
    dashboard_layout.addWidget(recent_group)

    favorites_group = QtWidgets.QGroupBox("Favoriten")
    favorites_layout = QtWidgets.QVBoxLayout(favorites_group)
    favorites_list = QtWidgets.QListWidget()
    favorites_list.setMinimumHeight(90)
    favorites_layout.addWidget(favorites_list)

    favorites_btn_row = QtWidgets.QHBoxLayout()
    btn_fav_add = QtWidgets.QPushButton("Aktuelle Pfade speichern")
    btn_fav_apply = QtWidgets.QPushButton("Favorit anwenden")
    btn_fav_remove = QtWidgets.QPushButton("Favorit entfernen")
    favorites_btn_row.addWidget(btn_fav_add)
    favorites_btn_row.addWidget(btn_fav_apply)
    favorites_btn_row.addWidget(btn_fav_remove)
    favorites_btn_row.addStretch(1)
    favorites_layout.addLayout(favorites_btn_row)
    dashboard_layout.addWidget(favorites_group)

    status_group = QtWidgets.QGroupBox("Status")
    status_layout = QtWidgets.QGridLayout(status_group)
    status_layout.addWidget(QtWidgets.QLabel("📁 Quelle:"), 0, 0)
    dashboard_source_label = QtWidgets.QLabel("-")
    dashboard_source_label.setWordWrap(True)
    status_layout.addWidget(dashboard_source_label, 0, 1)
    status_layout.addWidget(QtWidgets.QLabel("🎯 Ziel:"), 1, 0)
    dashboard_dest_label = QtWidgets.QLabel("-")
    dashboard_dest_label.setWordWrap(True)
    status_layout.addWidget(dashboard_dest_label, 1, 1)
    status_layout.addWidget(QtWidgets.QLabel("📊 Status:"), 2, 0)
    dashboard_status_label = QtWidgets.QLabel("-")
    status_layout.addWidget(dashboard_status_label, 2, 1)
    dashboard_progress = QtWidgets.QProgressBar()
    dashboard_progress.setRange(0, 100)
    dashboard_progress.setValue(0)
    status_layout.addWidget(dashboard_progress, 3, 0, 1, 2)
    status_layout.addWidget(QtWidgets.QLabel("🧷 DAT:"), 4, 0)
    dashboard_dat_label = QtWidgets.QLabel("-")
    status_layout.addWidget(dashboard_dat_label, 4, 1)
    dashboard_layout.addWidget(status_group)

    dashboard_layout.addStretch(1)

    return DashboardUI(
        btn_home_source=btn_home_source,
        btn_home_dest=btn_home_dest,
        btn_home_go_sort=btn_home_go_sort,
        recent_paths_label=recent_paths_label,
        favorites_list=favorites_list,
        btn_fav_add=btn_fav_add,
        btn_fav_apply=btn_fav_apply,
        btn_fav_remove=btn_fav_remove,
        dashboard_source_label=dashboard_source_label,
        dashboard_dest_label=dashboard_dest_label,
        dashboard_status_label=dashboard_status_label,
        dashboard_progress=dashboard_progress,
        dashboard_dat_label=dashboard_dat_label,
    )
