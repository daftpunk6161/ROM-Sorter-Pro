from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResultsTableUI:
    results_model: Any
    results_proxy: Any
    table: Any


def build_results_table_ui(
    QtWidgets,
    QtCore,
    ResultsTableModel,
    parent,
    results_stack: Any,
    logger,
    existing_model: Any | None = None,
    existing_proxy: Any | None = None,
    existing_table: Any | None = None,
) -> ResultsTableUI:
    if existing_model is not None and existing_proxy is not None and existing_table is not None:
        return ResultsTableUI(
            results_model=existing_model,
            results_proxy=existing_proxy,
            table=existing_table,
        )

    results_model = ResultsTableModel(parent)
    results_proxy = QtCore.QSortFilterProxyModel(parent)
    results_proxy.setSourceModel(results_model)
    results_proxy.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
    results_proxy.setSortCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
    results_proxy.setFilterKeyColumn(-1)

    table = QtWidgets.QTableView()
    table.setModel(results_proxy)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
    table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setSortingEnabled(True)
    table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
    header = table.horizontalHeader()
    header.setStretchLastSection(True)
    header.setSectionsMovable(True)
    try:
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    except Exception:
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    header.setMinimumSectionSize(110)
    try:
        header.setMaximumSectionSize(600)
    except Exception:
        logger.exception("Qt GUI: header max section size failed")

    results_stack.addWidget(table, 2)

    return ResultsTableUI(
        results_model=results_model,
        results_proxy=results_proxy,
        table=table,
    )
