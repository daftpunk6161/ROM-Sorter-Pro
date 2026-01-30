from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SidebarUI:
    sidebar: Any
    btn_nav_dashboard: Any
    btn_nav_sort: Any
    btn_nav_conversions: Any
    btn_nav_settings: Any
    btn_nav_reports: Any
    sidebar_status_label: Any
    sidebar_summary_label: Any


def build_sidebar_ui(QtWidgets) -> SidebarUI:
    sidebar = QtWidgets.QFrame()
    sidebar.setMinimumWidth(180)
    sidebar_layout = QtWidgets.QVBoxLayout(sidebar)
    sidebar_layout.setContentsMargins(8, 8, 8, 8)
    sidebar_layout.setSpacing(6)

    btn_nav_dashboard = QtWidgets.QPushButton("Home")
    btn_nav_sort = QtWidgets.QPushButton("Sortieren")
    btn_nav_conversions = QtWidgets.QPushButton("Konvertieren")
    btn_nav_settings = QtWidgets.QPushButton("Einstellungen")
    btn_nav_reports = QtWidgets.QPushButton("Reports")
    for btn in (
        btn_nav_dashboard,
        btn_nav_sort,
        btn_nav_conversions,
        btn_nav_settings,
        btn_nav_reports,
    ):
        btn.setMinimumHeight(32)
        sidebar_layout.addWidget(btn)

    sidebar_layout.addStretch(1)
    sidebar_layout.addWidget(QtWidgets.QLabel("Status"))
    sidebar_status_label = QtWidgets.QLabel("-")
    sidebar_summary_label = QtWidgets.QLabel("-")
    sidebar_status_label.setWordWrap(True)
    sidebar_summary_label.setWordWrap(True)
    sidebar_layout.addWidget(sidebar_status_label)
    sidebar_layout.addWidget(sidebar_summary_label)

    return SidebarUI(
        sidebar=sidebar,
        btn_nav_dashboard=btn_nav_dashboard,
        btn_nav_sort=btn_nav_sort,
        btn_nav_conversions=btn_nav_conversions,
        btn_nav_settings=btn_nav_settings,
        btn_nav_reports=btn_nav_reports,
        sidebar_status_label=sidebar_status_label,
        sidebar_summary_label=sidebar_summary_label,
    )
