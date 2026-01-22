"""ROM Sorter Pro - MVP Qt GUI (GUI-first).

MVP features:
- Source folder picker
- Destination folder picker
- Buttons: Scan, Preview Sort (Dry-run), Execute Sort, Cancel
- Progress bar + live log (ring buffer)
- Result table: InputPath, DetectedConsole/Type, Confidence, Signals, Candidates, PlannedTargetPath, Action, Status/Error

Threading model:
- QThread + QObject worker
- UI updates only via Qt signals

Qt binding preference (deterministic):
- PySide6 (preferred)
- PyQt5
"""

from __future__ import annotations

import importlib
import os
import logging
import time
import shutil
import sqlite3
import sys
import traceback
import threading
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional, cast


def _load_qt():
    """Load a Qt binding and return (QtWidgets, QtCore, QtGui, binding_name)."""

    for binding_name, base in (("pyside6", "PySide6"), ("pyqt5", "PyQt5")):
        try:
            QtCore = importlib.import_module(f"{base}.QtCore")
            QtGui = importlib.import_module(f"{base}.QtGui")
            QtWidgets = importlib.import_module(f"{base}.QtWidgets")
            return QtWidgets, QtCore, QtGui, binding_name
        except Exception:
            continue

    raise ImportError("No Qt binding found (PySide6/PyQt5)")


