from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResultsTabsUI:
    results_tabs: Any
    results_stack: Any
    details_stack: Any
    filter_sidebar: Any
    tab_index_results: int
    tab_index_details: int
    tab_index_filters: int


def build_results_tabs_ui(
    QtWidgets,
    QtCore,
    right_layout: Any,
    filters_group: Any,
) -> ResultsTabsUI:
    results_tabs = QtWidgets.QTabWidget()
    right_layout.addWidget(results_tabs, 1)

    results_page = QtWidgets.QWidget()
    results_page_layout = QtWidgets.QVBoxLayout(results_page)
    results_stack = QtWidgets.QVBoxLayout()
    results_page_layout.addLayout(results_stack, 1)
    tab_index_results = results_tabs.addTab(results_page, "Ergebnisse")

    details_page = QtWidgets.QWidget()
    details_page_layout = QtWidgets.QVBoxLayout(details_page)
    details_stack = QtWidgets.QVBoxLayout()
    details_page_layout.addLayout(details_stack, 1)
    tab_index_details = results_tabs.addTab(details_page, "Details")

    filters_page = QtWidgets.QWidget()
    filters_page_layout = QtWidgets.QVBoxLayout(filters_page)
    filters_page_layout.addWidget(filters_group)
    filters_page_layout.addStretch(1)
    tab_index_filters = results_tabs.addTab(filters_page, "Filter")

    return ResultsTabsUI(
        results_tabs=results_tabs,
        results_stack=results_stack,
        details_stack=details_stack,
        filter_sidebar=filters_group,
        tab_index_results=tab_index_results,
        tab_index_details=tab_index_details,
        tab_index_filters=tab_index_filters,
    )
