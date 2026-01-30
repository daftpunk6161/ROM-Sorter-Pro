"""Small Qt dialog helpers for MVP UI."""

from __future__ import annotations

from typing import Optional, Tuple


def show_info(QtWidgets, parent, title: str, message: str) -> None:
    QtWidgets.QMessageBox.information(parent, title, message)


def show_warning(QtWidgets, parent, title: str, message: str) -> None:
    QtWidgets.QMessageBox.warning(parent, title, message)


def ask_question(
    QtWidgets,
    parent,
    title: str,
    message: str,
    default_no: bool = True,
) -> bool:
    buttons = QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
    default_button = QtWidgets.QMessageBox.No if default_no else QtWidgets.QMessageBox.Yes
    reply = QtWidgets.QMessageBox.question(parent, title, message, buttons, default_button)
    return reply == QtWidgets.QMessageBox.Yes


def get_open_file(
    QtWidgets,
    parent,
    title: str,
    start_dir: str = "",
    file_filter: str = "",
) -> Tuple[str, str]:
    return QtWidgets.QFileDialog.getOpenFileName(parent, title, start_dir, file_filter)


def get_existing_directory(
    QtWidgets,
    parent,
    title: str,
    start_dir: str = "",
) -> str:
    return QtWidgets.QFileDialog.getExistingDirectory(parent, title, start_dir)