def run() -> int:
    QtWidgets, QtCore, QtGui, binding = _load_qt()

    Signal = getattr(QtCore, "Signal", None) or getattr(QtCore, "pyqtSignal")
    Slot = getattr(QtCore, "Slot", None) or getattr(QtCore, "pyqtSlot")

    from ...app.api import (
        CancelToken,
        ConflictPolicy,
        ConversionAuditReport,
        ConversionMode,
        ScanItem,
        ScanResult,
        SortPlan,
        SortReport,
        SortMode,
        audit_conversion_candidates,
        build_dat_index,
        execute_sort,
        filter_scan_items,
        infer_languages_and_version_from_name,
        infer_region_from_name,
        load_sort_resume_state,
        plan_sort,
        run_scan,
    )
    from ...app import db_controller
    from ...config.io import load_config, save_config
    from ...core.dat_index_sqlite import DatIndexSqlite
    from ...database.db_paths import get_rom_db_path
    from ...ui.theme_manager import ThemeManager
    from ...utils.external_tools import probe_igir, probe_wud2app, probe_wudcompress, igir_plan, igir_execute
    from .export_utils import (
        audit_report_to_dict,
        plan_report_to_dict,
        scan_report_to_dict,
        write_audit_csv,
        write_json,
        write_plan_csv,
        write_scan_csv,
    )
    from .model_utils import (
        format_candidates,
        format_confidence,
        format_signals,
        rom_display_name,
    )

    class WorkerSignals(QtCore.QObject):
        phase_changed = Signal(str, int)
        progress = Signal(int, int)
        log = Signal(str)
        action_status = Signal(int, str)
        finished = Signal(object)
        failed = Signal(str, str)

    class ExportWorker(QtCore.QObject):
        finished = Signal(str)
        failed = Signal(str)

        def __init__(self, label: str, task):
            super().__init__()
            self._label = label
            self._task = task

        @Slot()
        def run(self) -> None:
            try:
                self._task()
                self.finished.emit(self._label)
            except Exception as exc:
                self.failed.emit(str(exc))

    class DatIndexWorker(QtCore.QObject):
        finished = Signal(object)
        failed = Signal(str)

        def __init__(self, task):
            super().__init__()
            self._task = task

        @Slot()
        def run(self) -> None:
            try:
                result = self._task()
                self.finished.emit(result)
            except Exception as exc:
                self.failed.emit(str(exc))

    class IgirPlanWorker(QtCore.QObject):
        log = Signal(str)
        finished = Signal(object)
        failed = Signal(str)

        def __init__(
            self,
            input_path: str,
            output_dir: str,
            report_dir: str,
            temp_dir: str,
            cancel_token: CancelToken,
        ):
            super().__init__()
            self._input_path = input_path
            self._output_dir = output_dir
            self._report_dir = report_dir
            self._temp_dir = temp_dir
            self._cancel_token = cancel_token

        @Slot()
        def run(self) -> None:
            try:
                result = igir_plan(
                    input_path=self._input_path,
                    output_dir=self._output_dir,
                    dest_root=self._output_dir,
                    report_dir=self._report_dir,
                    temp_dir=self._temp_dir,
                    log_cb=lambda msg: self.log.emit(str(msg)),
                    cancel_token=self._cancel_token,
                )
                self.finished.emit(result)
            except Exception as exc:
                self.failed.emit(str(exc))

    class IgirExecuteWorker(QtCore.QObject):
        log = Signal(str)
        finished = Signal(object)
        failed = Signal(str)

        def __init__(
            self,
            input_path: str,
            output_dir: str,
            temp_dir: str,
            cancel_token: CancelToken,
            plan_confirmed: bool,
            explicit_user_action: bool,
        ):
            super().__init__()
            self._input_path = input_path
            self._output_dir = output_dir
            self._temp_dir = temp_dir
            self._cancel_token = cancel_token
            self._plan_confirmed = plan_confirmed
            self._explicit_user_action = explicit_user_action

        @Slot()
        def run(self) -> None:
            try:
                result = igir_execute(
                    input_path=self._input_path,
                    output_dir=self._output_dir,
                    dest_root=self._output_dir,
                    temp_dir=self._temp_dir,
                    log_cb=lambda msg: self.log.emit(str(msg)),
                    cancel_token=self._cancel_token,
                    plan_confirmed=self._plan_confirmed,
                    explicit_user_action=self._explicit_user_action,
                )
                self.finished.emit(result)
            except Exception as exc:
                self.failed.emit(str(exc))

    class QtLogHandler(logging.Handler):
        def __init__(self, emit_fn):
            super().__init__()
            self._emit_fn = emit_fn
            self._last_message = ""
            self._last_ts = 0.0
            self._qt_gui_handler = False

        def emit(self, record):
            try:
                msg = self.format(record)
            except Exception:
                msg = record.getMessage()
            now = time.monotonic()
            if msg == self._last_message and (now - self._last_ts) < 0.5:
                return
            self._last_message = msg
            self._last_ts = now
            try:
                self._emit_fn(msg)
            except Exception:
                return

    class OperationWorker(QtCore.QObject):
        def __init__(
            self,
            op: str,
            source: str,
            dest: str,
            output_dir: str,
            temp_dir: str,
            mode: str,
            on_conflict: str,
            conversion_mode: ConversionMode,
            scan_result: Optional[ScanResult],
            sort_plan: Optional[SortPlan],
            start_index: int,
            only_indices: Optional[list[int]],
            resume_path: Optional[str],
            cancel_token: CancelToken,
            signals: WorkerSignals,
        ):
            super().__init__()
            self.op = op
            self.source = source
            self.dest = dest
            self.output_dir = output_dir
            self.temp_dir = temp_dir
            self.mode = mode
            self.on_conflict = on_conflict
            self.conversion_mode = conversion_mode
            self.scan_result = scan_result
            self.sort_plan = sort_plan
            self.start_index = int(start_index)
            self.only_indices = list(only_indices) if only_indices else None
            self.resume_path = resume_path
            self.cancel_token = cancel_token
            self.signals = signals

        @Slot()
        def run(self) -> None:
            try:
                self.signals.log.emit(f"Qt binding: {binding}")

                if self.op == "scan":
                    self.signals.phase_changed.emit("scan", 0)
                    self.signals.log.emit(f"Scan started: source={self.source}")
                    scan = run_scan(
                        self.source,
                        config=None,
                        progress_cb=lambda c, t: self.signals.progress.emit(int(c), int(t)),
                        log_cb=lambda msg: self.signals.log.emit(str(msg)),
                        cancel_token=self.cancel_token,
                    )
                    self.signals.log.emit(f"Scan finished: items={len(scan.items)} cancelled={scan.cancelled}")
                    self.signals.finished.emit(scan)
                    return

                if self.op == "plan":
                    if self.scan_result is None:
                        raise RuntimeError("No scan result available")
                    self.signals.phase_changed.emit("plan", len(self.scan_result.items))
                    self.signals.log.emit(
                        f"Plan started: items={len(self.scan_result.items)} mode={self.mode} conflict={self.on_conflict}"
                    )
                    plan = plan_sort(
                        self.scan_result,
                        self.dest,
                        config=None,
                        mode=cast(SortMode, self.mode),
                        on_conflict=cast(ConflictPolicy, self.on_conflict),
                        cancel_token=self.cancel_token,
                    )
                    self.signals.log.emit(f"Plan finished: actions={len(plan.actions)}")
                    self.signals.finished.emit(plan)
                    return

                if self.op == "execute":
                    if self.sort_plan is None:
                        raise RuntimeError("No sort plan available")
                    total_actions = len(self.sort_plan.actions)
                    if self.only_indices:
                        filtered = [i for i in self.only_indices if 0 <= int(i) < total_actions]
                        total = len(set(filtered))
                    elif self.start_index > 0:
                        total = max(0, total_actions - int(self.start_index))
                    else:
                        total = total_actions
                    if self.conversion_mode != "all":
                        convert_count = sum(1 for action in self.sort_plan.actions if action.action == "convert")
                        if self.conversion_mode == "only":
                            total = convert_count
                        elif self.conversion_mode == "skip":
                            total = max(0, total_actions - convert_count)
                    self.signals.phase_changed.emit("execute", total)
                    self.signals.log.emit(
                        f"Execute started: total={total} resume={self.start_index} only_indices={self.only_indices} conversion_mode={self.conversion_mode}"
                    )
                    report = execute_sort(
                        self.sort_plan,
                        progress_cb=lambda c, t: self.signals.progress.emit(int(c), int(t)),
                        log_cb=lambda msg: self.signals.log.emit(str(msg)),
                        action_status_cb=lambda i, status: self.signals.action_status.emit(int(i), str(status)),
                        cancel_token=self.cancel_token,
                        dry_run=False,
                        resume_path=self.resume_path,
                        start_index=self.start_index,
                        only_indices=self.only_indices,
                        conversion_mode=self.conversion_mode,
                    )
                    self.signals.log.emit(
                        f"Execute finished: processed={report.processed} copied={report.copied} moved={report.moved} errors={len(report.errors)} cancelled={report.cancelled}"
                    )
                    self.signals.finished.emit(report)
                    return

                if self.op == "audit":
                    self.signals.phase_changed.emit("audit", 0)
                    self.signals.log.emit(f"Audit started: source={self.source}")
                    report = audit_conversion_candidates(
                        self.source,
                        config=None,
                        progress_cb=lambda c, t: self.signals.progress.emit(int(c), int(t)),
                        log_cb=lambda msg: self.signals.log.emit(str(msg)),
                        cancel_token=self.cancel_token,
                        include_disabled=True,
                    )
                    self.signals.log.emit(
                        f"Audit finished: items={len(report.items)} cancelled={report.cancelled}"
                    )
                    self.signals.finished.emit(report)
                    return

                raise RuntimeError(f"Unknown operation: {self.op}")

            except Exception as exc:
                self.signals.failed.emit(str(exc), traceback.format_exc())

    class DropLineEdit(QtWidgets.QLineEdit):
        def __init__(self, on_drop, *args, enabled: bool = True, **kwargs):
            super().__init__(*args, **kwargs)
            self._on_drop = on_drop
            self.setAcceptDrops(bool(enabled))

        def dragEnterEvent(self, event):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            else:
                event.ignore()

        def dropEvent(self, event):
            urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
            if not urls:
                return
            try:
                path = Path(urls[0].toLocalFile())
                if path.is_file():
                    path = path.parent
                if path.exists():
                    self._on_drop(str(path))
            except Exception:
                return

    class DBManagerDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Database Manager")
            self.resize(520, 220)

            self._db_path = get_rom_db_path()
            self._task_thread = None

            layout = QtWidgets.QVBoxLayout(self)

            self.path_label = QtWidgets.QLabel(f"DB Path: {self._db_path}")
            self.path_label.setWordWrap(True)
            layout.addWidget(self.path_label)

            self.status_label = QtWidgets.QLabel("DB: unknown")
            self.status_label.setWordWrap(True)
            layout.addWidget(self.status_label)

            button_row = QtWidgets.QHBoxLayout()
            layout.addLayout(button_row)

            self.btn_init = QtWidgets.QPushButton("Initialize DB")
            self.btn_backup = QtWidgets.QPushButton("Backup DB")
            self.btn_scan = QtWidgets.QPushButton("Scan ROM Folder")
            self.btn_import = QtWidgets.QPushButton("Import DAT")
            self.btn_migrate = QtWidgets.QPushButton("Migrate DB")
            self.btn_refresh = QtWidgets.QPushButton("Refresh")
            self.btn_open_folder = QtWidgets.QPushButton("Open Folder")
            self.btn_close = QtWidgets.QPushButton("Close")

            button_row.addWidget(self.btn_init)
            button_row.addWidget(self.btn_backup)
            button_row.addWidget(self.btn_scan)
            button_row.addWidget(self.btn_import)
            button_row.addWidget(self.btn_migrate)
            button_row.addWidget(self.btn_refresh)
            button_row.addWidget(self.btn_open_folder)
            button_row.addStretch(1)
            button_row.addWidget(self.btn_close)

            self.btn_init.clicked.connect(self._init_db)
            self.btn_backup.clicked.connect(self._backup_db)
            self.btn_scan.clicked.connect(self._scan_roms)
            self.btn_import.clicked.connect(self._import_dat)
            self.btn_migrate.clicked.connect(self._migrate_db)
            self.btn_refresh.clicked.connect(self._refresh)
            self.btn_open_folder.clicked.connect(self._open_folder)
            self.btn_close.clicked.connect(self.accept)

            self._refresh()

        def _refresh(self) -> None:
            db_path = self._db_path
            db_file = Path(db_path)
            if not db_file.exists():
                self.status_label.setText("DB: not found")
                return
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='roms'")
                has_roms = cur.fetchone() is not None
                rom_count = 0
                console_count = 0
                if has_roms:
                    cur.execute("SELECT COUNT(*) FROM roms")
                    rom_count = int(cur.fetchone()[0])
                    cur.execute("SELECT COUNT(DISTINCT console) FROM roms")
                    console_count = int(cur.fetchone()[0])
                conn.close()
                if has_roms:
                    self.status_label.setText(
                        f"DB: ok | ROMs: {rom_count:,} | Consoles: {console_count:,}"
                    )
                else:
                    self.status_label.setText("DB: ok (no 'roms' table)")
            except Exception as exc:
                self.status_label.setText(f"DB: error ({exc})")

        def _init_db(self) -> None:
            db_path = self._db_path
            db_file = Path(db_path)
            try:
                db_file.parent.mkdir(parents=True, exist_ok=True)
                db_controller.init_db(db_path)
                self.status_label.setText("DB: initialized")
            except Exception as exc:
                self.status_label.setText(f"DB init failed ({exc})")

        def _backup_db(self) -> None:
            db_path = Path(self._db_path)
            if not db_path.exists():
                self.status_label.setText("DB backup failed (missing db)")
                return
            try:
                backup_path = db_controller.backup_db(str(db_path))
                self.status_label.setText(f"DB backup: {backup_path}")
            except Exception as exc:
                self.status_label.setText(f"DB backup failed ({exc})")

        def _run_task(self, label: str, func) -> None:
            class _TaskWorker(QtCore.QObject):
                finished = Signal(object)
                failed = Signal(str)

                def __init__(self, task):
                    super().__init__()
                    self._task = task

                @Slot()
                def run(self):
                    try:
                        result = self._task()
                        self.finished.emit(result)
                    except Exception as exc:
                        self.failed.emit(str(exc))

            if self._task_thread is not None:
                return

            self.status_label.setText(f"DB: {label}...")

            worker = _TaskWorker(func)
            thread = QtCore.QThread()
            self._task_thread = thread

            worker.moveToThread(thread)
            thread.started.connect(worker.run)

            def _cleanup():
                thread.quit()
                thread.wait()
                self._task_thread = None

            worker.finished.connect(lambda result: self._on_task_done(label, result))
            worker.finished.connect(_cleanup)
            worker.failed.connect(lambda msg: self._on_task_failed(label, msg))
            worker.failed.connect(_cleanup)
            thread.start()

        def _ensure_repo_root(self) -> None:
            root = Path(__file__).resolve().parents[3]
            root_str = str(root)
            if root_str not in sys.path:
                sys.path.insert(0, root_str)

        def _on_task_done(self, label: str, result: object) -> None:
            self.status_label.setText(f"DB: {label} fertig ({result})")
            self._refresh()

        def _on_task_failed(self, label: str, msg: str) -> None:
            self.status_label.setText(f"DB: {label} failed ({msg})")

        def _scan_roms(self) -> None:
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select ROM Folder")
            if not directory:
                return

            def task():
                count = db_controller.scan_roms(directory, db_path=self._db_path, recursive=True)
                return f"{count} ROMs"

            self._run_task("scan", task)

        def _import_dat(self) -> None:
            dat_file, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Import DAT",
                "",
                "DAT/XML Files (*.dat *.xml);;All Files (*)",
            )
            if not dat_file:
                return

            def task():
                count = db_controller.import_dat(dat_file, db_path=self._db_path)
                return f"{count} updated"

            self._run_task("import", task)

        def _migrate_db(self) -> None:
            def task():
                ok = db_controller.migrate_db(self._db_path)
                return "ok" if ok else "failed"

            self._run_task("migrate", task)

        def _open_folder(self) -> None:
            try:
                folder = str(Path(self._db_path).parent)
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder))
            except Exception:
                return

    class MainWindow(QtWidgets.QMainWindow):
        log_signal = Signal(str)
        tools_signal = Signal(object)

        def __init__(self):
            super().__init__()

            self.setWindowTitle("ROM Sorter Pro - MVP GUI")
            self.resize(1100, 700)

            self._cancel_token = CancelToken()
            self._thread = None
            self._worker = None

            self._scan_result: Optional[ScanResult] = None
            self._sort_plan: Optional[SortPlan] = None
            self._audit_report: Optional[ConversionAuditReport] = None
            self._export_thread: Optional[QtCore.QThread] = None
            self._export_worker: Optional[ExportWorker] = None
            self._igir_thread: Optional[QtCore.QThread] = None
            self._igir_worker: Optional[QtCore.QObject] = None
            self._igir_cancel_token: Optional[CancelToken] = None
            self._igir_plan_ready = False
            self._igir_diff_csv: Optional[str] = None
            self._igir_diff_json: Optional[str] = None
            self._failed_action_indices: set[int] = set()
            self._resume_path = str((Path(__file__).resolve().parents[3] / "cache" / "last_sort_resume.json").resolve())

            self._theme_manager = ThemeManager()
            self._syncing_paths = False
            self._log_visible = True

            self._last_view: str = "scan"  # scan|plan
            self._dat_index: Optional[DatIndexSqlite] = None
            self._dat_status_timer = QtCore.QTimer(self)
            self._dat_status_timer.setInterval(800)
            self._dat_status_timer.timeout.connect(self._poll_dat_status)
            self._dat_index_thread: Optional[QtCore.QThread] = None
            self._dat_index_worker: Optional[DatIndexWorker] = None
            self._dat_index_cancel_token: Optional[CancelToken] = None

            central = QtWidgets.QWidget()
            self.setCentralWidget(central)

            menu_bar = self.menuBar()
            export_menu = menu_bar.addMenu("Export")
            self.menu_export_scan_csv = QtGui.QAction("Scan CSV", self)
            self.menu_export_scan_json = QtGui.QAction("Scan JSON", self)
            self.menu_export_plan_csv = QtGui.QAction("Plan CSV", self)
            self.menu_export_plan_json = QtGui.QAction("Plan JSON", self)
            self.menu_export_audit_csv = QtGui.QAction("Audit CSV", self)
            self.menu_export_audit_json = QtGui.QAction("Audit JSON", self)
            export_menu.addAction(self.menu_export_scan_csv)
            export_menu.addAction(self.menu_export_scan_json)
            export_menu.addSeparator()
            export_menu.addAction(self.menu_export_plan_csv)
            export_menu.addAction(self.menu_export_plan_json)
            export_menu.addSeparator()
            export_menu.addAction(self.menu_export_audit_csv)
            export_menu.addAction(self.menu_export_audit_json)

            root_layout = QtWidgets.QVBoxLayout(central)

            tabs = QtWidgets.QTabWidget()
            root_layout.addWidget(tabs)

            main_tab = QtWidgets.QWidget()
            settings_tab = QtWidgets.QWidget()
            tools_tab = QtWidgets.QWidget()
            conversions_tab = QtWidgets.QWidget()
            igir_tab = QtWidgets.QWidget()
            tabs.addTab(main_tab, "Haupt")
            tabs.addTab(conversions_tab, "Konvertierungen")
            tabs.addTab(igir_tab, "IGIR")
            tabs.addTab(settings_tab, "Einstellungen")
            show_external_tools = False
            if show_external_tools:
                tabs.addTab(tools_tab, "External Tools")

            main_layout = QtWidgets.QVBoxLayout(main_tab)
            conversions_layout = QtWidgets.QVBoxLayout(conversions_tab)
            igir_layout = QtWidgets.QVBoxLayout(igir_tab)
            settings_layout = QtWidgets.QVBoxLayout(settings_tab)
            tools_layout = QtWidgets.QVBoxLayout(tools_tab)

            paths_group = QtWidgets.QGroupBox("Pfade")
            actions_group = QtWidgets.QGroupBox("Aktionen")
            filters_group = QtWidgets.QGroupBox("Filter")

            paths_layout = QtWidgets.QGridLayout(paths_group)
            actions_layout = QtWidgets.QGridLayout(actions_group)
            filters_layout = QtWidgets.QGridLayout(filters_group)

            for grid_layout in (paths_layout, actions_layout, filters_layout):
                grid_layout.setHorizontalSpacing(10)
                grid_layout.setVerticalSpacing(6)

            sections_row = QtWidgets.QHBoxLayout()
            sections_row.addWidget(paths_group, 2)
            sections_row.addWidget(actions_group, 1)
            sections_row.addWidget(filters_group, 2)
            main_layout.addLayout(sections_row)

            dnd_enabled = self._is_drag_drop_enabled()
            self.source_edit = DropLineEdit(self._on_drop_source, enabled=dnd_enabled)
            self.dest_edit = DropLineEdit(self._on_drop_dest, enabled=dnd_enabled)
            self.source_edit.setPlaceholderText("ROM-Quelle auswählen")
            self.dest_edit.setPlaceholderText("Zielordner auswählen")

            self.btn_source = QtWidgets.QPushButton("Quelle wählen…")
            self.btn_dest = QtWidgets.QPushButton("Ziel wählen…")
            self.btn_source.setMinimumWidth(150)
            self.btn_dest.setMinimumWidth(150)
            self.btn_open_dest = QtWidgets.QPushButton("Ziel öffnen")

            if show_external_tools:
                self.output_edit = DropLineEdit(self._on_drop_output, tools_tab, enabled=dnd_enabled)
                self.temp_edit = DropLineEdit(self._on_drop_temp, tools_tab, enabled=dnd_enabled)
                self.output_edit.setPlaceholderText("Optional output folder for external tool results")
                self.temp_edit.setPlaceholderText("Optional temp folder for external tool processing")

                self.btn_output = QtWidgets.QPushButton("Select Output…")
                self.btn_temp = QtWidgets.QPushButton("Select Temp…")
                self.btn_output.setMinimumWidth(150)
                self.btn_temp.setMinimumWidth(150)
            else:
                self.output_edit = None
                self.temp_edit = None
                self.btn_output = None
                self.btn_temp = None

            self.igir_exe_edit = QtWidgets.QLineEdit()
            self.igir_args_edit = QtWidgets.QPlainTextEdit()
            self.igir_args_edit.setPlaceholderText("One argument per line. Use {input} and {output_dir}.")
            self.btn_igir_browse = QtWidgets.QPushButton("IGIR wählen…")
            self.btn_igir_save = QtWidgets.QPushButton("IGIR speichern")
            self.btn_igir_probe = QtWidgets.QPushButton("IGIR prüfen")
            self.btn_igir_plan = QtWidgets.QPushButton("IGIR Plan")
            self.btn_igir_execute = QtWidgets.QPushButton("IGIR Execute")
            self.btn_igir_execute.setEnabled(False)
            self.btn_igir_cancel = QtWidgets.QPushButton("IGIR abbrechen")
            self.btn_igir_cancel.setEnabled(False)
            self.igir_status_label = QtWidgets.QLabel("Status: -")
            self.igir_source_edit = QtWidgets.QLineEdit()
            self.igir_dest_edit = QtWidgets.QLineEdit()
            self.igir_source_edit.setPlaceholderText("Quelle (aus Haupt-Tab)")
            self.igir_dest_edit.setPlaceholderText("Ziel (aus Haupt-Tab)")

            self.mode_combo = QtWidgets.QComboBox()
            self.mode_combo.addItems(["copy", "move"])

            self.conflict_combo = QtWidgets.QComboBox()
            self.conflict_combo.addItems(["rename", "skip", "overwrite"])

            self.lang_filter = QtWidgets.QComboBox()
            self.lang_filter.addItems(["All"])
            self.lang_filter.setMinimumWidth(160)

            self.ver_filter = QtWidgets.QComboBox()
            self.ver_filter.addItems(["All"])
            self.ver_filter.setMinimumWidth(160)

            self.region_filter = QtWidgets.QComboBox()
            self.region_filter.addItems(["All"])
            self.region_filter.setMinimumWidth(160)

            self.ext_filter_edit = QtWidgets.QLineEdit()
            self.ext_filter_edit.setPlaceholderText(".iso,.chd,.zip")
            self.min_size_edit = QtWidgets.QLineEdit()
            self.min_size_edit.setPlaceholderText("Min MB")
            self.max_size_edit = QtWidgets.QLineEdit()
            self.max_size_edit.setPlaceholderText("Max MB")
            self.min_size_edit.setFixedWidth(90)
            self.max_size_edit.setFixedWidth(90)
            size_validator = QtGui.QDoubleValidator(0.0, 1_000_000_000.0, 3, self)
            size_validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
            self.min_size_edit.setValidator(size_validator)
            self.max_size_edit.setValidator(size_validator)

            self.btn_clear_filters = QtWidgets.QPushButton("Filter zurücksetzen")

            self.dedupe_checkbox = QtWidgets.QCheckBox("Duplikate vermeiden (Europa → USA)")
            self.dedupe_checkbox.setChecked(True)
            self.hide_unknown_checkbox = QtWidgets.QCheckBox("Unbekannt / Niedrige Sicherheit ausblenden")
            self.hide_unknown_checkbox.setChecked(False)
            self.chk_console_folders = QtWidgets.QCheckBox("Konsolenordner erstellen")
            self.chk_region_subfolders = QtWidgets.QCheckBox("Regionsordner erstellen")
            self.chk_preserve_structure = QtWidgets.QCheckBox("Quell-Unterordner beibehalten")
            self.dat_status = QtWidgets.QLabel("DAT: unbekannt")
            self.btn_add_dat = QtWidgets.QPushButton("DAT-Ordner hinzufügen…")
            self.btn_refresh_dat = QtWidgets.QPushButton("DAT Index bauen")
            self.btn_cancel_dat = QtWidgets.QPushButton("DAT Abbrechen")
            self.btn_cancel_dat.setEnabled(False)
            self.dat_status.setStyleSheet("color: #666;")
            self.dat_auto_load_checkbox = QtWidgets.QCheckBox("DATs beim Start automatisch laden")
            self.dat_auto_load_checkbox.setChecked(False)
            self.btn_clear_dat_cache = QtWidgets.QPushButton("DAT-Cache löschen")

            self.theme_combo = QtWidgets.QComboBox()
            theme_names = self._theme_manager.get_theme_names()
            if "Auto" not in theme_names:
                theme_names = ["Auto"] + theme_names
            self.theme_combo.addItems(theme_names)
            current_theme = self._theme_manager.get_current_theme_name()
            idx_theme = self.theme_combo.findText(current_theme)
            self.theme_combo.setCurrentIndex(idx_theme if idx_theme >= 0 else 0)

            self.db_status = QtWidgets.QLabel("DB: ")
            self.btn_db_manager = QtWidgets.QPushButton("DB-Manager öffnen")

            self.tools_group = QtWidgets.QGroupBox("External Tools Status")
            tools_group_layout = QtWidgets.QGridLayout(self.tools_group)
            self.wud2app_version = QtWidgets.QLabel("unknown")
            self.wud2app_probe = QtWidgets.QLabel("probe: pending")
            self.wudcompress_version = QtWidgets.QLabel("unknown")
            self.wudcompress_probe = QtWidgets.QLabel("probe: pending")
            tools_group_layout.addWidget(QtWidgets.QLabel("wud2app version:"), 0, 0)
            tools_group_layout.addWidget(self.wud2app_version, 0, 1)
            tools_group_layout.addWidget(QtWidgets.QLabel("wud2app probe:"), 1, 0)
            tools_group_layout.addWidget(self.wud2app_probe, 1, 1)
            tools_group_layout.addWidget(QtWidgets.QLabel("wudcompress version:"), 2, 0)
            tools_group_layout.addWidget(self.wudcompress_version, 2, 1)
            tools_group_layout.addWidget(QtWidgets.QLabel("wudcompress probe:"), 3, 0)
            tools_group_layout.addWidget(self.wudcompress_probe, 3, 1)

            paths_layout.addWidget(QtWidgets.QLabel("Quelle:"), 0, 0)
            paths_layout.addWidget(self.source_edit, 0, 1)
            paths_layout.addWidget(self.btn_source, 0, 2)

            paths_layout.addWidget(QtWidgets.QLabel("Ziel:"), 1, 0)
            paths_layout.addWidget(self.dest_edit, 1, 1)
            paths_layout.addWidget(self.btn_dest, 1, 2)
            paths_layout.addWidget(self.btn_open_dest, 1, 3)

            self.source_edit.textChanged.connect(self._on_source_text_changed)
            self.dest_edit.textChanged.connect(self._on_dest_text_changed)

            paths_layout.setColumnStretch(1, 1)

            actions_layout.addWidget(QtWidgets.QLabel("Aktion:"), 0, 0)
            actions_layout.addWidget(self.mode_combo, 0, 1)

            actions_layout.addWidget(QtWidgets.QLabel("Bei Konflikt:"), 1, 0)
            actions_layout.addWidget(self.conflict_combo, 1, 1)

            actions_layout.setColumnStretch(1, 1)

            filters_layout.addWidget(QtWidgets.QLabel("Sprachfilter:"), 0, 0)
            filters_layout.addWidget(self.lang_filter, 0, 1)

            filters_layout.addWidget(QtWidgets.QLabel("Versionsfilter:"), 1, 0)
            filters_layout.addWidget(self.ver_filter, 1, 1)

            filters_layout.addWidget(QtWidgets.QLabel("Regionsfilter:"), 2, 0)
            filters_layout.addWidget(self.region_filter, 2, 1)

            filters_layout.addWidget(self.dedupe_checkbox, 3, 1)
            filters_layout.addWidget(self.hide_unknown_checkbox, 3, 2)

            filters_layout.addWidget(QtWidgets.QLabel("Erweiterungsfilter:"), 4, 0)
            filters_layout.addWidget(self.ext_filter_edit, 4, 1)

            size_row = QtWidgets.QHBoxLayout()
            size_row.addWidget(QtWidgets.QLabel("Min (MB):"))
            size_row.addWidget(self.min_size_edit)
            size_row.addSpacing(10)
            size_row.addWidget(QtWidgets.QLabel("Max (MB):"))
            size_row.addWidget(self.max_size_edit)
            size_row.addStretch(1)
            filters_layout.addLayout(size_row, 5, 0, 1, 4, QtCore.Qt.AlignLeft)

            filters_layout.addWidget(self.btn_clear_filters, 6, 2, 1, 2, QtCore.Qt.AlignRight)

            filters_layout.setColumnStretch(1, 1)
            filters_layout.setColumnStretch(3, 1)

            settings_intro = QtWidgets.QLabel(
                "Allgemeine Einstellungen. Weitere Optionen können später ergänzt werden."
            )
            settings_intro.setWordWrap(True)
            settings_layout.addWidget(settings_intro)

            settings_form = QtWidgets.QGridLayout()
            settings_form.setHorizontalSpacing(10)
            settings_form.setVerticalSpacing(6)
            settings_layout.addLayout(settings_form)

            settings_form.addWidget(QtWidgets.QLabel("Theme:"), 0, 0)
            settings_form.addWidget(self.theme_combo, 0, 1)

            dat_hint = QtWidgets.QLabel(
                "DAT-Index wird als SQLite unter data/index/romsorter_dat_index.sqlite gespeichert. "
                "Lege DAT-Dateien in einem eigenen Ordner ab und baue den Index bei Änderungen neu."
            )
            dat_hint.setWordWrap(True)
            settings_layout.addWidget(dat_hint)

            settings_form.addWidget(self.dat_status, 1, 0)
            settings_form.addWidget(self.btn_add_dat, 1, 1)
            settings_form.addWidget(self.btn_refresh_dat, 1, 2)
            settings_form.addWidget(self.btn_cancel_dat, 1, 3)

            settings_form.addWidget(self.dat_auto_load_checkbox, 2, 1)
            settings_form.addWidget(self.btn_clear_dat_cache, 2, 2)

            sort_group = QtWidgets.QGroupBox("Sortieroptionen")
            sort_layout = QtWidgets.QVBoxLayout(sort_group)
            sort_layout.addWidget(self.chk_console_folders)
            sort_layout.addWidget(self.chk_region_subfolders)
            sort_layout.addWidget(self.chk_preserve_structure)
            settings_layout.addWidget(sort_group)

            settings_form.addWidget(self.db_status, 3, 0)
            settings_form.addWidget(self.btn_db_manager, 3, 1)

            settings_form.setColumnStretch(1, 1)

            external_form = QtWidgets.QGridLayout()
            external_form.setHorizontalSpacing(10)
            external_form.setVerticalSpacing(6)
            if show_external_tools:
                tools_layout.addLayout(external_form)

                tools_intro = QtWidgets.QLabel(
                    "External tool conversions run during Execute Sort when conversion rules are enabled. "
                    "Configure tool paths & templates in config as needed."
                )
                tools_intro.setWordWrap(True)
                tools_layout.insertWidget(0, tools_intro)

                external_form.addWidget(QtWidgets.QLabel("External tools output:"), 0, 0)
                external_form.addWidget(self.output_edit, 0, 1)
                external_form.addWidget(self.btn_output, 0, 2)

                external_form.addWidget(QtWidgets.QLabel("External tools temp:"), 1, 0)
                external_form.addWidget(self.temp_edit, 1, 1)
                external_form.addWidget(self.btn_temp, 1, 2)

                external_form.setColumnStretch(1, 1)

                tools_layout.addWidget(self.tools_group)

                tools_hint = QtWidgets.QLabel(
                    "Probe results are generated by running each tool with a non-existent input. "
                    "This confirms the executable responds without guessing flags."
                )
                tools_hint.setWordWrap(True)
                tools_layout.addWidget(tools_hint)

            button_row = QtWidgets.QGridLayout()
            button_row.setHorizontalSpacing(6)
            button_row.setVerticalSpacing(6)
            sort_title = QtWidgets.QLabel("Sortierung")
            sort_title.setStyleSheet("font-weight: 600;")
            main_layout.addWidget(sort_title)
            main_layout.addLayout(button_row)

            self.btn_scan = QtWidgets.QPushButton("Scannen")
            self.btn_preview = QtWidgets.QPushButton("Vorschau Sortierung (Dry-run)")
            self.btn_execute = QtWidgets.QPushButton("Sortieren ausführen (ohne Konvertierung)")
            self.btn_execute_convert = QtWidgets.QPushButton("Konvertierungen ausführen")
            self.btn_audit = QtWidgets.QPushButton("Konvertierungen prüfen")
            self.btn_export_audit_csv = QtWidgets.QPushButton("Audit CSV exportieren")
            self.btn_export_audit_json = QtWidgets.QPushButton("Audit JSON exportieren")
            self.btn_export_scan_csv = QtWidgets.QPushButton("Scan CSV exportieren")
            self.btn_export_scan_json = QtWidgets.QPushButton("Scan JSON exportieren")
            self.btn_export_plan_csv = QtWidgets.QPushButton("Plan CSV exportieren")
            self.btn_export_plan_json = QtWidgets.QPushButton("Plan JSON exportieren")
            self.btn_resume = QtWidgets.QPushButton("Fortsetzen")
            self.btn_retry_failed = QtWidgets.QPushButton("Fehlgeschlagene erneut")
            self.btn_cancel = QtWidgets.QPushButton("Abbrechen")

            for btn in (
                self.btn_scan,
                self.btn_preview,
                self.btn_execute,
                self.btn_execute_convert,
                self.btn_audit,
                self.btn_export_audit_csv,
                self.btn_export_audit_json,
                self.btn_export_scan_csv,
                self.btn_export_scan_json,
                self.btn_export_plan_csv,
                self.btn_export_plan_json,
                self.btn_resume,
                self.btn_retry_failed,
                self.btn_cancel,
            ):
                btn.setMinimumHeight(28)

            self.btn_cancel.setEnabled(False)
            self.btn_resume.setEnabled(False)
            self.btn_retry_failed.setEnabled(False)

            button_row.addWidget(self.btn_scan, 0, 0)
            button_row.addWidget(self.btn_preview, 0, 1)
            button_row.addWidget(self.btn_execute, 0, 2)
            button_row.addWidget(self.btn_resume, 1, 0)
            button_row.addWidget(self.btn_retry_failed, 1, 1)
            button_row.addWidget(self.btn_cancel, 1, 2)
            button_row.setColumnStretch(3, 1)

            conversions_intro = QtWidgets.QLabel(
                "Konvertierungen nutzen konfigurierte Tools und Regeln. Nutze die Prüfung für eine Vorschau."
            )
            conversions_intro.setWordWrap(True)
            conversions_layout.addWidget(conversions_intro)

            conversions_paths = QtWidgets.QGroupBox("Pfade")
            conversions_paths_layout = QtWidgets.QGridLayout(conversions_paths)
            conversions_paths_layout.setHorizontalSpacing(6)
            conversions_paths_layout.setVerticalSpacing(6)

            self.conversion_source_edit = QtWidgets.QLineEdit()
            self.conversion_source_edit.setPlaceholderText("ROM-Quelle auswählen")
            self.conversion_source_btn = QtWidgets.QPushButton("Quelle wählen…")
            self.conversion_dest_edit = QtWidgets.QLineEdit()
            self.conversion_dest_edit.setPlaceholderText("Zielordner auswählen")
            self.conversion_dest_btn = QtWidgets.QPushButton("Ziel wählen…")
            self.conversion_open_dest_btn = QtWidgets.QPushButton("Ziel öffnen")

            self.conversion_source_btn.clicked.connect(self._choose_source)
            self.conversion_dest_btn.clicked.connect(self._choose_dest)
            self.conversion_open_dest_btn.clicked.connect(self._open_destination)
            self.conversion_source_edit.textChanged.connect(self._on_source_text_changed)
            self.conversion_dest_edit.textChanged.connect(self._on_dest_text_changed)

            conversions_paths_layout.addWidget(QtWidgets.QLabel("Quelle:"), 0, 0)
            conversions_paths_layout.addWidget(self.conversion_source_edit, 0, 1)
            conversions_paths_layout.addWidget(self.conversion_source_btn, 0, 2)
            conversions_paths_layout.addWidget(QtWidgets.QLabel("Ziel:"), 1, 0)
            conversions_paths_layout.addWidget(self.conversion_dest_edit, 1, 1)
            conversions_paths_layout.addWidget(self.conversion_dest_btn, 1, 2)
            conversions_paths_layout.addWidget(self.conversion_open_dest_btn, 1, 3)
            conversions_paths_layout.setColumnStretch(1, 1)

            self.conversion_source_edit.setText(self.source_edit.text())
            self.conversion_dest_edit.setText(self.dest_edit.text())
            self.igir_source_edit.setText(self.source_edit.text())
            self.igir_dest_edit.setText(self.dest_edit.text())

            conversions_layout.addWidget(conversions_paths)

            conversions_row = QtWidgets.QGridLayout()
            conversions_row.setHorizontalSpacing(6)
            conversions_row.setVerticalSpacing(6)
            conversions_layout.addLayout(conversions_row)
            conversions_row.addWidget(self.btn_execute_convert, 0, 0)
            conversions_row.addWidget(self.btn_audit, 0, 1)
            conversions_row.addWidget(self.btn_export_audit_csv, 1, 0)
            conversions_row.addWidget(self.btn_export_audit_json, 1, 1)
            conversions_row.addWidget(self.btn_export_scan_csv, 2, 0)
            conversions_row.addWidget(self.btn_export_scan_json, 2, 1)
            conversions_row.addWidget(self.btn_export_plan_csv, 3, 0)
            conversions_row.addWidget(self.btn_export_plan_json, 3, 1)
            conversions_row.setColumnStretch(2, 1)
            conversions_layout.addStretch(1)

            igir_intro = QtWidgets.QLabel(
                "IGIR ist ein externes Tool. Es wird nur bei 'IGIR ausführen' gestartet (niemals im Dry-Run)."
            )
            igir_intro.setWordWrap(True)
            igir_layout.addWidget(igir_intro)

            igir_cfg_group = QtWidgets.QGroupBox("IGIR Konfiguration")
            igir_cfg_layout = QtWidgets.QGridLayout(igir_cfg_group)
            igir_cfg_layout.setHorizontalSpacing(6)
            igir_cfg_layout.setVerticalSpacing(6)
            igir_cfg_layout.addWidget(QtWidgets.QLabel("IGIR Executable:"), 0, 0)
            igir_cfg_layout.addWidget(self.igir_exe_edit, 0, 1)
            igir_cfg_layout.addWidget(self.btn_igir_browse, 0, 2)
            igir_cfg_layout.addWidget(QtWidgets.QLabel("Args Template:"), 1, 0)
            igir_cfg_layout.addWidget(self.igir_args_edit, 1, 1, 3, 2)
            igir_cfg_layout.setColumnStretch(1, 1)
            igir_actions_row = QtWidgets.QHBoxLayout()
            igir_actions_row.addWidget(self.btn_igir_save)
            igir_actions_row.addWidget(self.btn_igir_probe)
            igir_actions_row.addStretch(1)
            igir_cfg_layout.addLayout(igir_actions_row, 4, 1, 1, 2)
            igir_layout.addWidget(igir_cfg_group)

            igir_run_group = QtWidgets.QGroupBox("IGIR Lauf")
            igir_run_layout = QtWidgets.QGridLayout(igir_run_group)
            igir_run_layout.setHorizontalSpacing(6)
            igir_run_layout.setVerticalSpacing(6)
            igir_run_layout.addWidget(QtWidgets.QLabel("Quelle:"), 0, 0)
            igir_run_layout.addWidget(self.igir_source_edit, 0, 1)
            igir_run_layout.addWidget(QtWidgets.QLabel("Ziel:"), 1, 0)
            igir_run_layout.addWidget(self.igir_dest_edit, 1, 1)
            igir_run_layout.addWidget(self.btn_igir_plan, 2, 0)
            igir_run_layout.addWidget(self.btn_igir_execute, 2, 1)
            igir_run_layout.addWidget(self.btn_igir_cancel, 2, 2)
            igir_run_layout.addWidget(self.igir_status_label, 3, 0, 1, 3)
            igir_run_layout.setColumnStretch(1, 1)
            igir_layout.addWidget(igir_run_group)

            self.progress = QtWidgets.QProgressBar()
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            main_layout.addWidget(self.progress)

            self.status_label = QtWidgets.QLabel("Bereit")
            main_layout.addWidget(self.status_label)

            self.summary_label = QtWidgets.QLabel("-")
            main_layout.addWidget(self.summary_label)

            results_intro = QtWidgets.QLabel(
                "Die Ergebnistabelle zeigt geplante Ziele und Status. Nutze die Vorschau vor dem Ausführen."
            )
            results_intro.setWordWrap(True)
            main_layout.addWidget(results_intro)

            self.table = QtWidgets.QTableWidget(0, 9)
            self.table.setHorizontalHeaderLabels(
                [
                    "Eingabepfad",
                    "Name",
                    "Erkannte Konsole/Typ",
                    "Sicherheit",
                    "Signale",
                    "Kandidaten",
                    "Geplantes Ziel",
                    "Aktion",
                    "Status/Fehler",
                ]
            )
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            header = self.table.horizontalHeader()
            header.setStretchLastSection(True)
            header.setSectionsMovable(True)
            try:
                header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
            except Exception:
                header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
            header.setMinimumSectionSize(110)
            try:
                header.setMaximumSectionSize(600)
            except Exception:
                pass
            self.table.setAlternatingRowColors(True)
            try:
                self.table.setSortingEnabled(True)
            except Exception:
                pass
            self.table.resizeColumnsToContents()
            main_layout.addWidget(self.table, 2)

            self.log_view = QtWidgets.QPlainTextEdit()
            self.log_view.setReadOnly(True)
            try:
                self.log_view.document().setMaximumBlockCount(2000)
            except Exception:
                pass
            log_title = QtWidgets.QLabel("Log")
            log_title.setStyleSheet("font-weight: 600;")
            self.log_toggle_btn = QtWidgets.QPushButton("Log ausblenden")
            self.log_toggle_btn.setMinimumWidth(140)
            self.log_toggle_btn.clicked.connect(self._toggle_log_visibility)
            log_hint = QtWidgets.QLabel("Logs zeigen Fortschritt, Tool-Ausgaben und Fehler zur Fehlersuche.")
            log_hint.setWordWrap(True)

            log_header = QtWidgets.QHBoxLayout()
            log_header.addWidget(log_title)
            log_header.addStretch(1)
            log_header.addWidget(self.log_toggle_btn)
            root_layout.addLayout(log_header)
            root_layout.addWidget(self.log_view, 1)
            root_layout.addWidget(log_hint)
            self.log_hint_label = log_hint


            self._log_buffer = []
            self._log_flush_timer = QtCore.QTimer(self)
            self._log_flush_timer.setInterval(100)
            self._log_flush_timer.timeout.connect(self._flush_log)
            self._log_flush_timer.start()

            self.log_signal.connect(self._append_log)
            self.tools_signal.connect(self._on_tools_status)
            self._install_log_handler()

            self.btn_source.clicked.connect(self._choose_source)
            self.btn_dest.clicked.connect(self._choose_dest)
            self.btn_open_dest.clicked.connect(self._open_destination)
            if self.btn_output is not None:
                self.btn_output.clicked.connect(self._choose_output)
            if self.btn_temp is not None:
                self.btn_temp.clicked.connect(self._choose_temp)
            self.btn_igir_browse.clicked.connect(self._choose_igir_exe)
            self.btn_igir_save.clicked.connect(self._save_igir_settings_to_config)
            self.btn_igir_probe.clicked.connect(self._probe_igir)
            self.btn_igir_plan.clicked.connect(self._start_igir_plan)
            self.btn_igir_execute.clicked.connect(self._start_igir_execute)
            self.btn_igir_cancel.clicked.connect(self._cancel_igir)
            self.btn_scan.clicked.connect(self._start_scan)
            self.btn_preview.clicked.connect(self._start_preview)
            self.btn_execute.clicked.connect(self._start_execute)
            self.btn_execute_convert.clicked.connect(self._start_convert_only)
            self.btn_audit.clicked.connect(self._start_audit)
            self.btn_export_audit_csv.clicked.connect(self._export_audit_csv)
            self.btn_export_audit_json.clicked.connect(self._export_audit_json)
            self.btn_export_scan_csv.clicked.connect(self._export_scan_csv)
            self.btn_export_scan_json.clicked.connect(self._export_scan_json)
            self.btn_export_plan_csv.clicked.connect(self._export_plan_csv)
            self.btn_export_plan_json.clicked.connect(self._export_plan_json)
            self.menu_export_scan_csv.triggered.connect(self._export_scan_csv)
            self.menu_export_scan_json.triggered.connect(self._export_scan_json)
            self.menu_export_plan_csv.triggered.connect(self._export_plan_csv)
            self.menu_export_plan_json.triggered.connect(self._export_plan_json)
            self.menu_export_audit_csv.triggered.connect(self._export_audit_csv)
            self.menu_export_audit_json.triggered.connect(self._export_audit_json)
            self.btn_resume.clicked.connect(self._start_resume)
            self.btn_retry_failed.clicked.connect(self._start_retry_failed)
            self.btn_cancel.clicked.connect(self._cancel)
            self.lang_filter.currentTextChanged.connect(self._on_filters_changed)
            self.ver_filter.currentTextChanged.connect(self._on_filters_changed)
            self.region_filter.currentTextChanged.connect(self._on_filters_changed)
            self.dedupe_checkbox.stateChanged.connect(lambda _v: self._on_filters_changed())
            self.hide_unknown_checkbox.stateChanged.connect(lambda _v: self._on_filters_changed())
            self.ext_filter_edit.textChanged.connect(self._on_filters_changed)
            self.min_size_edit.textChanged.connect(self._on_filters_changed)
            self.max_size_edit.textChanged.connect(self._on_filters_changed)
            self.btn_clear_filters.clicked.connect(self._clear_filters)
            self.btn_add_dat.clicked.connect(self._add_dat_folder)
            self.btn_refresh_dat.clicked.connect(self._refresh_dat_sources)
            self.btn_cancel_dat.clicked.connect(self._cancel_dat_index)
            self.dat_auto_load_checkbox.stateChanged.connect(self._on_dat_auto_load_changed)
            self.btn_clear_dat_cache.clicked.connect(self._clear_dat_cache)
            self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
            self.btn_db_manager.clicked.connect(self._open_db_manager)
            self.chk_console_folders.stateChanged.connect(self._on_sort_settings_changed)
            self.chk_region_subfolders.stateChanged.connect(self._on_sort_settings_changed)
            self.chk_preserve_structure.stateChanged.connect(self._on_sort_settings_changed)

            self._apply_theme(self._theme_manager.get_theme())
            self._load_theme_from_config()
            self._load_dat_settings_from_config()
            self._load_sort_settings_from_config()
            self._load_igir_settings_from_config()
            self._refresh_filter_options()
            self._refresh_db_status()
            self._load_window_size()
            self._load_log_visibility()
            if show_external_tools:
                self._probe_tools_async()

        def _load_dat_config(self) -> dict:
            cfg = load_config()
            if not isinstance(cfg, dict):
                cfg = {}
            dat_cfg = cfg.get("dats", {}) or {}
            return {"cfg": cfg, "dat": dat_cfg}

        def _load_dat_settings_from_config(self) -> None:
            try:
                data = self._load_dat_config()
                dat_cfg = data["dat"]
                auto_load = bool(dat_cfg.get("auto_build", False))
                self.dat_auto_load_checkbox.setChecked(auto_load)
                paths = dat_cfg.get("import_paths") or []
                if isinstance(paths, str):
                    paths = [paths]
                paths = [p for p in paths if p]
                if not paths:
                    self.dat_status.setText("DAT: nicht konfiguriert")
                else:
                    self.dat_status.setText(f"DAT: konfiguriert ({len(paths)} Pfade)")
                if auto_load and paths:
                    self._start_dat_auto_load()
            except Exception:
                return

        def _load_igir_settings_from_config(self) -> None:
            try:
                path = Path(__file__).resolve().parents[2] / "tools" / "igir.yaml"
                if not path.exists():
                    return
                raw = path.read_text(encoding="utf-8")
                try:
                    import yaml  # type: ignore
                    data = yaml.safe_load(raw)
                except Exception:
                    data = json.loads(raw)
                if not isinstance(data, dict):
                    return
                exe_path = str(data.get("exe_path") or "")
                args_templates = data.get("args_templates") or {}
                args_template = args_templates.get("execute") or []
                if isinstance(args_template, str):
                    args_template = [args_template]
                args_text = "\n".join(str(arg) for arg in args_template if str(arg).strip())
                self.igir_exe_edit.setText(exe_path)
                self.igir_args_edit.setPlainText(args_text)
            except Exception:
                return

        def _save_igir_settings_to_config(self) -> None:
            try:
                path = Path(__file__).resolve().parents[2] / "tools" / "igir.yaml"
                if path.exists():
                    raw = path.read_text(encoding="utf-8")
                    try:
                        import yaml  # type: ignore
                        data = yaml.safe_load(raw)
                    except Exception:
                        data = json.loads(raw)
                else:
                    data = {}
                if not isinstance(data, dict):
                    data = {}
                args_lines = [
                    line.strip()
                    for line in self.igir_args_edit.toPlainText().splitlines()
                    if line.strip()
                ]
                data["exe_path"] = self.igir_exe_edit.text().strip()
                data.setdefault("args_templates", {})
                if isinstance(data["args_templates"], dict):
                    data["args_templates"]["execute"] = args_lines
                payload = None
                try:
                    import yaml  # type: ignore
                    payload = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
                except Exception:
                    payload = json.dumps(data, indent=2)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(payload, encoding="utf-8")
                self.igir_status_label.setText("Status: gespeichert")
            except Exception as exc:
                self.igir_status_label.setText(f"Status: speichern fehlgeschlagen ({exc})")

        def _choose_igir_exe(self) -> None:
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "IGIR auswählen",
                "",
                "Executable (*.exe *.bat *.cmd);;All Files (*)",
            )
            if filename:
                self.igir_exe_edit.setText(filename)

        def _probe_igir(self) -> None:
            try:
                cfg = load_config()
                result = probe_igir(cfg)
                msg = result.probe_message or result.probe_status
                self.igir_status_label.setText(f"Status: {msg}")
            except Exception as exc:
                self.igir_status_label.setText(f"Status: probe fehlgeschlagen ({exc})")

        def _start_igir_plan(self) -> None:
            if self._igir_thread is not None and self._igir_thread.isRunning():
                QtWidgets.QMessageBox.information(self, "IGIR läuft", "IGIR läuft bereits.")
                return
            source = self.igir_source_edit.text().strip()
            dest = self.igir_dest_edit.text().strip()
            if not source:
                QtWidgets.QMessageBox.information(self, "IGIR", "Bitte Quelle wählen.")
                return
            if not dest:
                QtWidgets.QMessageBox.information(self, "IGIR", "Bitte Ziel wählen.")
                return

            self._save_igir_settings_to_config()
            self._igir_cancel_token = CancelToken()
            temp_dir = str((Path(__file__).resolve().parents[3] / "temp").resolve())
            report_dir = str((Path(__file__).resolve().parents[3] / "data" / "reports" / "igir").resolve())

            thread = QtCore.QThread()
            worker = IgirPlanWorker(source, dest, report_dir, temp_dir, self._igir_cancel_token)
            worker.moveToThread(thread)

            worker.log.connect(self._append_log)
            worker.finished.connect(self._on_igir_plan_finished)
            worker.failed.connect(self._on_igir_failed)
            worker.finished.connect(thread.quit)
            worker.failed.connect(thread.quit)
            thread.finished.connect(lambda: self._cleanup_igir_thread())

            self._igir_thread = thread
            self._igir_worker = worker
            self.btn_igir_plan.setEnabled(False)
            self.btn_igir_execute.setEnabled(False)
            self.btn_igir_cancel.setEnabled(True)
            self.igir_status_label.setText("Status: Plan läuft...")
            thread.started.connect(worker.run)
            thread.start()

        def _start_igir_execute(self) -> None:
            if not self._igir_plan_ready:
                QtWidgets.QMessageBox.information(self, "IGIR", "Bitte zuerst IGIR Plan ausführen.")
                return
            if self._igir_thread is not None and self._igir_thread.isRunning():
                QtWidgets.QMessageBox.information(self, "IGIR läuft", "IGIR läuft bereits.")
                return
            source = self.igir_source_edit.text().strip()
            dest = self.igir_dest_edit.text().strip()
            if not source:
                QtWidgets.QMessageBox.information(self, "IGIR", "Bitte Quelle wählen.")
                return
            if not dest:
                QtWidgets.QMessageBox.information(self, "IGIR", "Bitte Ziel wählen.")
                return

            diff_parts = []
            if self._igir_diff_csv:
                diff_parts.append(f"CSV: {self._igir_diff_csv}")
            if self._igir_diff_json:
                diff_parts.append(f"JSON: {self._igir_diff_json}")
            diff_hint = "\n".join(diff_parts)
            confirm_text = "IGIR Execute startet echte Änderungen. Fortfahren?"
            if diff_hint:
                confirm_text = f"{confirm_text}\n\nDiff-Berichte:\n{diff_hint}"
            reply = QtWidgets.QMessageBox.question(
                self,
                "IGIR Execute bestätigen",
                confirm_text,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

            self._save_igir_settings_to_config()
            self._igir_cancel_token = CancelToken()
            temp_dir = str((Path(__file__).resolve().parents[3] / "temp").resolve())

            thread = QtCore.QThread()
            worker = IgirExecuteWorker(
                source,
                dest,
                temp_dir,
                self._igir_cancel_token,
                self._igir_plan_ready,
                True,
            )
            worker.moveToThread(thread)

            worker.log.connect(self._append_log)
            worker.finished.connect(self._on_igir_execute_finished)
            worker.failed.connect(self._on_igir_failed)
            worker.finished.connect(thread.quit)
            worker.failed.connect(thread.quit)
            thread.finished.connect(lambda: self._cleanup_igir_thread())

            self._igir_thread = thread
            self._igir_worker = worker
            self.btn_igir_plan.setEnabled(False)
            self.btn_igir_execute.setEnabled(False)
            self.btn_igir_cancel.setEnabled(True)
            self.igir_status_label.setText("Status: Execute läuft...")
            thread.started.connect(worker.run)
            thread.start()

        def _cancel_igir(self) -> None:
            if self._igir_cancel_token is None:
                return
            try:
                self._igir_cancel_token.cancel()
            except Exception:
                pass

        def _cleanup_igir_thread(self) -> None:
            try:
                if self._igir_worker is not None:
                    self._igir_worker.deleteLater()
            except Exception:
                pass
            try:
                if self._igir_thread is not None:
                    self._igir_thread.deleteLater()
            except Exception:
                pass
            self._igir_thread = None
            self._igir_worker = None
            self._igir_cancel_token = None

        def _on_igir_plan_finished(self, result: object) -> None:
            self.btn_igir_plan.setEnabled(True)
            self.btn_igir_cancel.setEnabled(False)
            message = getattr(result, "message", "ok")
            if getattr(result, "ok", False):
                self._igir_plan_ready = True
                self._igir_diff_csv = getattr(result, "diff_csv", None)
                self._igir_diff_json = getattr(result, "diff_json", None)
                self.btn_igir_execute.setEnabled(True)
                self.igir_status_label.setText("Status: Plan ok")
                QtWidgets.QMessageBox.information(self, "IGIR", f"Plan erstellt ({message}).")
            elif getattr(result, "cancelled", False):
                self.igir_status_label.setText("Status: Plan abgebrochen")
                QtWidgets.QMessageBox.information(self, "IGIR", "Plan abgebrochen.")
            else:
                self.igir_status_label.setText(f"Status: Plan fehlgeschlagen ({message})")
                QtWidgets.QMessageBox.warning(self, "IGIR", f"Plan fehlgeschlagen: {message}")

        def _on_igir_execute_finished(self, result: object) -> None:
            self.btn_igir_plan.setEnabled(True)
            self.btn_igir_execute.setEnabled(True)
            self.btn_igir_cancel.setEnabled(False)
            message = getattr(result, "message", "ok")
            if getattr(result, "success", False):
                self.igir_status_label.setText("Status: Execute ok")
                QtWidgets.QMessageBox.information(self, "IGIR", f"Execute abgeschlossen ({message}).")
            elif getattr(result, "cancelled", False):
                self.igir_status_label.setText("Status: Execute abgebrochen")
                QtWidgets.QMessageBox.information(self, "IGIR", "Execute abgebrochen.")
            else:
                self.igir_status_label.setText(f"Status: Execute fehlgeschlagen ({message})")
                QtWidgets.QMessageBox.warning(self, "IGIR", f"Execute fehlgeschlagen: {message}")

        def _on_igir_failed(self, message: str) -> None:
            self.btn_igir_plan.setEnabled(True)
            self.btn_igir_execute.setEnabled(self._igir_plan_ready)
            self.btn_igir_cancel.setEnabled(False)
            self.igir_status_label.setText(f"Status: fehlgeschlagen ({message})")
            QtWidgets.QMessageBox.warning(self, "IGIR", f"IGIR fehlgeschlagen: {message}")

        def _start_dat_auto_load(self) -> None:
            try:
                cfg = load_config()
                dat_cfg = cfg.get("dats", {}) if isinstance(cfg, dict) else {}
                index_path = dat_cfg.get("index_path") or os.path.join("data", "index", "romsorter_dat_index.sqlite")
                if Path(index_path).exists():
                    self.dat_status.setText("DAT: index vorhanden")
                else:
                    self.dat_status.setText("DAT: index fehlt")
            except Exception as exc:
                self.dat_status.setText(f"DAT: Fehler ({exc})")

        def _poll_dat_status(self) -> None:
            self._dat_status_timer.stop()

        def _load_sort_settings_from_config(self) -> None:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    return
                sorting_cfg = cfg.get("features", {}).get("sorting", {}) or {}
                console_enabled = bool(sorting_cfg.get("console_sorting_enabled", True))
                create_console = bool(sorting_cfg.get("create_console_folders", True))
                self.chk_console_folders.setChecked(console_enabled and create_console)
                self.chk_region_subfolders.setChecked(bool(sorting_cfg.get("region_based_sorting", False)))
                self.chk_preserve_structure.setChecked(bool(sorting_cfg.get("preserve_folder_structure", False)))
            except Exception:
                return

        def _on_sort_settings_changed(self, _value: int = 0) -> None:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    cfg = {}
                features_cfg = cfg.get("features", {}) or {}
                sorting_cfg = features_cfg.get("sorting", {}) or {}
                console_checked = bool(self.chk_console_folders.isChecked())
                sorting_cfg["console_sorting_enabled"] = console_checked
                sorting_cfg["create_console_folders"] = console_checked
                sorting_cfg["region_based_sorting"] = bool(self.chk_region_subfolders.isChecked())
                sorting_cfg["preserve_folder_structure"] = bool(self.chk_preserve_structure.isChecked())
                features_cfg["sorting"] = sorting_cfg
                cfg["features"] = features_cfg
                save_config(cfg)
            except Exception:
                return

        def _on_dat_auto_load_changed(self, _value: int) -> None:
            try:
                data = self._load_dat_config()
                cfg = data["cfg"]
                dat_cfg = data["dat"]
                dat_cfg["auto_build"] = bool(self.dat_auto_load_checkbox.isChecked())
                cfg["dats"] = dat_cfg
                save_config(cfg)
            except Exception:
                return

        def _clear_dat_cache(self) -> None:
            try:
                confirm = QtWidgets.QMessageBox.question(
                    self,
                    "DAT-Cache löschen",
                    "Zwischengespeicherten DAT-Index löschen? Er wird beim nächsten Aktualisieren neu aufgebaut.",
                )
                if confirm != QtWidgets.QMessageBox.StandardButton.Yes:
                    return
                index_file = Path(os.getcwd()) / "data" / "index" / "romsorter_dat_index.sqlite"
                if index_file.exists():
                    index_file.unlink()
                    self.dat_status.setText("DAT: Index gelöscht")
                    self._append_log("DAT-Cache gelöscht")
                else:
                    self.dat_status.setText("DAT: Index nicht gefunden")
            except Exception as exc:
                self.dat_status.setText(f"DAT: Cache löschen fehlgeschlagen ({exc})")

        def _has_external_tools_templates(self) -> bool:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    return False
                tools_cfg = cfg.get("external_tools", {}) or {}
                for key in ("wud2app", "wudcompress"):
                    tool = tools_cfg.get(key, {}) or {}
                    args = tool.get("args_template") or []
                    if isinstance(args, str):
                        args = [args]
                    if any("{input}" in str(arg) for arg in args):
                        return True
            except Exception:
                return False
            return False

        def _add_dat_folder(self) -> None:
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "DAT-Ordner auswählen")
            if not directory:
                return
            data = self._load_dat_config()
            cfg = data["cfg"]
            dat_cfg = data["dat"]
            paths = dat_cfg.get("import_paths") or []
            if isinstance(paths, str):
                paths = [paths]
            if directory not in paths:
                paths.append(directory)
            dat_cfg["import_paths"] = paths
            cfg["dats"] = dat_cfg
            save_config(cfg)
            self.dat_status.setText("DAT: Pfade aktualisiert")
            if bool(dat_cfg.get("auto_build", False)):
                self._start_dat_auto_load()

        def _refresh_dat_sources(self) -> None:
            try:
                if self._dat_index_thread is not None:
                    return
                self.dat_status.setText("DAT: Index wird gebaut...")
                self._dat_index_cancel_token = CancelToken()

                def task():
                    return build_dat_index(cancel_token=self._dat_index_cancel_token)

                worker = DatIndexWorker(task)
                thread = QtCore.QThread()
                worker.moveToThread(thread)
                worker.finished.connect(self._on_dat_index_done)
                worker.failed.connect(self._on_dat_index_failed)
                worker.finished.connect(thread.quit)
                worker.failed.connect(thread.quit)
                thread.finished.connect(self._cleanup_dat_index_thread)

                self._dat_index_worker = worker
                self._dat_index_thread = thread
                self.btn_refresh_dat.setEnabled(False)
                self.btn_cancel_dat.setEnabled(True)
                thread.started.connect(worker.run)
                thread.start()
            except Exception as exc:
                self.dat_status.setText(f"DAT: Fehler ({exc})")

        def _cancel_dat_index(self) -> None:
            if self._dat_index_cancel_token is None:
                return
            try:
                self._dat_index_cancel_token.cancel()
            except Exception:
                pass

        def _cleanup_dat_index_thread(self) -> None:
            if self._dat_index_worker is not None:
                self._dat_index_worker.deleteLater()
            if self._dat_index_thread is not None:
                self._dat_index_thread.deleteLater()
            self._dat_index_thread = None
            self._dat_index_worker = None
            self._dat_index_cancel_token = None

        def _on_dat_index_done(self, result: object) -> None:
            self.btn_refresh_dat.setEnabled(True)
            self.btn_cancel_dat.setEnabled(False)
            self.dat_status.setText(f"DAT: Index fertig ({result})")

        def _on_dat_index_failed(self, message: str) -> None:
            self.btn_refresh_dat.setEnabled(True)
            self.btn_cancel_dat.setEnabled(False)
            self.dat_status.setText(f"DAT: Index fehlgeschlagen ({message})")

        def _is_drag_drop_enabled(self) -> bool:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    return True
                gui_cfg = cfg.get("gui_settings", {}) or {}
                return bool(gui_cfg.get("drag_drop_enabled", True))
            except Exception:
                return True

        def _resolve_theme_name(self, value: str) -> Optional[str]:
            val = (value or "").strip()
            if not val:
                return None
            low = val.lower()
            if low == "auto":
                return self._theme_manager.get_current_theme_name()
            if low == "light":
                return "Light"
            if low == "dark":
                return "Dark"
            return val

        def _load_theme_from_config(self) -> None:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    return
                gui_cfg = cfg.get("gui_settings", {}) or {}
                theme_value = gui_cfg.get("theme")
                if not theme_value:
                    return
                theme_name = self._resolve_theme_name(str(theme_value))
                if not theme_name:
                    return
                if str(theme_value).strip().lower() == "auto":
                    idx = self.theme_combo.findText("Auto")
                    if idx >= 0:
                        self.theme_combo.setCurrentIndex(idx)
                if theme_name in self._theme_manager.get_theme_names():
                    self._theme_manager.set_current_theme(theme_name)
                    idx = self.theme_combo.findText(theme_name)
                    if idx >= 0:
                        self.theme_combo.setCurrentIndex(idx)
                    self._apply_theme(self._theme_manager.get_theme(theme_name))
            except Exception:
                return

        def _refresh_db_status(self) -> None:
            db_path = get_rom_db_path()
            if Path(db_path).exists():
                self.db_status.setText(f"DB: {db_path}")
            else:
                self.db_status.setText(f"DB: missing ({db_path})")

        def _open_db_manager(self) -> None:
            dialog = DBManagerDialog(self)
            dialog.exec()

        def _apply_theme(self, theme) -> None:
            try:
                sheet = theme.generate_qt_stylesheet()
                app = QtWidgets.QApplication.instance()
                if app:
                    app.setStyleSheet(sheet)
                else:
                    self.setStyleSheet(sheet)
            except Exception:
                return

        def _on_theme_changed(self, name: str) -> None:
            if not name:
                return
            theme_value = name
            if name == "Auto":
                theme_value = "auto"
                resolved = self._resolve_theme_name("auto")
                if resolved and self._theme_manager.set_current_theme(resolved):
                    self._apply_theme(self._theme_manager.get_theme(resolved))
            else:
                if self._theme_manager.set_current_theme(name):
                    self._apply_theme(self._theme_manager.get_theme(name))
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    cfg = {}
                gui_cfg = cfg.get("gui_settings", {}) or {}
                gui_cfg["theme"] = theme_value
                cfg["gui_settings"] = gui_cfg
                self._save_config_async(cfg)
            except Exception:
                pass

        def _save_config_async(self, cfg: dict) -> None:
            def task():
                try:
                    save_config(cfg)
                except Exception:
                    return

            threading.Thread(target=task, daemon=True).start()

        def _load_window_size(self) -> None:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    return
                gui_cfg = cfg.get("gui_settings", {}) or {}
                if not bool(gui_cfg.get("remember_window_size", True)):
                    return
                width = int(gui_cfg.get("window_width", 0) or 0)
                height = int(gui_cfg.get("window_height", 0) or 0)
                if width > 0 and height > 0:
                    self.resize(width, height)
            except Exception:
                return

        def _load_log_visibility(self) -> None:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    return
                gui_cfg = cfg.get("gui_settings", {}) or {}
                visible = bool(gui_cfg.get("log_visible", True))
                self._set_log_visible(visible, persist=False)
            except Exception:
                return

        def _save_window_size(self) -> None:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    cfg = {}
                gui_cfg = cfg.get("gui_settings", {}) or {}
                if not bool(gui_cfg.get("remember_window_size", True)):
                    return
                gui_cfg["window_width"] = int(self.width())
                gui_cfg["window_height"] = int(self.height())
                cfg["gui_settings"] = gui_cfg
                self._save_config_async(cfg)
            except Exception:
                return

        def _save_log_visibility(self) -> None:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    cfg = {}
                gui_cfg = cfg.get("gui_settings", {}) or {}
                gui_cfg["log_visible"] = bool(self._log_visible)
                cfg["gui_settings"] = gui_cfg
                self._save_config_async(cfg)
            except Exception:
                return

        def _probe_tools_async(self) -> None:
            def task():
                try:
                    cfg = load_config()
                    wud2app_result = probe_wud2app(cfg)
                    wudcompress_result = probe_wudcompress(cfg)
                    payload = {
                        "wud2app": {
                            "version": wud2app_result.version or "unknown",
                            "message": wud2app_result.probe_message or wud2app_result.probe_status,
                        },
                        "wudcompress": {
                            "version": wudcompress_result.version or "unknown",
                            "message": wudcompress_result.probe_message or wudcompress_result.probe_status,
                        },
                    }
                except Exception as exc:
                    payload = {
                        "wud2app": {"version": "unknown", "message": f"probe failed: {exc}"},
                        "wudcompress": {"version": "unknown", "message": "probe skipped"},
                    }
                self.tools_signal.emit(payload)

            threading.Thread(target=task, daemon=True).start()

        def _on_tools_status(self, payload: object) -> None:
            if not isinstance(payload, dict):
                return
            wud2app = payload.get("wud2app") or {}
            wudcompress = payload.get("wudcompress") or {}
            self.wud2app_version.setText(str(wud2app.get("version") or "unknown"))
            self.wud2app_probe.setText(str(wud2app.get("message") or ""))
            self.wudcompress_version.setText(str(wudcompress.get("version") or "unknown"))
            self.wudcompress_probe.setText(str(wudcompress.get("message") or ""))

        def closeEvent(self, event):
            self._remove_log_handler()
            try:
                if self._log_flush_timer is not None:
                    self._log_flush_timer.stop()
                    self._flush_log()
            except Exception:
                pass
            self._save_window_size()
            return super().closeEvent(event)

        def _install_log_handler(self) -> None:
            root_logger = logging.getLogger()
            for handler in list(root_logger.handlers):
                if getattr(handler, "_qt_gui_handler", False):
                    root_logger.removeHandler(handler)

            handler = QtLogHandler(self.log_signal.emit)
            handler._qt_gui_handler = True
            handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            root_logger.addHandler(handler)
            self._log_handler = handler

        def _remove_log_handler(self) -> None:
            root_logger = logging.getLogger()
            handler = getattr(self, "_log_handler", None)
            if handler is not None:
                try:
                    root_logger.removeHandler(handler)
                except Exception:
                    pass
            for handler in list(root_logger.handlers):
                if getattr(handler, "_qt_gui_handler", False):
                    try:
                        root_logger.removeHandler(handler)
                    except Exception:
                        pass

        def _on_filters_changed(self, _value: str = "") -> None:
            # Changing filters invalidates existing plan.
            if self._sort_plan is not None:
                self._sort_plan = None
                self._append_log("Filters changed: sort plan invalidated. Please run Preview Sort again.")

            if self._scan_result is not None:
                # Keep table in sync with current filter selection.
                self._populate_scan_table(self._get_filtered_scan_result())
                self._last_view = "scan"

        def _clear_filters(self) -> None:
            def _set_combo(combo, value: str) -> None:
                idx = combo.findText(value)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                else:
                    combo.setCurrentIndex(0)

            _set_combo(self.lang_filter, "All")
            _set_combo(self.ver_filter, "All")
            _set_combo(self.region_filter, "All")
            self.ext_filter_edit.clear()
            self.min_size_edit.clear()
            self.max_size_edit.clear()
            self.dedupe_checkbox.setChecked(True)
            self.hide_unknown_checkbox.setChecked(False)
            self._on_filters_changed()

        def _get_filtered_scan_result(self) -> ScanResult:
            if self._scan_result is None:
                raise RuntimeError("No scan result available")

            lang = str(self.lang_filter.currentText() or "All")
            ver = str(self.ver_filter.currentText() or "All")
            region = str(self.region_filter.currentText() or "All")
            dedupe = bool(self.dedupe_checkbox.isChecked())
            hide_unknown = bool(self.hide_unknown_checkbox.isChecked())
            ext_filter = str(self.ext_filter_edit.text() or "").strip()
            min_size_mb = self._parse_size_mb(self.min_size_edit.text())
            max_size_mb = self._parse_size_mb(self.max_size_edit.text())

            filtered_items = filter_scan_items(
                list(self._scan_result.items),
                language_filter=lang,
                version_filter=ver,
                region_filter=region,
                extension_filter=ext_filter,
                min_size_mb=min_size_mb,
                max_size_mb=max_size_mb,
                dedupe_variants=dedupe,
            )

            if hide_unknown:
                min_conf = self._get_min_confidence()
                filtered_items = [it for it in filtered_items if self._is_confident_for_display(it, min_conf)]

            return ScanResult(
                source_path=self._scan_result.source_path,
                items=filtered_items,
                stats=dict(self._scan_result.stats),
                cancelled=bool(self._scan_result.cancelled),
            )

        def _parse_size_mb(self, value: str) -> Optional[float]:
            try:
                raw = (value or "").strip()
                if not raw:
                    return None
                return float(raw.replace(",", "."))
            except Exception:
                return None

        def _get_min_confidence(self) -> float:
            try:
                cfg = load_config()
            except Exception:
                return 0.95
            try:
                sorting_cfg = cfg.get("features", {}).get("sorting", {}) or {}
                return float(sorting_cfg.get("confidence_threshold", 0.95))
            except Exception:
                return 0.95

        def _is_confident_for_display(self, item: ScanItem, min_confidence: float) -> bool:
            system = (item.detected_system or "Unknown").strip()
            if not system or system == "Unknown":
                return False
            source = str(item.detection_source or "").lower()
            if source.startswith("dat:"):
                return True
            try:
                conf = float(item.detection_confidence or 0.0)
            except Exception:
                conf = 0.0
            return conf >= min_confidence

        def _refresh_filter_options(self) -> None:
            if self._scan_result is None:
                lang_defaults, ver_defaults, region_defaults = self._load_filter_defaults()
                self.lang_filter.clear()
                self.lang_filter.addItems(lang_defaults)
                self.ver_filter.clear()
                self.ver_filter.addItems(ver_defaults)
                self.region_filter.clear()
                self.region_filter.addItems(region_defaults)
                return

            langs = set()
            has_unknown_lang = False
            vers = set()
            has_unknown_ver = False

            regions = set()
            has_unknown_region = False

            for item in self._scan_result.items:
                item_langs = getattr(item, "languages", ()) or ()
                if not item_langs:
                    try:
                        inferred_langs, inferred_ver = infer_languages_and_version_from_name(item.input_path)
                        if inferred_langs:
                            item_langs = inferred_langs
                        if inferred_ver and not getattr(item, "version", None):
                            vers.add(str(inferred_ver))
                    except Exception:
                        pass
                if not item_langs:
                    has_unknown_lang = True
                else:
                    langs.update(item_langs)

                v = getattr(item, "version", None)
                if not v:
                    has_unknown_ver = True
                else:
                    vers.add(str(v))

                r = getattr(item, "region", None)
                if not r:
                    # Fallback parse for older scan items
                    try:
                        r = infer_region_from_name(item.input_path)
                    except Exception:
                        r = None
                if not r or str(r) == "Unknown":
                    has_unknown_region = True
                else:
                    regions.add(str(r))

            current_lang = str(self.lang_filter.currentText() or "All")
            current_ver = str(self.ver_filter.currentText() or "All")
            current_region = str(self.region_filter.currentText() or "All")

            self.lang_filter.blockSignals(True)
            self.lang_filter.clear()
            self.lang_filter.addItem("All")
            if has_unknown_lang:
                self.lang_filter.addItem("Unknown")
            for l in sorted(langs):
                self.lang_filter.addItem(str(l))
            idx = self.lang_filter.findText(current_lang)
            self.lang_filter.setCurrentIndex(idx if idx >= 0 else 0)
            self.lang_filter.blockSignals(False)

            self.ver_filter.blockSignals(True)
            self.ver_filter.clear()
            self.ver_filter.addItem("All")
            if has_unknown_ver:
                self.ver_filter.addItem("Unknown")
            for v in sorted(vers):
                self.ver_filter.addItem(str(v))
            idx2 = self.ver_filter.findText(current_ver)
            self.ver_filter.setCurrentIndex(idx2 if idx2 >= 0 else 0)
            self.ver_filter.blockSignals(False)

            self.region_filter.blockSignals(True)
            self.region_filter.clear()
            self.region_filter.addItem("All")
            if has_unknown_region:
                self.region_filter.addItem("Unknown")
            for r in sorted(regions):
                self.region_filter.addItem(str(r))
            idx3 = self.region_filter.findText(current_region)
            self.region_filter.setCurrentIndex(idx3 if idx3 >= 0 else 0)
            self.region_filter.blockSignals(False)

        def _load_filter_defaults(self) -> tuple[list[str], list[str], list[str]]:
            lang_values = ["All", "Unknown"]
            ver_values = ["All", "Unknown"]
            region_values = ["All", "Unknown"]

            try:
                cfg = load_config()
                prioritization = cfg.get("prioritization", {}) or {}
                langs = prioritization.get("language_order", []) or []
                regions = prioritization.get("region_order", []) or []
                lang_priority = prioritization.get("language_priorities", {}) or {}
                region_priority = prioritization.get("region_priorities", {}) or {}
                for lang in langs:
                    if str(lang) not in lang_values:
                        lang_values.append(str(lang))
                for region in regions:
                    if str(region) not in region_values:
                        region_values.append(str(region))
                for lang in lang_priority.keys():
                    if str(lang) not in lang_values:
                        lang_values.append(str(lang))
                for region in region_priority.keys():
                    if str(region) not in region_values:
                        region_values.append(str(region))
            except Exception:
                pass

            return lang_values, ver_values, region_values

        def _append_summary_row(self, report: SortReport) -> None:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem("(Summary)"))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(""))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(""))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(""))
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(""))
            self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(""))
            self.table.setItem(row, 6, QtWidgets.QTableWidgetItem(report.dest_path))
            self.table.setItem(row, 7, QtWidgets.QTableWidgetItem(report.mode))

            text = (
                f"Processed: {report.processed} | Copied: {report.copied} | Moved: {report.moved} | "
                f"Skipped: {report.skipped} | Errors: {len(report.errors)} | Cancelled: {report.cancelled}"
            )
            item = QtWidgets.QTableWidgetItem(text)
            if report.errors:
                item.setToolTip("\n".join(report.errors))
            self.table.setItem(row, 8, item)

        def _append_log(self, text: str) -> None:
            if not text:
                return
            self._log_buffer.append(str(text))

        def _flush_log(self) -> None:
            if not self._log_buffer:
                return
            payload = "\n".join(self._log_buffer)
            self._log_buffer.clear()
            self.log_view.appendPlainText(payload)

        def _toggle_log_visibility(self) -> None:
            self._set_log_visible(not self._log_visible)

        def _set_log_visible(self, visible: bool, persist: bool = True) -> None:
            self._log_visible = bool(visible)
            self.log_view.setVisible(self._log_visible)
            if hasattr(self, "log_hint_label"):
                self.log_hint_label.setVisible(self._log_visible)
            self.log_toggle_btn.setText("Log ausblenden" if self._log_visible else "Log anzeigen")
            if persist:
                self._save_log_visibility()

        def _rom_display_name(self, input_path: str) -> str:
            return rom_display_name(input_path)

        def _format_confidence(self, value: Optional[float]) -> str:
            return format_confidence(value)

        def _format_signals(self, item: object, default: str = "-") -> str:
            return format_signals(item, default=default)

        def _format_candidates(self, item: object) -> str:
            return format_candidates(item)

        def _choose_source(self) -> None:
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select source folder")
            if directory:
                self._set_source_text(directory)
                self._append_log(f"Source set: {directory}")

        def _choose_dest(self) -> None:
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select destination folder")
            if directory:
                self._set_dest_text(directory)
                self._append_log(f"Destination set: {directory}")

        def _choose_output(self) -> None:
            if self.output_edit is None:
                return
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select output folder")
            if directory:
                self.output_edit.setText(directory)
                self._append_log(f"External output set: {directory}")

        def _choose_temp(self) -> None:
            if self.temp_edit is None:
                return
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select temp folder")
            if directory:
                self.temp_edit.setText(directory)
                self._append_log(f"External temp set: {directory}")

        def _on_drop_source(self, path: str) -> None:
            self._set_source_text(path)
            self._append_log(f"DnD source: {path}")

        def _on_drop_dest(self, path: str) -> None:
            self._set_dest_text(path)
            self._append_log(f"DnD destination: {path}")

        def _set_source_text(self, text: str) -> None:
            if self._syncing_paths:
                return
            self._syncing_paths = True
            try:
                self.source_edit.setText(text)
                if hasattr(self, "conversion_source_edit"):
                    self.conversion_source_edit.setText(text)
                if hasattr(self, "igir_source_edit"):
                    self.igir_source_edit.setText(text)
            finally:
                self._syncing_paths = False

        def _set_dest_text(self, text: str) -> None:
            if self._syncing_paths:
                return
            self._syncing_paths = True
            try:
                self.dest_edit.setText(text)
                if hasattr(self, "conversion_dest_edit"):
                    self.conversion_dest_edit.setText(text)
                if hasattr(self, "igir_dest_edit"):
                    self.igir_dest_edit.setText(text)
            finally:
                self._syncing_paths = False

        def _on_source_text_changed(self, text: str) -> None:
            if self._syncing_paths:
                return
            self._set_source_text(text)

        def _on_dest_text_changed(self, text: str) -> None:
            if self._syncing_paths:
                return
            self._set_dest_text(text)

        def _open_destination(self) -> None:
            directory = self.dest_edit.text().strip()
            if not directory:
                QtWidgets.QMessageBox.information(self, "Kein Ziel", "Bitte zuerst einen Zielordner wählen.")
                return
            try:
                url = QtCore.QUrl.fromLocalFile(directory)
                if not QtGui.QDesktopServices.openUrl(url):
                    QtWidgets.QMessageBox.warning(self, "Öffnen fehlgeschlagen", "Zielordner konnte nicht geöffnet werden.")
            except Exception:
                QtWidgets.QMessageBox.warning(self, "Öffnen fehlgeschlagen", "Zielordner konnte nicht geöffnet werden.")

        def _on_drop_output(self, path: str) -> None:
            if self.output_edit is None:
                return
            self.output_edit.setText(path)
            self._append_log(f"DnD external output: {path}")

        def _on_drop_temp(self, path: str) -> None:
            if self.temp_edit is None:
                return
            self.temp_edit.setText(path)
            self._append_log(f"DnD external temp: {path}")

        def _set_running(self, running: bool) -> None:
            self.btn_scan.setEnabled(not running)
            self.btn_preview.setEnabled(not running)
            self.btn_execute.setEnabled(not running)
            self.btn_execute_convert.setEnabled(not running)
            self.btn_audit.setEnabled(not running)
            self.btn_export_audit_csv.setEnabled(not running and self._audit_report is not None)
            self.btn_export_audit_json.setEnabled(not running and self._audit_report is not None)
            self.btn_export_scan_csv.setEnabled(not running and self._scan_result is not None)
            self.btn_export_scan_json.setEnabled(not running and self._scan_result is not None)
            self.btn_export_plan_csv.setEnabled(not running and self._sort_plan is not None)
            self.btn_export_plan_json.setEnabled(not running and self._sort_plan is not None)
            self.menu_export_audit_csv.setEnabled(not running and self._audit_report is not None)
            self.menu_export_audit_json.setEnabled(not running and self._audit_report is not None)
            self.menu_export_scan_csv.setEnabled(not running and self._scan_result is not None)
            self.menu_export_scan_json.setEnabled(not running and self._scan_result is not None)
            self.menu_export_plan_csv.setEnabled(not running and self._sort_plan is not None)
            self.menu_export_plan_json.setEnabled(not running and self._sort_plan is not None)
            self.btn_cancel.setEnabled(running)
            self.btn_resume.setEnabled(not running and self._can_resume())
            self.btn_retry_failed.setEnabled(not running and self._can_retry_failed())

            self.btn_source.setEnabled(not running)
            self.btn_dest.setEnabled(not running)
            self.btn_open_dest.setEnabled(not running)
            if self.btn_output is not None:
                self.btn_output.setEnabled(not running)
            if self.btn_temp is not None:
                self.btn_temp.setEnabled(not running)
            if self.output_edit is not None:
                self.output_edit.setEnabled(not running)
            if self.temp_edit is not None:
                self.temp_edit.setEnabled(not running)
            self.mode_combo.setEnabled(not running)
            self.conflict_combo.setEnabled(not running)
            self.btn_clear_filters.setEnabled(not running)
            if not running:
                self._update_resume_buttons()

        def _can_resume(self) -> bool:
            try:
                return Path(self._resume_path).exists()
            except Exception:
                return False

        def _can_retry_failed(self) -> bool:
            return bool(self._failed_action_indices) and self._sort_plan is not None

        def _update_resume_buttons(self) -> None:
            if self._worker is not None or self._thread is not None:
                return
            self.btn_resume.setEnabled(self._can_resume())
            self.btn_retry_failed.setEnabled(self._can_retry_failed())

        def _validate_paths(self, *, require_dest: bool = True) -> Optional[dict]:
            source = self.source_edit.text().strip()
            dest = self.dest_edit.text().strip()
            if self.output_edit is None:
                output_dir = ""
            else:
                try:
                    output_dir = self.output_edit.text().strip()
                except RuntimeError:
                    output_dir = ""
            if self.temp_edit is None:
                temp_dir = ""
            else:
                try:
                    temp_dir = self.temp_edit.text().strip()
                except RuntimeError:
                    temp_dir = ""
            if not source:
                try:
                    self._append_log("Validation failed: missing source path")
                except Exception:
                    pass
                QtWidgets.QMessageBox.warning(self, "Quelle fehlt", "Bitte einen Quellordner wählen.")
                return None
            if require_dest and not dest:
                try:
                    self._append_log("Validation failed: missing destination path")
                except Exception:
                    pass
                QtWidgets.QMessageBox.warning(self, "Ziel fehlt", "Bitte einen Zielordner wählen.")
                return None
            return {"source": source, "dest": dest, "output_dir": output_dir, "temp_dir": temp_dir}

        def _start_operation(
            self,
            op: str,
            *,
            start_index: int = 0,
            only_indices: Optional[list[int]] = None,
            resume_path: Optional[str] = None,
            conversion_mode: ConversionMode = "all",
        ) -> None:
            values = self._validate_paths(require_dest=op in ("plan", "execute"))
            if values is None:
                return

            try:
                self._append_log(f"Starting {op}…")
            except Exception:
                pass

            if op in ("plan", "execute") and self._scan_result is None:
                QtWidgets.QMessageBox.information(self, "Keine Scan-Ergebnisse", "Bitte zuerst scannen.")
                return
            if op == "execute" and self._sort_plan is None:
                QtWidgets.QMessageBox.information(self, "Kein Sortierplan", "Bitte zuerst Vorschau ausführen.")
                return

            self._cancel_token = CancelToken()
            self.progress.setValue(0)
            self.status_label.setText("Starte…")

            if op == "scan":
                self._scan_result = None
                self._sort_plan = None
                self.table.setRowCount(0)
                self.log_view.clear()

            signals = WorkerSignals()
            signals.phase_changed.connect(self._on_phase_changed)
            signals.progress.connect(self._on_progress)
            signals.log.connect(self._append_log)
            signals.action_status.connect(self._on_action_status)
            signals.finished.connect(lambda payload: self._on_finished(op, payload))
            signals.failed.connect(self._on_failed)

            self._thread = QtCore.QThread()

            scan_for_plan = None
            if op == "plan":
                scan_for_plan = self._get_filtered_scan_result()

            if op == "execute" and resume_path is None:
                resume_path = self._resume_path

            self._worker = OperationWorker(
                op=op,
                source=values["source"],
                dest=values["dest"],
                output_dir=values["output_dir"],
                temp_dir=values["temp_dir"],
                mode=str(self.mode_combo.currentText()),
                on_conflict=str(self.conflict_combo.currentText()),
                conversion_mode=conversion_mode,
                scan_result=scan_for_plan if scan_for_plan is not None else self._scan_result,
                sort_plan=self._sort_plan,
                start_index=start_index,
                only_indices=only_indices,
                resume_path=resume_path,
                cancel_token=self._cancel_token,
                signals=signals,
            )
            self._worker.moveToThread(self._thread)
            self._thread.started.connect(self._worker.run)

            self._set_running(True)
            self._thread.start()

        def _start_scan(self) -> None:
            self._failed_action_indices.clear()
            self._audit_report = None
            self._update_resume_buttons()
            try:
                self._append_log("Scan requested")
            except Exception:
                pass
            self._start_operation("scan")

        def _start_preview(self) -> None:
            self._failed_action_indices.clear()
            self._audit_report = None
            self._update_resume_buttons()
            self._start_operation("plan")

        def _start_execute(self) -> None:
            self._failed_action_indices.clear()
            self._audit_report = None
            self._update_resume_buttons()
            self._start_operation("execute", conversion_mode="skip")

        def _start_convert_only(self) -> None:
            self._failed_action_indices.clear()
            self._audit_report = None
            self._update_resume_buttons()
            self._start_operation("execute", conversion_mode="only")

        def _start_audit(self) -> None:
            self._failed_action_indices.clear()
            self._audit_report = None
            self._update_resume_buttons()
            self._start_operation("audit")

        def _start_resume(self) -> None:
            if not self._can_resume():
                QtWidgets.QMessageBox.information(self, "Kein Fortsetzen möglich", "Kein Fortsetzungsstand gefunden.")
                return
            try:
                state = load_sort_resume_state(self._resume_path)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Fortsetzen fehlgeschlagen", f"Fortsetzungsstand konnte nicht geladen werden: {exc}")
                return
            self._sort_plan = state.sort_plan
            self._populate_plan_table(state.sort_plan)
            self._failed_action_indices.clear()
            self._update_resume_buttons()
            self._start_operation("execute", start_index=state.resume_from_index)

        def _start_retry_failed(self) -> None:
            if not self._can_retry_failed():
                QtWidgets.QMessageBox.information(self, "Keine fehlgeschlagenen Aktionen", "Es gibt keine fehlgeschlagenen Aktionen zum Wiederholen.")
                return
            indices = sorted(self._failed_action_indices)
            self._failed_action_indices.clear()
            self._update_resume_buttons()
            self._start_operation("execute", only_indices=indices)

        def _cancel(self) -> None:
            self._append_log("Cancel requested by user")
            self._cancel_token.cancel()
            self.btn_cancel.setEnabled(False)

        def _on_phase_changed(self, phase: str, total: int) -> None:
            if phase == "scan":
                self.status_label.setText("Scan läuft…")
                self.progress.setRange(0, 100)
                self.progress.setValue(0)
            elif phase == "plan":
                self.status_label.setText("Plane…")
                self.progress.setRange(0, max(1, int(total)))
                self.progress.setValue(0)
            elif phase == "execute":
                self.status_label.setText("Ausführen…")
                self.progress.setRange(0, max(1, int(total)))
                self.progress.setValue(0)
            elif phase == "audit":
                self.status_label.setText("Prüfe Konvertierungen…")
                self.progress.setRange(0, max(1, int(total)))
                self.progress.setValue(0)

        def _on_progress(self, current: int, total: int) -> None:
            if total and total > 0:
                self.progress.setRange(0, int(total))
                self.progress.setValue(int(current))
            else:
                self.progress.setRange(0, 0)

        def _cleanup_thread(self) -> None:
            if self._thread is not None:
                self._thread.quit()
                self._thread.wait(2000)
            self._thread = None
            self._worker = None

        def _populate_scan_table(self, scan: ScanResult) -> None:
            try:
                sorting_enabled = self.table.isSortingEnabled()
            except Exception:
                sorting_enabled = False
            try:
                self.table.setSortingEnabled(False)
                self.table.setUpdatesEnabled(False)
            except Exception:
                pass

            self.table.setRowCount(len(scan.items))
            for row, item in enumerate(scan.items):

                path_item = QtWidgets.QTableWidgetItem(str(item.input_path or ""))
                self.table.setItem(row, 0, path_item)

                name_item = QtWidgets.QTableWidgetItem(self._rom_display_name(item.input_path))
                if item.input_path:
                    name_item.setToolTip(str(item.input_path))
                self.table.setItem(row, 1, name_item)

                sys_item = QtWidgets.QTableWidgetItem(item.detected_system)
                self.table.setItem(row, 2, sys_item)
                conf_item = QtWidgets.QTableWidgetItem(self._format_confidence(item.detection_confidence))
                try:
                    source = str(item.detection_source or "-")
                    exact = "ja" if getattr(item, "is_exact", False) else "nein"
                    conf_item.setToolTip(f"Quelle: {source}\nExact: {exact}")
                except Exception:
                    pass
                self.table.setItem(row, 3, conf_item)
                self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(self._format_signals(item)))
                self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(self._format_candidates(item)))
                self.table.setItem(row, 6, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(row, 7, QtWidgets.QTableWidgetItem("scan"))
                status_item = QtWidgets.QTableWidgetItem("found")
                try:
                    source = str(item.detection_source or "-")
                    exact = "ja" if getattr(item, "is_exact", False) else "nein"
                    status_item.setToolTip(f"Quelle: {source}\nExact: {exact}")
                except Exception:
                    pass
                min_conf = self._get_min_confidence()
                if not self._is_confident_for_display(item, min_conf):
                    status_item.setText("unknown/low-confidence")
                    try:
                        status_item.setForeground(QtGui.QBrush(QtGui.QColor("#b00020")))
                    except Exception:
                        pass
                self.table.setItem(row, 8, status_item)

            try:
                self.table.setUpdatesEnabled(True)
                self.table.setSortingEnabled(sorting_enabled)
            except Exception:
                pass

            try:
                self.status_label.setText(
                    f"Scan results: {len(scan.items)} (filtered from {len(self._scan_result.items) if self._scan_result else len(scan.items)})"
                )
            except Exception:
                pass

            try:
                min_conf = self._get_min_confidence()
                unknown_count = sum(1 for item in scan.items if not self._is_confident_for_display(item, min_conf))
                self.summary_label.setText(f"{len(scan.items)} gesamt | {unknown_count} unbekannt/niedrige Sicherheit")
            except Exception:
                self.summary_label.setText("-")

        def _populate_plan_table(self, plan: SortPlan) -> None:
            try:
                sorting_enabled = self.table.isSortingEnabled()
            except Exception:
                sorting_enabled = False
            try:
                self.table.setSortingEnabled(False)
                self.table.setUpdatesEnabled(False)
            except Exception:
                pass

            self.table.setRowCount(len(plan.actions))
            for row, act in enumerate(plan.actions):

                path_item = QtWidgets.QTableWidgetItem(str(act.input_path or ""))
                self.table.setItem(row, 0, path_item)

                name_item = QtWidgets.QTableWidgetItem(self._rom_display_name(act.input_path))
                if act.input_path:
                    name_item.setToolTip(str(act.input_path))
                self.table.setItem(row, 1, name_item)

                self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(act.detected_system))
                self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(row, 6, QtWidgets.QTableWidgetItem(act.planned_target_path or ""))
                self.table.setItem(row, 7, QtWidgets.QTableWidgetItem(act.action))
                self.table.setItem(row, 8, QtWidgets.QTableWidgetItem(act.error or act.status))

            try:
                self.table.setUpdatesEnabled(True)
                self.table.setSortingEnabled(sorting_enabled)
            except Exception:
                pass

            try:
                planned = sum(1 for act in plan.actions if str(act.status).startswith("planned"))
                skipped = sum(1 for act in plan.actions if str(act.status).startswith("skipped"))
                errors = sum(1 for act in plan.actions if str(act.status).startswith("error"))
                converts = sum(1 for act in plan.actions if str(act.action) == "convert")
                renames = sum(1 for act in plan.actions if "rename" in str(act.status))
                self.summary_label.setText(
                    f"{planned} geplant | {converts} konvertieren | {renames} umbenennen | {skipped} übersprungen | {errors} Fehler"
                )
            except Exception:
                self.summary_label.setText("-")

        def _populate_audit_table(self, report: ConversionAuditReport) -> None:
            try:
                sorting_enabled = self.table.isSortingEnabled()
            except Exception:
                sorting_enabled = False
            try:
                self.table.setSortingEnabled(False)
                self.table.setUpdatesEnabled(False)
            except Exception:
                pass

            self.table.setRowCount(len(report.items))
            for row, item in enumerate(report.items):
                path_item = QtWidgets.QTableWidgetItem(str(item.input_path or ""))
                self.table.setItem(row, 0, path_item)

                name_item = QtWidgets.QTableWidgetItem(self._rom_display_name(item.input_path))
                if item.input_path:
                    name_item.setToolTip(str(item.input_path))
                self.table.setItem(row, 1, name_item)

                self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(item.detected_system))
                self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(""))

                suggestion = item.current_extension
                if item.recommended_extension and item.recommended_extension != item.current_extension:
                    suggestion = f"{item.current_extension} -> {item.recommended_extension}".strip()
                self.table.setItem(row, 6, QtWidgets.QTableWidgetItem(suggestion))

                action = "convert" if item.status == "should_convert" else "keep"
                self.table.setItem(row, 7, QtWidgets.QTableWidgetItem(action))

                status = item.status
                if item.reason:
                    status = f"{status}: {item.reason}"
                self.table.setItem(row, 8, QtWidgets.QTableWidgetItem(status))

            try:
                self.table.setUpdatesEnabled(True)
                self.table.setSortingEnabled(sorting_enabled)
            except Exception:
                pass

            try:
                totals = report.totals or {}
                self.summary_label.setText(
                    " | ".join(f"{key} {totals.get(key, 0)}" for key in sorted(totals.keys()))
                )
            except Exception:
                self.summary_label.setText("-")

        def _on_action_status(self, row_index: int, status: str) -> None:
            try:
                row = int(row_index)
                if row < 0 or row >= self.table.rowCount():
                    return
                existing = self.table.item(row, 8)
                if existing is None:
                    existing = QtWidgets.QTableWidgetItem(str(status))
                    self.table.setItem(row, 8, existing)
                else:
                    existing.setText(str(status))

                text = str(status)
                if text.lower().startswith("error") or len(text) > 80:
                    existing.setToolTip(text)
                if text.lower().startswith("error"):
                    self._failed_action_indices.add(row)
                    self._update_resume_buttons()
            except Exception:
                # UI must not crash on status update
                return

        def _audit_report_to_dict(self, report: ConversionAuditReport) -> dict:
            return audit_report_to_dict(report)

        def _scan_report_to_dict(self, scan: ScanResult) -> dict:
            return scan_report_to_dict(scan)

        def _plan_report_to_dict(self, plan: SortPlan) -> dict:
            return plan_report_to_dict(plan)

        def _export_scan_json(self) -> None:
            scan = self._scan_result
            if scan is None:
                QtWidgets.QMessageBox.information(self, "Kein Scan", "Bitte zuerst scannen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Scan JSON",
                "scan_report.json",
                "JSON Files (*.json)",
            )
            if not filename:
                return
            self._run_export_task(
                "Scan JSON",
                lambda: write_json(self._scan_report_to_dict(scan), filename),
            )

        def _export_scan_csv(self) -> None:
            scan = self._scan_result
            if scan is None:
                QtWidgets.QMessageBox.information(self, "Kein Scan", "Bitte zuerst scannen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Scan CSV",
                "scan_report.csv",
                "CSV Files (*.csv)",
            )
            if not filename:
                return
            self._run_export_task("Scan CSV", lambda: write_scan_csv(scan, filename))

        def _export_plan_json(self) -> None:
            plan = self._sort_plan
            if plan is None:
                QtWidgets.QMessageBox.information(self, "Kein Plan", "Bitte zuerst Vorschau ausführen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Plan JSON",
                "plan_report.json",
                "JSON Files (*.json)",
            )
            if not filename:
                return
            self._run_export_task(
                "Plan JSON",
                lambda: write_json(self._plan_report_to_dict(plan), filename),
            )

        def _export_plan_csv(self) -> None:
            plan = self._sort_plan
            if plan is None:
                QtWidgets.QMessageBox.information(self, "Kein Plan", "Bitte zuerst Vorschau ausführen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Plan CSV",
                "plan_report.csv",
                "CSV Files (*.csv)",
            )
            if not filename:
                return
            self._run_export_task("Plan CSV", lambda: write_plan_csv(plan, filename))

        def _export_audit_json(self) -> None:
            report = self._audit_report
            if report is None:
                QtWidgets.QMessageBox.information(self, "Kein Audit", "Bitte zuerst Konvertierungen prüfen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Audit JSON",
                "audit_report.json",
                "JSON Files (*.json)",
            )
            if not filename:
                return
            self._run_export_task(
                "Audit JSON",
                lambda: write_json(self._audit_report_to_dict(report), filename),
            )

        def _export_audit_csv(self) -> None:
            report = self._audit_report
            if report is None:
                QtWidgets.QMessageBox.information(self, "Kein Audit", "Bitte zuerst Konvertierungen prüfen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Audit CSV",
                "audit_report.csv",
                "CSV Files (*.csv)",
            )
            if not filename:
                return
            self._run_export_task("Audit CSV", lambda: write_audit_csv(report, filename))

        def _run_export_task(self, label: str, task) -> None:
            if self._export_thread is not None and self._export_thread.isRunning():
                QtWidgets.QMessageBox.information(self, "Export läuft", "Ein Export ist bereits aktiv.")
                return

            thread = QtCore.QThread()
            worker = ExportWorker(label, task)
            worker.moveToThread(thread)

            worker.finished.connect(lambda lbl: self._on_export_finished(lbl))
            worker.failed.connect(lambda msg: self._on_export_failed(msg))
            worker.finished.connect(thread.quit)
            worker.failed.connect(thread.quit)
            thread.finished.connect(lambda: self._cleanup_export_thread())

            self._export_thread = thread
            self._export_worker = worker
            thread.started.connect(worker.run)
            thread.start()

        def _cleanup_export_thread(self) -> None:
            try:
                if self._export_worker is not None:
                    self._export_worker.deleteLater()
            except Exception:
                pass
            try:
                if self._export_thread is not None:
                    self._export_thread.deleteLater()
            except Exception:
                pass
            self._export_thread = None
            self._export_worker = None

        def _on_export_finished(self, label: str) -> None:
            QtWidgets.QMessageBox.information(self, "Export abgeschlossen", f"{label} gespeichert.")

        def _on_export_failed(self, message: str) -> None:
            QtWidgets.QMessageBox.warning(self, "Export fehlgeschlagen", message)

        def _on_finished(self, op: str, payload: object) -> None:
            self._cleanup_thread()
            self._set_running(False)

            if op == "scan":
                if not isinstance(payload, ScanResult):
                    raise RuntimeError("Scan worker returned unexpected payload")
                self._scan_result = payload
                self._refresh_filter_options()
                filtered = self._get_filtered_scan_result()
                self.status_label.setText("Abgebrochen" if payload.cancelled else "Scan abgeschlossen")
                self._populate_scan_table(filtered)
                self._last_view = "scan"
                if payload.cancelled:
                    QtWidgets.QMessageBox.information(self, "Abgebrochen", "Scan abgebrochen.")
                else:
                    QtWidgets.QMessageBox.information(self, "Scan abgeschlossen", f"ROMs gefunden: {len(payload.items)}")
                return

            if op == "plan":
                if not isinstance(payload, SortPlan):
                    raise RuntimeError("Plan worker returned unexpected payload")
                self._sort_plan = payload
                self.status_label.setText("Plan bereit")
                self._populate_plan_table(payload)
                self._last_view = "plan"
                QtWidgets.QMessageBox.information(self, "Vorschau bereit", f"Geplante Aktionen: {len(payload.actions)}")
                return

            if op == "execute":
                if not isinstance(payload, SortReport):
                    raise RuntimeError("Execute worker returned unexpected payload")
                self.status_label.setText("Abgebrochen" if payload.cancelled else "Fertig")
                self._append_summary_row(payload)
                QtWidgets.QMessageBox.information(
                    self,
                    "Fertig",
                    f"Fertig. Kopiert: {payload.copied}, Verschoben: {payload.moved}\nFehler: {len(payload.errors)}\n\nSiehe Log für Details.",
                )
                return

            if op == "audit":
                if not isinstance(payload, ConversionAuditReport):
                    raise RuntimeError("Audit worker returned unexpected payload")
                self.status_label.setText("Abgebrochen" if payload.cancelled else "Audit bereit")
                self._audit_report = payload
                self._populate_audit_table(payload)
                QtWidgets.QMessageBox.information(
                    self,
                    "Audit abgeschlossen",
                    f"Geprüft: {len(payload.items)}\n\nSiehe Tabelle für Vorschläge.",
                )
                self._set_running(False)
                return

        def _on_failed(self, message: str, tb: str) -> None:
            self._append_log(message)
            self._append_log(tb)
            self._cleanup_thread()
            self._set_running(False)
            self.status_label.setText("Error")
            QtWidgets.QMessageBox.critical(self, "Arbeitsfehler", f"{message}\n\n{tb}")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()

    exec_fn = getattr(app, "exec", None) or getattr(app, "exec_")
    return int(exec_fn())
