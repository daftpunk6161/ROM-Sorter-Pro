from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SplitterUI:
    main_splitter: Any
    left_panel: Any
    right_panel: Any
    left_layout: Any
    right_layout: Any


def build_splitter_ui(QtWidgets, QtCore, parent_layout: Any) -> SplitterUI:
    main_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
    parent_layout.addWidget(main_splitter, 1)

    left_panel = QtWidgets.QWidget()
    right_panel = QtWidgets.QWidget()
    main_splitter.addWidget(left_panel)
    main_splitter.addWidget(right_panel)
    main_splitter.setStretchFactor(0, 0)
    main_splitter.setStretchFactor(1, 1)

    left_layout = QtWidgets.QVBoxLayout(left_panel)
    right_layout = QtWidgets.QVBoxLayout(right_panel)

    return SplitterUI(
        main_splitter=main_splitter,
        left_panel=left_panel,
        right_panel=right_panel,
        left_layout=left_layout,
        right_layout=right_layout,
    )
