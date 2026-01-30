from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class DBManagerUI:
    path_label: Any
    status_label: Any
    btn_init: Any
    btn_backup: Any
    btn_scan: Any
    btn_import: Any
    btn_migrate: Any
    btn_refresh: Any
    btn_open_folder: Any
    btn_close: Any


def build_db_manager_ui(QtWidgets, label_func: Callable[[str, str], str], parent, db_path: str) -> DBManagerUI:
    layout = QtWidgets.QVBoxLayout(parent)

    path_label = QtWidgets.QLabel(f"DB Path: {db_path}")
    path_label.setWordWrap(True)
    layout.addWidget(path_label)

    status_label = QtWidgets.QLabel("DB: unknown")
    status_label.setWordWrap(True)
    layout.addWidget(status_label)

    button_row = QtWidgets.QHBoxLayout()
    layout.addLayout(button_row)

    btn_init = QtWidgets.QPushButton("Initialize DB")
    btn_backup = QtWidgets.QPushButton("Backup DB")
    btn_scan = QtWidgets.QPushButton(label_func("Scan ROM Folder", "scan"))
    btn_import = QtWidgets.QPushButton("Import DAT")
    btn_migrate = QtWidgets.QPushButton("Migrate DB")
    btn_refresh = QtWidgets.QPushButton("Refresh")
    btn_open_folder = QtWidgets.QPushButton("Open Folder")
    btn_close = QtWidgets.QPushButton("Close")

    button_row.addWidget(btn_init)
    button_row.addWidget(btn_backup)
    button_row.addWidget(btn_scan)
    button_row.addWidget(btn_import)
    button_row.addWidget(btn_migrate)
    button_row.addWidget(btn_refresh)
    button_row.addWidget(btn_open_folder)
    button_row.addStretch(1)
    button_row.addWidget(btn_close)

    return DBManagerUI(
        path_label=path_label,
        status_label=status_label,
        btn_init=btn_init,
        btn_backup=btn_backup,
        btn_scan=btn_scan,
        btn_import=btn_import,
        btn_migrate=btn_migrate,
        btn_refresh=btn_refresh,
        btn_open_folder=btn_open_folder,
        btn_close=btn_close,
    )
