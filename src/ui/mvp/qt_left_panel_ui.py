from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LeftPanelUI:
    left_tabs: Any
    workflow_tabs: Any


def build_left_panel_ui(
    QtWidgets,
    left_layout: Any,
    main_status_group: Any,
    paths_group: Any,
    actions_group: Any,
    presets_group: Any,
    queue_group: Any,
) -> LeftPanelUI:
    left_tabs = QtWidgets.QTabWidget()

    left_main_tab = QtWidgets.QWidget()
    left_main_layout = QtWidgets.QVBoxLayout(left_main_tab)
    workflow_tabs = QtWidgets.QTabWidget()

    status_tab = QtWidgets.QWidget()
    status_layout = QtWidgets.QVBoxLayout(status_tab)
    status_layout.addWidget(main_status_group)
    status_layout.addStretch(1)

    paths_tab = QtWidgets.QWidget()
    paths_tab_layout = QtWidgets.QVBoxLayout(paths_tab)
    paths_tab_layout.addWidget(paths_group)
    paths_tab_layout.addStretch(1)

    actions_tab = QtWidgets.QWidget()
    actions_tab_layout = QtWidgets.QVBoxLayout(actions_tab)
    actions_tab_layout.addWidget(actions_group)
    actions_tab_layout.addStretch(1)

    workflow_tabs.addTab(status_tab, "Status")
    workflow_tabs.addTab(paths_tab, "Pfade")
    workflow_tabs.addTab(actions_tab, "Aktionen")

    left_main_layout.addWidget(workflow_tabs, 1)

    left_presets_tab = QtWidgets.QWidget()
    left_presets_layout = QtWidgets.QVBoxLayout(left_presets_tab)
    left_presets_layout.addWidget(presets_group)
    left_presets_layout.addWidget(queue_group)
    left_presets_layout.addStretch(1)

    left_tabs.addTab(left_main_tab, "Workflow")
    left_tabs.addTab(left_presets_tab, "Presets & Queue")
    left_layout.addWidget(left_tabs, 1)

    return LeftPanelUI(left_tabs=left_tabs, workflow_tabs=workflow_tabs)
