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
import sqlite3
import sys
import traceback
import threading
import json
from pathlib import Path
from typing import Any, Iterable, List, Optional, cast


def _load_version() -> str:
    config_path = Path(__file__).resolve().parents[3] / "src" / "config.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        meta = data.get("_metadata", {}) if isinstance(data, dict) else {}
        version = str(meta.get("version") or "").strip()
        return version or "1.0.0"
    except Exception:
        return "1.0.0"


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
        DatSourceReport,
        ScanItem,
        ScanResult,
        SortPlan,
        SortReport,
        SortMode,
        audit_conversion_candidates,
        analyze_dat_sources,
        build_dat_index,
        build_library_report,
        execute_sort,
        filter_scan_items,
        get_dat_sources,
        infer_languages_and_version_from_name,
        infer_region_from_name,
        load_sort_resume_state,
        normalize_input,
        plan_sort,
        run_scan,
        save_dat_sources,
    )
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
        write_emulationstation_gamelist,
        write_json,
        write_launchbox_csv,
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
            copy_first: bool,
        ):
            super().__init__()
            self._input_path = input_path
            self._output_dir = output_dir
            self._temp_dir = temp_dir
            self._cancel_token = cancel_token
            self._plan_confirmed = plan_confirmed
            self._explicit_user_action = explicit_user_action
            self._copy_first = copy_first

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
                    copy_first=self._copy_first,
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
                        conversion_mode=cast(ConversionMode, self.conversion_mode),
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
            self._queue_or_run("igir_plan", "IGIR Plan", self._start_igir_plan_now)

        def _start_igir_plan_now(self) -> None:
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
            self._set_igir_running(True)
            self.igir_status_label.setText("Status: Plan läuft...")

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
            thread.started.connect(worker.run)
            thread.start()

    class DatSourcesDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("DAT Quellen")
            self.resize(560, 360)

            self._analysis_thread: Optional[threading.Thread] = None

            layout = QtWidgets.QVBoxLayout(self)

            self.list_widget = QtWidgets.QListWidget()
            layout.addWidget(self.list_widget)

            controls = QtWidgets.QHBoxLayout()
            layout.addLayout(controls)

            self.btn_add = QtWidgets.QPushButton("Hinzufügen…")
            self.btn_remove = QtWidgets.QPushButton("Entfernen")
            self.btn_open = QtWidgets.QPushButton("Ordner öffnen")
            self.btn_refresh = QtWidgets.QPushButton("Integrität prüfen")
            self.btn_coverage = QtWidgets.QPushButton("Coverage anzeigen")
            self.btn_close = QtWidgets.QPushButton("Schließen")

            controls.addWidget(self.btn_add)
            controls.addWidget(self.btn_remove)
            controls.addWidget(self.btn_open)
            controls.addWidget(self.btn_refresh)
            controls.addWidget(self.btn_coverage)
            controls.addStretch(1)
            controls.addWidget(self.btn_close)

            self.status_label = QtWidgets.QLabel("-")
            self.status_label.setWordWrap(True)
            layout.addWidget(self.status_label)

            self.btn_add.clicked.connect(self._add_source)
            self.btn_remove.clicked.connect(self._remove_selected)
            self.btn_open.clicked.connect(self._open_selected)
            self.btn_refresh.clicked.connect(self._refresh_stats)
            self.btn_coverage.clicked.connect(self._show_coverage)
            self.btn_close.clicked.connect(self.accept)

            self._load_sources()

        def _load_sources(self) -> None:
            self.list_widget.clear()
            for path in get_dat_sources():
                self.list_widget.addItem(path)
            if self.list_widget.count() == 0:
                self.status_label.setText("Keine DAT-Pfade konfiguriert.")
            else:
                self._refresh_stats()

        def _get_paths(self) -> list[str]:
            return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]

        def _add_source(self) -> None:
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "DAT-Ordner auswählen")
            if not directory:
                return
            paths = self._get_paths()
            if directory not in paths:
                paths.append(directory)
                save_dat_sources(paths)
                self._load_sources()

        def _remove_selected(self) -> None:
            selected = self.list_widget.selectedItems()
            if not selected:
                return
            paths = [p for p in self._get_paths() if p not in {i.text() for i in selected}]
            save_dat_sources(paths)
            self._load_sources()

        def _open_selected(self) -> None:
            selected = self.list_widget.selectedItems()
            if not selected:
                return
            path = Path(selected[0].text())
            if path.exists():
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))

        def _format_report(self, report: DatSourceReport) -> str:
            total = len(report.paths)
            existing = len(report.existing_paths)
            missing = len(report.missing_paths)
            files_total = report.dat_files + report.dat_xml_files + report.dat_zip_files
            return (
                f"Pfade: {total} | vorhanden: {existing} | fehlend: {missing} | "
                f"DAT/XML/ZIP: {files_total} (dat {report.dat_files}, xml {report.dat_xml_files}, zip {report.dat_zip_files})"
            )

        def _format_coverage(self, report: dict) -> str:
            active = int(report.get("active_dat_files", 0) or 0)
            inactive = int(report.get("inactive_dat_files", 0) or 0)
            roms = int(report.get("rom_hashes", 0) or 0)
            games = int(report.get("game_names", 0) or 0)
            platforms = report.get("platforms", {}) or {}
            summary = f"Coverage: aktiv {active} | inaktiv {inactive} | ROMs {roms} | Games {games}"
            if isinstance(platforms, dict) and platforms:
                top = ", ".join(
                    f"{name}:{(data or {}).get('roms', 0)}"
                    for name, data in list(platforms.items())[:6]
                )
                if top:
                    summary = f"{summary} | {top}"
            return summary

        def _show_coverage(self) -> None:
            index = None
            try:
                index = DatIndexSqlite.from_config()
                report = index.coverage_report()
                message = self._format_coverage(report)
                self.status_label.setText(message)
                QtWidgets.QMessageBox.information(self, "DAT Coverage", message)
            except Exception as exc:
                self.status_label.setText(f"Fehler: {exc}")
                QtWidgets.QMessageBox.warning(self, "DAT Coverage", f"Coverage konnte nicht geladen werden:\n{exc}")
            finally:
                if index is not None:
                    try:
                        index.close()
                    except Exception:
                        pass

        def _refresh_stats(self) -> None:
            if self._analysis_thread is not None and self._analysis_thread.is_alive():
                return
            paths = self._get_paths()
            if not paths:
                self.status_label.setText("Keine DAT-Pfade konfiguriert.")
                return
            self.status_label.setText("Integrität prüfen…")

            def _task() -> None:
                try:
                    report = analyze_dat_sources(paths)
                    QtCore.QTimer.singleShot(0, lambda: self.status_label.setText(self._format_report(report)))
                except Exception as exc:
                    msg = f"Fehler: {exc}"
                    QtCore.QTimer.singleShot(0, lambda msg=msg: self.status_label.setText(msg))

            self._analysis_thread = threading.Thread(target=_task, daemon=True)
            self._analysis_thread.start()

    class MainWindow(QtWidgets.QMainWindow):
        log_signal = Signal(str)
        tools_signal = Signal(object)

        def __init__(self):
            super().__init__()

            self.setWindowTitle(f"ROM Sorter Pro v{_load_version()} - MVP GUI")
            self.resize(1100, 700)

            self._cancel_token = CancelToken()
            self._thread = None
            self._worker = None

            self._scan_result: Optional[ScanResult] = None
            self._sort_plan: Optional[SortPlan] = None
            self._audit_report: Optional[ConversionAuditReport] = None
            self._export_thread: Optional[Any] = None
            self._export_worker: Optional[ExportWorker] = None
            self._igir_thread: Optional[Any] = None
            self._igir_worker: Optional[Any] = None
            self._igir_cancel_token: Optional[CancelToken] = None
            self._igir_plan_ready = False
            self._igir_diff_csv: Optional[str] = None
            self._igir_diff_json: Optional[str] = None
            self._igir_selected_template: Optional[str] = None
            self._failed_action_indices: set[int] = set()
            self._resume_path = str((Path(__file__).resolve().parents[3] / "cache" / "last_sort_resume.json").resolve())

            self._theme_manager = ThemeManager()
            self._syncing_paths = False
            self._log_visible = True
            self._is_running = False

            self._last_view: str = "scan"  # scan|plan
            self._table_items: List[ScanItem] = []
            self._dat_index: Optional[DatIndexSqlite] = None
            self._dat_status_timer = QtCore.QTimer(self)
            self._dat_status_timer.setInterval(800)
            self._dat_status_timer.timeout.connect(self._poll_dat_status)
            self._dat_index_thread: Optional[Any] = None
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
            self.menu_export_frontend_es = QtGui.QAction("Frontend EmulationStation", self)
            self.menu_export_frontend_launchbox = QtGui.QAction("Frontend LaunchBox", self)
            self.menu_export_audit_csv = QtGui.QAction("Audit CSV", self)
            self.menu_export_audit_json = QtGui.QAction("Audit JSON", self)
            export_menu.addAction(self.menu_export_scan_csv)
            export_menu.addAction(self.menu_export_scan_json)
            export_menu.addSeparator()
            export_menu.addAction(self.menu_export_plan_csv)
            export_menu.addAction(self.menu_export_plan_json)
            export_menu.addSeparator()
            export_menu.addAction(self.menu_export_frontend_es)
            export_menu.addAction(self.menu_export_frontend_launchbox)
            export_menu.addSeparator()
            export_menu.addAction(self.menu_export_audit_csv)
            export_menu.addAction(self.menu_export_audit_json)

            root_layout = QtWidgets.QVBoxLayout(central)

            tabs = QtWidgets.QTabWidget()
            self.tabs = tabs
            root_layout.addWidget(tabs)

            dashboard_tab = QtWidgets.QWidget()
            main_tab = QtWidgets.QWidget()
            sort_tab = QtWidgets.QWidget()
            conversions_tab = QtWidgets.QWidget()
            igir_tab = QtWidgets.QWidget()
            db_tab = QtWidgets.QWidget()
            settings_tab = QtWidgets.QWidget()
            tools_tab = QtWidgets.QWidget()
            tabs.addTab(dashboard_tab, "🏠 Dashboard")
            tabs.addTab(main_tab, "🧭 Arbeitsbereich")
            tabs.addTab(sort_tab, "🗂️ Sortierung")
            tabs.addTab(conversions_tab, "🧰 Konvertierungen")
            tabs.addTab(igir_tab, "🧪 IGIR")
            tabs.addTab(db_tab, "🗃️ Datenbank")
            tabs.addTab(settings_tab, "⚙️ Einstellungen")
            self._tab_index_main = tabs.indexOf(main_tab)
            self._tab_index_dashboard = tabs.indexOf(dashboard_tab)
            show_external_tools = False
            if show_external_tools:
                tabs.addTab(tools_tab, "External Tools")
            tabs.setCurrentIndex(0)

            dashboard_layout = QtWidgets.QVBoxLayout(dashboard_tab)
            main_layout = QtWidgets.QVBoxLayout(main_tab)
            sort_tab_layout = QtWidgets.QVBoxLayout(sort_tab)
            conversions_layout = QtWidgets.QVBoxLayout(conversions_tab)
            igir_layout = QtWidgets.QVBoxLayout(igir_tab)
            db_layout = QtWidgets.QVBoxLayout(db_tab)
            settings_layout = QtWidgets.QVBoxLayout(settings_tab)
            tools_layout = QtWidgets.QVBoxLayout(tools_tab)

            dashboard_title = QtWidgets.QLabel("Willkommen")
            dashboard_title.setStyleSheet("font-size: 18px; font-weight: 700;")
            dashboard_layout.addWidget(dashboard_title)

            dashboard_hint = QtWidgets.QLabel(
                "Starte mit einem Scan oder öffne den Arbeitsbereich für Details."
            )
            dashboard_hint.setWordWrap(True)
            dashboard_layout.addWidget(dashboard_hint)

            quick_group = QtWidgets.QGroupBox("Schnellstart")
            quick_layout = QtWidgets.QHBoxLayout(quick_group)
            self.btn_dash_scan = QtWidgets.QPushButton("🔍 Scannen")
            self.btn_dash_preview = QtWidgets.QPushButton("🧾 Vorschau (Dry-run)")
            self.btn_dash_execute = QtWidgets.QPushButton("🚀 Sortieren ausführen")
            self.btn_dash_scan.setToolTip("Scannt den Quellordner")
            self.btn_dash_preview.setToolTip("Erstellt einen Sortierplan ohne Änderungen")
            self.btn_dash_execute.setToolTip("Führt den Plan aus")
            self.btn_dash_scan.setMinimumHeight(34)
            self.btn_dash_preview.setMinimumHeight(34)
            self.btn_dash_execute.setMinimumHeight(34)
            quick_layout.addWidget(self.btn_dash_scan)
            quick_layout.addWidget(self.btn_dash_preview)
            quick_layout.addWidget(self.btn_dash_execute)
            quick_layout.addStretch(1)
            dashboard_layout.addWidget(quick_group)

            dnd_enabled = self._is_drag_drop_enabled()
            paths_dashboard_group = QtWidgets.QGroupBox("Pfade")
            paths_dashboard_layout = QtWidgets.QGridLayout(paths_dashboard_group)
            paths_dashboard_layout.addWidget(QtWidgets.QLabel("Quelle:"), 0, 0)
            self.dashboard_source_edit = DropLineEdit(self._on_drop_source, enabled=dnd_enabled)
            self.dashboard_source_edit.setPlaceholderText("ROM-Quelle auswählen")
            paths_dashboard_layout.addWidget(self.dashboard_source_edit, 0, 1)
            self.btn_dash_source = QtWidgets.QPushButton("Quelle wählen…")
            self.btn_dash_source.clicked.connect(self._choose_source)
            paths_dashboard_layout.addWidget(self.btn_dash_source, 0, 2)

            paths_dashboard_layout.addWidget(QtWidgets.QLabel("Ziel:"), 1, 0)
            self.dashboard_dest_edit = DropLineEdit(self._on_drop_dest, enabled=dnd_enabled)
            self.dashboard_dest_edit.setPlaceholderText("Zielordner auswählen")
            paths_dashboard_layout.addWidget(self.dashboard_dest_edit, 1, 1)
            self.btn_dash_dest = QtWidgets.QPushButton("Ziel wählen…")
            self.btn_dash_dest.clicked.connect(self._choose_dest)
            paths_dashboard_layout.addWidget(self.btn_dash_dest, 1, 2)
            self.btn_dash_open_dest = QtWidgets.QPushButton("Ziel öffnen")
            self.btn_dash_open_dest.clicked.connect(self._open_destination)
            paths_dashboard_layout.addWidget(self.btn_dash_open_dest, 1, 3)
            paths_dashboard_layout.setColumnStretch(1, 1)
            dashboard_layout.addWidget(paths_dashboard_group)

            self.dashboard_path_hint = QtWidgets.QLabel(
                "Quelle und Ziel setzen, damit Schnellstart aktiv wird."
            )
            self.dashboard_path_hint.setWordWrap(True)
            self.dashboard_path_hint.setStyleSheet("color: #777;")
            dashboard_layout.addWidget(self.dashboard_path_hint)

            status_group = QtWidgets.QGroupBox("Status")
            status_layout = QtWidgets.QGridLayout(status_group)
            status_layout.addWidget(QtWidgets.QLabel("📁 Quelle:"), 0, 0)
            self.dashboard_source_label = QtWidgets.QLabel("-")
            self.dashboard_source_label.setWordWrap(True)
            status_layout.addWidget(self.dashboard_source_label, 0, 1)
            status_layout.addWidget(QtWidgets.QLabel("🎯 Ziel:"), 1, 0)
            self.dashboard_dest_label = QtWidgets.QLabel("-")
            self.dashboard_dest_label.setWordWrap(True)
            status_layout.addWidget(self.dashboard_dest_label, 1, 1)
            status_layout.addWidget(QtWidgets.QLabel("📊 Status:"), 2, 0)
            self.dashboard_status_label = QtWidgets.QLabel("-")
            status_layout.addWidget(self.dashboard_status_label, 2, 1)
            self.dashboard_progress = QtWidgets.QProgressBar()
            self.dashboard_progress.setRange(0, 100)
            self.dashboard_progress.setValue(0)
            status_layout.addWidget(self.dashboard_progress, 3, 0, 1, 2)
            status_layout.addWidget(QtWidgets.QLabel("🧷 DAT:"), 4, 0)
            self.dashboard_dat_label = QtWidgets.QLabel("-")
            status_layout.addWidget(self.dashboard_dat_label, 4, 1)
            dashboard_layout.addWidget(status_group)
            dashboard_layout.addStretch(1)

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

            main_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
            main_layout.addWidget(main_splitter, 1)
            left_panel = QtWidgets.QWidget()
            right_panel = QtWidgets.QWidget()
            main_splitter.addWidget(left_panel)
            main_splitter.addWidget(right_panel)
            main_splitter.setStretchFactor(0, 0)
            main_splitter.setStretchFactor(1, 1)

            left_layout = QtWidgets.QVBoxLayout(left_panel)
            right_layout = QtWidgets.QVBoxLayout(right_panel)
            main_status_group = QtWidgets.QGroupBox("Status")
            main_status_layout = QtWidgets.QGridLayout(main_status_group)
            main_status_layout.setHorizontalSpacing(6)
            main_status_layout.setVerticalSpacing(4)

            self.main_source_label = QtWidgets.QLabel("-")
            self.main_source_label.setWordWrap(True)
            self.main_dest_label = QtWidgets.QLabel("-")
            self.main_dest_label.setWordWrap(True)

            self.progress = QtWidgets.QProgressBar()
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.status_label = QtWidgets.QLabel(f"Bereit ({binding})")
            self.summary_label = QtWidgets.QLabel("-")

            main_status_layout.addWidget(QtWidgets.QLabel("Quelle:"), 0, 0)
            main_status_layout.addWidget(self.main_source_label, 0, 1)
            main_status_layout.addWidget(QtWidgets.QLabel("Ziel:"), 1, 0)
            main_status_layout.addWidget(self.main_dest_label, 1, 1)
            main_status_layout.addWidget(self.progress, 2, 0, 1, 2)
            main_status_layout.addWidget(self.status_label, 3, 0, 1, 2)
            main_status_layout.addWidget(self.summary_label, 4, 0, 1, 2)
            main_status_layout.setColumnStretch(1, 1)
            left_layout.addWidget(main_status_group)
            left_layout.addLayout(sections_row)

            presets_group = QtWidgets.QGroupBox("Presets & Auswahl")
            presets_layout = QtWidgets.QGridLayout(presets_group)
            presets_layout.setHorizontalSpacing(6)
            presets_layout.setVerticalSpacing(6)
            self.preset_combo = QtWidgets.QComboBox()
            self.preset_combo.addItem("-")
            self.preset_name_edit = QtWidgets.QLineEdit()
            self.preset_name_edit.setPlaceholderText("Preset-Name")
            self.btn_preset_apply = QtWidgets.QPushButton("Übernehmen")
            self.btn_preset_save = QtWidgets.QPushButton("Speichern")
            self.btn_preset_delete = QtWidgets.QPushButton("Löschen")
            self.btn_execute_selected = QtWidgets.QPushButton("Auswahl ausführen")
            presets_layout.addWidget(QtWidgets.QLabel("Preset:"), 0, 0)
            presets_layout.addWidget(self.preset_combo, 0, 1)
            presets_layout.addWidget(self.btn_preset_apply, 0, 2)
            presets_layout.addWidget(self.preset_name_edit, 1, 0, 1, 2)
            presets_layout.addWidget(self.btn_preset_save, 1, 2)
            presets_layout.addWidget(self.btn_preset_delete, 2, 2)
            presets_layout.addWidget(self.btn_execute_selected, 2, 0, 1, 2)
            presets_layout.setColumnStretch(1, 1)

            left_layout.addWidget(filters_group)
            left_layout.addWidget(presets_group)

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
            self.igir_templates_view = QtWidgets.QPlainTextEdit()
            self.igir_templates_view.setReadOnly(True)
            self.igir_templates_view.setPlaceholderText("Templates from igir.yaml (read-only)")
            self.igir_template_combo = QtWidgets.QComboBox()
            self.igir_template_combo.addItem("-")
            self.btn_igir_apply_template = QtWidgets.QPushButton("Template übernehmen")
            self.igir_profile_combo = QtWidgets.QComboBox()
            self.igir_profile_combo.addItem("-")
            self.btn_igir_apply_profile = QtWidgets.QPushButton("Profil aktivieren")
            self.btn_igir_browse = QtWidgets.QPushButton("IGIR wählen…")
            self.btn_igir_save = QtWidgets.QPushButton("IGIR speichern")
            self.btn_igir_probe = QtWidgets.QPushButton("IGIR prüfen")
            self.btn_igir_plan = QtWidgets.QPushButton("Plan erstellen")
            self.btn_igir_execute = QtWidgets.QPushButton("Ausführen")
            self.btn_igir_execute.setEnabled(False)
            self.btn_igir_cancel = QtWidgets.QPushButton("IGIR abbrechen")
            self.btn_igir_cancel.setEnabled(False)
            self.igir_status_label = QtWidgets.QLabel("Status: -")
            self.igir_copy_first_checkbox = QtWidgets.QCheckBox("Copy-first (Staging)")
            self.igir_source_edit = QtWidgets.QLineEdit()
            self.igir_dest_edit = QtWidgets.QLineEdit()
            self.igir_source_edit.setPlaceholderText("Quelle (aus Haupt-Tab)")
            self.igir_dest_edit.setPlaceholderText("Ziel (aus Haupt-Tab)")
            self.igir_source_edit.setReadOnly(True)
            self.igir_dest_edit.setReadOnly(True)

            self.mode_combo = QtWidgets.QComboBox()
            self.mode_combo.addItems(["copy", "move"])

            self.conflict_combo = QtWidgets.QComboBox()
            self.conflict_combo.addItems(["rename", "skip", "overwrite"])

            self.rebuild_checkbox = QtWidgets.QCheckBox("Rebuilder-Modus (Copy-only, Konflikte überspringen)")

            self.lang_filter = QtWidgets.QListWidget()
            self.lang_filter.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
            self.lang_filter.addItems(["All"])
            self.lang_filter.setMinimumWidth(160)
            self.lang_filter.setMaximumHeight(90)

            self.ver_filter = QtWidgets.QComboBox()
            self.ver_filter.addItems(["All"])
            self.ver_filter.setMinimumWidth(160)

            self.region_filter = QtWidgets.QListWidget()
            self.region_filter.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
            self.region_filter.addItems(["All"])
            self.region_filter.setMinimumWidth(160)
            self.region_filter.setMaximumHeight(90)

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
            self.btn_manage_dat = QtWidgets.QPushButton("DAT Quellen…")
            self.btn_open_overrides = QtWidgets.QPushButton("Mapping Overrides öffnen")

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
            if hasattr(self, "dashboard_source_edit"):
                self.dashboard_source_edit.textChanged.connect(self._on_source_text_changed)
            if hasattr(self, "dashboard_dest_edit"):
                self.dashboard_dest_edit.textChanged.connect(self._on_dest_text_changed)

            paths_layout.setColumnStretch(1, 1)

            actions_layout.addWidget(QtWidgets.QLabel("Aktion:"), 0, 0)
            actions_layout.addWidget(self.mode_combo, 0, 1)

            actions_layout.addWidget(QtWidgets.QLabel("Bei Konflikt:"), 1, 0)
            actions_layout.addWidget(self.conflict_combo, 1, 1)

            actions_layout.addWidget(self.rebuild_checkbox, 2, 1)

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
            settings_form.setColumnStretch(1, 1)

            self.log_visible_checkbox = QtWidgets.QCheckBox("Log standardmäßig anzeigen")
            self.remember_window_checkbox = QtWidgets.QCheckBox("Fenstergröße merken")
            self.drag_drop_checkbox = QtWidgets.QCheckBox("Drag & Drop aktivieren")
            settings_form.addWidget(self.log_visible_checkbox, 1, 1)
            settings_form.addWidget(self.remember_window_checkbox, 2, 1)
            settings_form.addWidget(self.drag_drop_checkbox, 3, 1)
            settings_form.addWidget(self.dat_auto_load_checkbox, 4, 1)

            sort_intro = QtWidgets.QLabel("Sortieroptionen für die Zielstruktur.")
            sort_intro.setWordWrap(True)
            sort_tab_layout.addWidget(sort_intro)
            defaults_group = QtWidgets.QGroupBox("Standardwerte")
            defaults_layout = QtWidgets.QGridLayout(defaults_group)
            defaults_layout.setHorizontalSpacing(10)
            defaults_layout.setVerticalSpacing(6)
            self.default_mode_combo = QtWidgets.QComboBox()
            self.default_mode_combo.addItems(["copy", "move"])
            self.default_conflict_combo = QtWidgets.QComboBox()
            self.default_conflict_combo.addItems(["rename", "skip", "overwrite"])
            defaults_layout.addWidget(QtWidgets.QLabel("Standardmodus:"), 0, 0)
            defaults_layout.addWidget(self.default_mode_combo, 0, 1)
            defaults_layout.addWidget(QtWidgets.QLabel("Standard-Konflikte:"), 1, 0)
            defaults_layout.addWidget(self.default_conflict_combo, 1, 1)
            defaults_layout.setColumnStretch(1, 1)
            sort_tab_layout.addWidget(defaults_group)
            sort_group = QtWidgets.QGroupBox("Sortieroptionen")
            sort_layout = QtWidgets.QVBoxLayout(sort_group)
            sort_layout.addWidget(self.chk_console_folders)
            sort_layout.addWidget(self.chk_region_subfolders)
            sort_layout.addWidget(self.chk_preserve_structure)
            sort_tab_layout.addWidget(sort_group)
            sort_tab_layout.addStretch(1)

            db_intro = QtWidgets.QLabel("Datenbank- und DAT-Index-Verwaltung.")
            db_intro.setWordWrap(True)
            db_layout.addWidget(db_intro)

            dat_hint = QtWidgets.QLabel(
                "DAT-Index wird als SQLite unter data/index/romsorter_dat_index.sqlite gespeichert. "
                "Lege DAT-Dateien in einem eigenen Ordner ab und baue den Index bei Änderungen neu."
            )
            dat_hint.setWordWrap(True)
            db_layout.addWidget(dat_hint)

            db_form = QtWidgets.QGridLayout()
            db_form.setHorizontalSpacing(10)
            db_form.setVerticalSpacing(6)
            db_layout.addLayout(db_form)

            db_form.addWidget(self.dat_status, 0, 0)
            db_form.addWidget(self.btn_add_dat, 0, 1)
            db_form.addWidget(self.btn_refresh_dat, 0, 2)
            db_form.addWidget(self.btn_cancel_dat, 0, 3)
            db_form.addWidget(self.btn_manage_dat, 0, 4)

            db_form.addWidget(self.btn_clear_dat_cache, 1, 2)
            db_form.addWidget(self.btn_open_overrides, 1, 3)

            db_form.addWidget(self.db_status, 2, 0)
            db_form.addWidget(self.btn_db_manager, 2, 1)
            db_form.setColumnStretch(1, 1)

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
            left_layout.addWidget(sort_title)
            left_layout.addLayout(button_row)

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
            self.btn_export_frontend_es = QtWidgets.QPushButton("Frontend ES exportieren")
            self.btn_export_frontend_launchbox = QtWidgets.QPushButton("Frontend LaunchBox exportieren")
            self.btn_resume = QtWidgets.QPushButton("Fortsetzen")
            self.btn_retry_failed = QtWidgets.QPushButton("Fehlgeschlagene erneut")
            self.btn_cancel = QtWidgets.QPushButton("Abbrechen")

            self.btn_scan.setToolTip("Scannt den Quellordner und erkennt Konsolen")
            self.btn_preview.setToolTip("Erstellt einen Sortierplan ohne Dateien zu ändern")
            self.btn_execute.setToolTip("Führt den Plan aus (ohne Konvertierungen)")
            self.btn_execute_convert.setToolTip("Führt Sortierung inkl. Konvertierung aus")
            self.btn_audit.setToolTip("Prüft Konvertierungen ohne Änderungen")
            self.btn_scan.setDefault(True)

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
                self.btn_export_frontend_es,
                self.btn_export_frontend_launchbox,
                self.btn_resume,
                self.btn_retry_failed,
                self.btn_cancel,
            ):
                btn.setMinimumHeight(28)
                if btn in (self.btn_scan, self.btn_preview, self.btn_execute):
                    btn.setMinimumWidth(200)

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

            conversions_quick = QtWidgets.QGroupBox("Schnellstart")
            conversions_quick_layout = QtWidgets.QHBoxLayout(conversions_quick)
            conversions_quick_layout.addWidget(self.btn_execute_convert)
            conversions_quick_layout.addWidget(self.btn_audit)
            conversions_quick_layout.addStretch(1)
            conversions_layout.addWidget(conversions_quick)

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
            conversions_row.addWidget(self.btn_export_audit_csv, 0, 0)
            conversions_row.addWidget(self.btn_export_audit_json, 0, 1)
            conversions_row.addWidget(self.btn_export_scan_csv, 1, 0)
            conversions_row.addWidget(self.btn_export_scan_json, 1, 1)
            conversions_row.addWidget(self.btn_export_plan_csv, 2, 0)
            conversions_row.addWidget(self.btn_export_plan_json, 2, 1)
            conversions_row.addWidget(self.btn_export_frontend_es, 3, 0)
            conversions_row.addWidget(self.btn_export_frontend_launchbox, 3, 1)
            conversions_row.setColumnStretch(2, 1)
            conversions_layout.addStretch(1)

            igir_intro = QtWidgets.QLabel(
                "IGIR ist ein externes Tool. Erstellt zuerst einen Plan und führt dann aus (niemals im Dry-Run)."
            )
            igir_intro.setWordWrap(True)
            igir_layout.addWidget(igir_intro)

            igir_quick = QtWidgets.QGroupBox("Schnellstart")
            igir_quick_layout = QtWidgets.QHBoxLayout(igir_quick)
            igir_quick_layout.addWidget(self.btn_igir_plan)
            igir_quick_layout.addWidget(self.btn_igir_execute)
            igir_quick_layout.addStretch(1)
            igir_layout.addWidget(igir_quick)

            self.igir_advanced_toggle = QtWidgets.QCheckBox("Erweitert anzeigen")
            self.igir_advanced_toggle.setChecked(False)
            igir_layout.addWidget(self.igir_advanced_toggle)

            igir_cfg_group = QtWidgets.QGroupBox("Erweitert: IGIR Konfiguration")
            igir_cfg_layout = QtWidgets.QGridLayout(igir_cfg_group)
            igir_cfg_layout.setHorizontalSpacing(6)
            igir_cfg_layout.setVerticalSpacing(6)
            igir_cfg_layout.addWidget(QtWidgets.QLabel("IGIR Executable:"), 0, 0)
            igir_cfg_layout.addWidget(self.igir_exe_edit, 0, 1)
            igir_cfg_layout.addWidget(self.btn_igir_browse, 0, 2)
            igir_cfg_layout.addWidget(QtWidgets.QLabel("Args Template:"), 1, 0)
            igir_cfg_layout.addWidget(self.igir_args_edit, 1, 1, 2, 2)
            igir_cfg_layout.addWidget(QtWidgets.QLabel("Standard Templates:"), 3, 0)
            igir_cfg_layout.addWidget(self.igir_templates_view, 3, 1, 2, 2)
            igir_cfg_layout.addWidget(QtWidgets.QLabel("Template übernehmen:"), 5, 0)
            igir_cfg_layout.addWidget(self.igir_template_combo, 5, 1)
            igir_cfg_layout.addWidget(self.btn_igir_apply_template, 5, 2)
            igir_cfg_layout.addWidget(QtWidgets.QLabel("Profil:"), 6, 0)
            igir_cfg_layout.addWidget(self.igir_profile_combo, 6, 1)
            igir_cfg_layout.addWidget(self.btn_igir_apply_profile, 6, 2)
            igir_cfg_layout.setColumnStretch(1, 1)
            igir_actions_row = QtWidgets.QHBoxLayout()
            igir_actions_row.addWidget(self.btn_igir_save)
            igir_actions_row.addWidget(self.btn_igir_probe)
            igir_actions_row.addStretch(1)
            igir_cfg_layout.addLayout(igir_actions_row, 7, 1, 1, 2)
            igir_layout.addWidget(igir_cfg_group)
            self._igir_cfg_group = igir_cfg_group
            self._set_igir_advanced_visible(False)

            igir_run_group = QtWidgets.QGroupBox("Ausführen")
            igir_run_layout = QtWidgets.QGridLayout(igir_run_group)
            igir_run_layout.setHorizontalSpacing(6)
            igir_run_layout.setVerticalSpacing(6)
            igir_run_layout.addWidget(QtWidgets.QLabel("Quelle:"), 0, 0)
            igir_run_layout.addWidget(self.igir_source_edit, 0, 1)
            igir_run_layout.addWidget(QtWidgets.QLabel("Ziel:"), 1, 0)
            igir_run_layout.addWidget(self.igir_dest_edit, 1, 1)
            igir_run_layout.addWidget(self.btn_igir_cancel, 2, 0)
            igir_run_layout.addWidget(self.igir_status_label, 3, 0, 1, 3)
            igir_run_layout.addWidget(self.igir_copy_first_checkbox, 4, 0, 1, 2)
            self.btn_igir_open_diff_csv = QtWidgets.QPushButton("Diff CSV öffnen")
            self.btn_igir_open_diff_json = QtWidgets.QPushButton("Diff JSON öffnen")
            self.btn_igir_open_diff_csv.setEnabled(False)
            self.btn_igir_open_diff_json.setEnabled(False)
            igir_run_layout.addWidget(self.btn_igir_open_diff_csv, 5, 0)
            igir_run_layout.addWidget(self.btn_igir_open_diff_json, 5, 1)
            igir_run_layout.setColumnStretch(1, 1)
            igir_layout.addWidget(igir_run_group)
            igir_layout.addStretch(1)

            self.btn_why_unknown = QtWidgets.QPushButton("Why Unknown?")
            self.btn_why_unknown.clicked.connect(self._show_why_unknown)
            right_layout.addWidget(self.btn_why_unknown)

            report_row = QtWidgets.QHBoxLayout()
            self.btn_library_report = QtWidgets.QPushButton("Bibliothek-Report")
            self.btn_library_report_save = QtWidgets.QPushButton("Report speichern…")
            report_row.addWidget(self.btn_library_report)
            report_row.addWidget(self.btn_library_report_save)
            report_row.addStretch(1)
            right_layout.addLayout(report_row)

            results_intro = QtWidgets.QLabel(
                "Die Ergebnistabelle zeigt geplante Ziele und Status. Nutze die Vorschau vor dem Ausführen."
            )
            results_intro.setWordWrap(True)
            right_layout.addWidget(results_intro)

            self.results_empty_label = QtWidgets.QLabel(
                "Noch keine Ergebnisse. Starte mit Scan oder Vorschau, um Einträge zu sehen."
            )
            self.results_empty_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.results_empty_label.setStyleSheet("color: #777; padding: 8px;")
            right_layout.addWidget(self.results_empty_label)

            queue_group = QtWidgets.QGroupBox("Jobs")
            queue_layout = QtWidgets.QGridLayout(queue_group)
            queue_layout.setHorizontalSpacing(6)
            queue_layout.setVerticalSpacing(6)
            self.queue_mode_checkbox = QtWidgets.QCheckBox("Queue mode")
            self.queue_priority_combo = QtWidgets.QComboBox()
            self.queue_priority_combo.addItems(["Normal", "High", "Low"])
            self.queue_pause_btn = QtWidgets.QPushButton("Pause")
            self.queue_resume_btn = QtWidgets.QPushButton("Resume")
            self.queue_clear_btn = QtWidgets.QPushButton("Clear")
            self.queue_resume_btn.setEnabled(False)
            self.queue_list = QtWidgets.QListWidget()
            self.queue_list.setMaximumHeight(90)
            queue_layout.addWidget(QtWidgets.QLabel("Priorität:"), 0, 0)
            queue_layout.addWidget(self.queue_priority_combo, 0, 1)
            queue_layout.addWidget(self.queue_mode_checkbox, 0, 2)
            queue_layout.addWidget(self.queue_pause_btn, 1, 0)
            queue_layout.addWidget(self.queue_resume_btn, 1, 1)
            queue_layout.addWidget(self.queue_clear_btn, 1, 2)
            queue_layout.addWidget(self.queue_list, 2, 0, 1, 3)
            left_layout.addWidget(queue_group)

            self.table = QtWidgets.QTableWidget(0, 11)
            self.table.setHorizontalHeaderLabels(
                [
                    "Status/Fehler",
                    "Aktion",
                    "Eingabepfad",
                    "Name",
                    "Erkannte Konsole/Typ",
                    "Sicherheit",
                    "Signale",
                    "Kandidaten",
                    "Geplantes Ziel",
                    "Normalisierung",
                    "Grund",
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
            right_layout.addWidget(self.table, 2)

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
            self.log_filter_edit = QtWidgets.QLineEdit()
            self.log_filter_edit.setPlaceholderText("Log filtern…")
            self.log_filter_clear_btn = QtWidgets.QPushButton("Filter löschen")

            log_header = QtWidgets.QHBoxLayout()
            log_header.addWidget(log_title)
            log_header.addWidget(self.log_filter_edit)
            log_header.addWidget(self.log_filter_clear_btn)
            log_header.addStretch(1)
            log_header.addWidget(self.log_toggle_btn)
            root_layout.addLayout(log_header)
            root_layout.addWidget(self.log_view, 1)
            root_layout.addWidget(log_hint)
            self.log_hint_label = log_hint


            self._log_buffer = []
            self._log_history: List[str] = []
            self._log_filter_text = ""
            self._log_flush_timer = QtCore.QTimer(self)
            self._log_flush_timer.setInterval(100)
            self._log_flush_timer.timeout.connect(self._flush_log)
            self._log_flush_timer.start()

            self._job_queue: List[dict[str, object]] = []
            self._job_active: Optional[dict[str, object]] = None
            self._job_paused = False
            self._job_counter = 0
            self._current_op: Optional[str] = None

            self.log_signal.connect(self._append_log)
            self.tools_signal.connect(self._on_tools_status)
            self._install_log_handler()

            self.log_filter_edit.textChanged.connect(self._apply_log_filter)
            self.log_filter_clear_btn.clicked.connect(lambda: self.log_filter_edit.setText(""))
            self.queue_pause_btn.clicked.connect(self._pause_jobs)
            self.queue_resume_btn.clicked.connect(self._resume_jobs)
            self.queue_clear_btn.clicked.connect(self._clear_job_queue)
            self.igir_advanced_toggle.stateChanged.connect(self._on_igir_advanced_toggle)

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
            self.btn_igir_apply_template.clicked.connect(self._apply_igir_template)
            self.btn_igir_apply_profile.clicked.connect(self._apply_igir_profile)
            self.btn_igir_plan.clicked.connect(self._start_igir_plan)
            self.btn_igir_execute.clicked.connect(self._start_igir_execute)
            self.btn_igir_cancel.clicked.connect(self._cancel_igir)
            self.btn_igir_open_diff_csv.clicked.connect(lambda: self._open_igir_diff(self._igir_diff_csv))
            self.btn_igir_open_diff_json.clicked.connect(lambda: self._open_igir_diff(self._igir_diff_json))
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
            self.btn_export_frontend_es.clicked.connect(self._export_frontend_es)
            self.btn_export_frontend_launchbox.clicked.connect(self._export_frontend_launchbox)
            self.menu_export_scan_csv.triggered.connect(self._export_scan_csv)
            self.menu_export_scan_json.triggered.connect(self._export_scan_json)
            self.menu_export_plan_csv.triggered.connect(self._export_plan_csv)
            self.menu_export_plan_json.triggered.connect(self._export_plan_json)
            self.menu_export_frontend_es.triggered.connect(self._export_frontend_es)
            self.menu_export_frontend_launchbox.triggered.connect(self._export_frontend_launchbox)
            self.menu_export_audit_csv.triggered.connect(self._export_audit_csv)
            self.menu_export_audit_json.triggered.connect(self._export_audit_json)
            self.btn_resume.clicked.connect(self._start_resume)
            self.btn_retry_failed.clicked.connect(self._start_retry_failed)
            self.btn_cancel.clicked.connect(self._cancel)
            self.lang_filter.itemSelectionChanged.connect(self._on_filters_changed)
            self.ver_filter.currentTextChanged.connect(self._on_filters_changed)
            self.region_filter.itemSelectionChanged.connect(self._on_filters_changed)
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
            self.btn_manage_dat.clicked.connect(self._open_dat_sources_dialog)
            self.btn_open_overrides.clicked.connect(self._open_identification_overrides)
            self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
            self.btn_db_manager.clicked.connect(self._open_db_manager)
            self.log_visible_checkbox.stateChanged.connect(self._on_log_visible_changed)
            self.remember_window_checkbox.stateChanged.connect(self._on_remember_window_changed)
            self.drag_drop_checkbox.stateChanged.connect(self._on_drag_drop_changed)
            self.btn_preset_apply.clicked.connect(self._apply_selected_preset)
            self.btn_preset_save.clicked.connect(self._save_preset)
            self.btn_preset_delete.clicked.connect(self._delete_selected_preset)
            self.btn_execute_selected.clicked.connect(self._start_execute_selected)
            self.btn_library_report.clicked.connect(self._show_library_report)
            self.btn_library_report_save.clicked.connect(self._save_library_report)
            self.default_mode_combo.currentTextChanged.connect(self._on_default_mode_changed)
            self.default_conflict_combo.currentTextChanged.connect(self._on_default_conflict_changed)
            self.chk_console_folders.stateChanged.connect(self._on_sort_settings_changed)
            self.chk_region_subfolders.stateChanged.connect(self._on_sort_settings_changed)
            self.chk_preserve_structure.stateChanged.connect(self._on_sort_settings_changed)
            self.rebuild_checkbox.stateChanged.connect(self._on_rebuild_toggle)
            self.btn_dash_scan.clicked.connect(self._start_scan)
            self.btn_dash_preview.clicked.connect(self._start_preview)
            self.btn_dash_execute.clicked.connect(self._start_execute)

            self._apply_theme(self._theme_manager.get_theme())
            self._load_theme_from_config()
            self._load_dat_settings_from_config()
            self._load_sort_settings_from_config()
            self._load_igir_settings_from_config()
            self._refresh_filter_options()
            self._refresh_db_status()
            self._load_window_size()
            self._load_log_visibility()
            self._load_general_settings_from_config()
            self._load_presets_from_config()
            self._dashboard_timer = QtCore.QTimer(self)
            self._dashboard_timer.setInterval(600)
            self._dashboard_timer.timeout.connect(self._refresh_dashboard)
            self._dashboard_timer.start()
            self._refresh_dashboard()
            self._update_results_empty_state()
            self._refresh_dashboard()
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
                templates = data.get("templates") or {}
                self._igir_templates = templates if isinstance(templates, dict) else {}
                self.igir_template_combo.blockSignals(True)
                self.igir_template_combo.clear()
                self.igir_template_combo.addItem("-")
                if isinstance(self._igir_templates, dict):
                    for name in sorted(self._igir_templates.keys()):
                        self.igir_template_combo.addItem(str(name))
                self.igir_template_combo.blockSignals(False)
                templates_text = ""
                if isinstance(templates, dict):
                    blocks = []
                    for name, spec in templates.items():
                        if not isinstance(spec, dict):
                            continue
                        plan = spec.get("plan") or []
                        execute = spec.get("execute") or []
                        if isinstance(plan, str):
                            plan = [plan]
                        if isinstance(execute, str):
                            execute = [execute]
                        blocks.append(
                            "\n".join(
                                [
                                    f"[{name}]",
                                    "plan:",
                                    *[f"  {arg}" for arg in plan],
                                    "execute:",
                                    *[f"  {arg}" for arg in execute],
                                ]
                            )
                        )
                    templates_text = "\n\n".join(blocks)
                self.igir_templates_view.setPlainText(templates_text)
                profiles = data.get("profiles") or {}
                self._igir_profiles = profiles if isinstance(profiles, dict) else {}
                self.igir_profile_combo.blockSignals(True)
                self.igir_profile_combo.clear()
                self.igir_profile_combo.addItem("-")
                if isinstance(self._igir_profiles, dict):
                    for name in sorted(self._igir_profiles.keys()):
                        self.igir_profile_combo.addItem(str(name))
                active_profile = str(data.get("active_profile") or "").strip()
                if active_profile:
                    idx_profile = self.igir_profile_combo.findText(active_profile)
                    if idx_profile >= 0:
                        self.igir_profile_combo.setCurrentIndex(idx_profile)
                        self._igir_selected_profile = active_profile
                self.igir_profile_combo.blockSignals(False)
                try:
                    self.igir_copy_first_checkbox.setChecked(bool(data.get("copy_first", False)))
                except Exception:
                    pass
            except Exception:
                return

        def _apply_igir_template(self) -> None:
            try:
                name = str(self.igir_template_combo.currentText() or "").strip()
                if not name or name == "-":
                    self.igir_status_label.setText("Status: Template wählen")
                    return
                templates = getattr(self, "_igir_templates", {}) or {}
                spec = templates.get(name) if isinstance(templates, dict) else None
                if not isinstance(spec, dict):
                    self.igir_status_label.setText("Status: Template ungültig")
                    return
                args = spec.get("execute") or []
                if isinstance(args, str):
                    args = [args]
                args_text = "\n".join(str(arg) for arg in args if str(arg).strip())
                self.igir_args_edit.setPlainText(args_text)
                self._igir_selected_template = name
                self.igir_status_label.setText(f"Status: Template '{name}' übernommen")
            except Exception as exc:
                self.igir_status_label.setText(f"Status: Template Fehler ({exc})")

        def _apply_igir_profile(self) -> None:
            try:
                name = str(self.igir_profile_combo.currentText() or "").strip()
                if not name or name == "-":
                    self.igir_status_label.setText("Status: Profil wählen")
                    return
                profiles = getattr(self, "_igir_profiles", {}) or {}
                spec = profiles.get(name) if isinstance(profiles, dict) else None
                if not isinstance(spec, dict):
                    self.igir_status_label.setText("Status: Profil ungültig")
                    return
                args = spec.get("execute") or []
                if isinstance(args, str):
                    args = [args]
                args_text = "\n".join(str(arg) for arg in args if str(arg).strip())
                self.igir_args_edit.setPlainText(args_text)
                self._igir_selected_profile = name
                self.igir_status_label.setText(f"Status: Profil '{name}' aktiviert")
            except Exception as exc:
                self.igir_status_label.setText(f"Status: Profil Fehler ({exc})")

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
                    template_name = getattr(self, "_igir_selected_template", None)
                    templates = data.get("templates") or {}
                    if template_name and isinstance(templates, dict):
                        spec = templates.get(template_name)
                        if isinstance(spec, dict):
                            plan_args = spec.get("plan") or []
                            if isinstance(plan_args, str):
                                plan_args = [plan_args]
                            plan_args = [str(arg) for arg in plan_args if str(arg).strip()]
                            if plan_args:
                                data["args_templates"]["plan"] = plan_args
                profile_name = getattr(self, "_igir_selected_profile", None)
                if profile_name:
                    data["active_profile"] = profile_name
                else:
                    data["active_profile"] = ""
                data["copy_first"] = bool(self.igir_copy_first_checkbox.isChecked())
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
            if not self._igir_diff_csv and not self._igir_diff_json:
                QtWidgets.QMessageBox.information(
                    self,
                    "IGIR",
                    "Bitte zuerst einen Plan mit Diff-Report erstellen.",
                )
                return
            if self._igir_diff_csv and not Path(self._igir_diff_csv).exists():
                QtWidgets.QMessageBox.warning(
                    self,
                    "IGIR",
                    "Diff-CSV fehlt. Bitte Plan erneut ausführen.",
                )
                return
            if self._igir_diff_json and not Path(self._igir_diff_json).exists():
                QtWidgets.QMessageBox.warning(
                    self,
                    "IGIR",
                    "Diff-JSON fehlt. Bitte Plan erneut ausführen.",
                )
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
                bool(self.igir_copy_first_checkbox.isChecked()),
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
                self._append_log("IGIR cancel requested by user")
                self.igir_status_label.setText("Status: Abbruch angefordert…")
                self.btn_igir_cancel.setEnabled(False)
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

        def _update_igir_diff_buttons(self) -> None:
            has_csv = bool(self._igir_diff_csv)
            has_json = bool(self._igir_diff_json)
            self.btn_igir_open_diff_csv.setEnabled(has_csv)
            self.btn_igir_open_diff_json.setEnabled(has_json)

        def _on_igir_plan_finished(self, result: object) -> None:
            self.btn_igir_plan.setEnabled(True)
            self.btn_igir_cancel.setEnabled(False)
            message = getattr(result, "message", "ok")
            if getattr(result, "ok", False):
                self._igir_plan_ready = True
                self._igir_diff_csv = getattr(result, "diff_csv", None)
                self._igir_diff_json = getattr(result, "diff_json", None)
                self._update_igir_diff_buttons()
                self.btn_igir_execute.setEnabled(True)
                self.igir_status_label.setText("Status: Plan ok")
                QtWidgets.QMessageBox.information(self, "IGIR", f"Plan erstellt ({message}).")
                self._complete_job("igir_plan")
            elif getattr(result, "cancelled", False):
                self.igir_status_label.setText("Status: Plan abgebrochen")
                self._update_igir_diff_buttons()
                QtWidgets.QMessageBox.information(self, "IGIR", "Plan abgebrochen.")
                self._complete_job("igir_plan")
            else:
                self.igir_status_label.setText(f"Status: Plan fehlgeschlagen ({message})")
                self._update_igir_diff_buttons()
                QtWidgets.QMessageBox.warning(self, "IGIR", f"Plan fehlgeschlagen: {message}")
                self._complete_job("igir_plan")

        def _on_igir_execute_finished(self, result: object) -> None:
            self.btn_igir_plan.setEnabled(True)
            self.btn_igir_execute.setEnabled(True)
            self.btn_igir_cancel.setEnabled(False)
            self._update_igir_diff_buttons()
            message = getattr(result, "message", "ok")
            if getattr(result, "success", False):
                self.igir_status_label.setText("Status: Execute ok")
                QtWidgets.QMessageBox.information(self, "IGIR", f"Execute abgeschlossen ({message}).")
                self._complete_job("igir_execute")
            elif getattr(result, "cancelled", False):
                self.igir_status_label.setText("Status: Execute abgebrochen")
                QtWidgets.QMessageBox.information(self, "IGIR", "Execute abgebrochen.")
                self._complete_job("igir_execute")
            else:
                self.igir_status_label.setText(f"Status: Execute fehlgeschlagen ({message})")
                QtWidgets.QMessageBox.warning(self, "IGIR", f"Execute fehlgeschlagen: {message}")
                self._complete_job("igir_execute")

        def _on_igir_failed(self, message: str) -> None:
            self.btn_igir_plan.setEnabled(True)
            self.btn_igir_execute.setEnabled(self._igir_plan_ready)
            self.btn_igir_cancel.setEnabled(False)
            self._update_igir_diff_buttons()
            self.igir_status_label.setText(f"Status: fehlgeschlagen ({message})")
            QtWidgets.QMessageBox.warning(self, "IGIR", f"IGIR fehlgeschlagen: {message}")
            self._complete_job("igir_plan")
            self._complete_job("igir_execute")

        def _open_igir_diff(self, path: Optional[str]) -> None:
            if not path:
                QtWidgets.QMessageBox.information(self, "IGIR", "Kein Diff vorhanden.")
                return
            try:
                if not Path(path).exists():
                    QtWidgets.QMessageBox.warning(self, "IGIR", f"Diff nicht gefunden: {path}")
                    return
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "IGIR", f"Diff konnte nicht geöffnet werden: {exc}")

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
            if isinstance(result, dict):
                processed = result.get("processed", 0)
                skipped = result.get("skipped", 0)
                inserted = result.get("inserted", 0)
                self.dat_status.setText(
                    f"DAT: Index fertig (processed {processed}, skipped {skipped}, inserted {inserted})"
                )
            else:
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

        def _open_dat_sources_dialog(self) -> None:
            try:
                dialog = DatSourcesDialog(self)
                dialog.exec()
            except Exception as exc:
                logging.getLogger(__name__).exception("Failed to open DAT sources dialog")
                QtWidgets.QMessageBox.warning(
                    self,
                    "DAT Quellen",
                    f"Dialog konnte nicht geöffnet werden:\n{exc}",
                )

        def _resolve_override_path(self) -> Path:
            try:
                cfg = load_config()
            except Exception:
                cfg = {}
            override_cfg = cfg.get("identification_overrides", {}) if isinstance(cfg, dict) else {}
            if isinstance(override_cfg, str):
                override_cfg = {"path": override_cfg}
            raw_path = str(override_cfg.get("path") or "config/identify_overrides.yaml").strip()
            if not raw_path:
                raw_path = "config/identify_overrides.yaml"
            path = Path(raw_path)
            if not path.is_absolute():
                path = (Path(__file__).resolve().parents[3] / path).resolve()
            return path

        def _open_identification_overrides(self) -> None:
            try:
                path = self._resolve_override_path()
                if not path.exists():
                    QtWidgets.QMessageBox.information(
                        self,
                        "Mapping Overrides",
                        f"Override-Datei nicht gefunden:\n{path}",
                    )
                    return
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))
            except Exception as exc:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Mapping Overrides",
                    f"Öffnen fehlgeschlagen:\n{exc}",
                )

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
                    screen = self.screen() or QtWidgets.QApplication.primaryScreen()
                    if screen is not None:
                        available = screen.availableGeometry()
                        if available.isValid():
                            width = min(width, available.width())
                            height = min(height, available.height())
                    min_hint = self.minimumSizeHint()
                    if min_hint.isValid():
                        width = max(width, min_hint.width())
                        height = max(height, min_hint.height())
                    self.resize(width, height)
            except Exception:
                return

        def _load_log_visibility(self) -> None:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    return
                gui_cfg = cfg.get("gui_settings", {}) or {}
                visible = bool(gui_cfg.get("log_visible", False))
                self._set_log_visible(visible, persist=False)
            except Exception:
                return

        def _load_general_settings_from_config(self) -> None:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    return
                gui_cfg = cfg.get("gui_settings", {}) or {}

                self.log_visible_checkbox.setChecked(bool(gui_cfg.get("log_visible", False)))
                self.remember_window_checkbox.setChecked(bool(gui_cfg.get("remember_window_size", True)))
                self.drag_drop_checkbox.setChecked(bool(gui_cfg.get("drag_drop_enabled", True)))

                default_mode = str(gui_cfg.get("default_sort_mode") or "copy")
                default_conflict = str(gui_cfg.get("default_conflict_policy") or "rename")
                if self.default_mode_combo.findText(default_mode) >= 0:
                    self.default_mode_combo.setCurrentText(default_mode)
                if self.default_conflict_combo.findText(default_conflict) >= 0:
                    self.default_conflict_combo.setCurrentText(default_conflict)
                self._apply_default_sort_settings(default_mode, default_conflict)
            except Exception:
                return

        def _update_gui_setting(self, key: str, value: object) -> None:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    cfg = {}
                gui_cfg = cfg.get("gui_settings", {}) or {}
                gui_cfg[key] = value
                cfg["gui_settings"] = gui_cfg
                self._save_config_async(cfg)
            except Exception:
                return

        def _apply_default_sort_settings(self, mode: str, conflict: str) -> None:
            try:
                if self.mode_combo.currentText() != mode:
                    self.mode_combo.setCurrentText(mode)
                if self.conflict_combo.currentText() != conflict:
                    self.conflict_combo.setCurrentText(conflict)
            except Exception:
                return

        def _on_log_visible_changed(self, _value: int) -> None:
            self._set_log_visible(bool(self.log_visible_checkbox.isChecked()))

        def _on_remember_window_changed(self, _value: int) -> None:
            self._update_gui_setting("remember_window_size", bool(self.remember_window_checkbox.isChecked()))

        def _on_drag_drop_changed(self, _value: int) -> None:
            enabled = bool(self.drag_drop_checkbox.isChecked())
            self._update_gui_setting("drag_drop_enabled", enabled)
            self._set_drag_drop_enabled(enabled)

        def _on_default_mode_changed(self, value: str) -> None:
            mode = str(value or "").strip() or "copy"
            self._update_gui_setting("default_sort_mode", mode)
            self._apply_default_sort_settings(mode, self.default_conflict_combo.currentText())

        def _on_default_conflict_changed(self, value: str) -> None:
            conflict = str(value or "").strip() or "rename"
            self._update_gui_setting("default_conflict_policy", conflict)
            self._apply_default_sort_settings(self.default_mode_combo.currentText(), conflict)

        def _set_drag_drop_enabled(self, enabled: bool) -> None:
            widgets = [
                self.source_edit,
                self.dest_edit,
                getattr(self, "dashboard_source_edit", None),
                getattr(self, "dashboard_dest_edit", None),
                getattr(self, "conversion_source_edit", None),
                getattr(self, "conversion_dest_edit", None),
                getattr(self, "igir_source_edit", None),
                getattr(self, "igir_dest_edit", None),
            ]
            for widget in widgets:
                if widget is None:
                    continue
                try:
                    widget.setAcceptDrops(bool(enabled))
                except Exception:
                    pass

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
            self._enforce_all_exclusive(self.lang_filter)
            self._enforce_all_exclusive(self.region_filter)
            # Changing filters invalidates existing plan.
            if self._sort_plan is not None:
                self._sort_plan = None
                self._append_log("Filters changed: sort plan invalidated. Please run Preview Sort again.")

            if self._scan_result is not None:
                # Keep table in sync with current filter selection.
                self._populate_scan_table(self._get_filtered_scan_result())
                self._last_view = "scan"

        def _format_reason(self, item: ScanItem) -> str:
            raw = item.raw or {}
            reason = raw.get("reason") or raw.get("policy") or ""
            if not reason:
                reason = str(item.detection_source or "")
            min_conf = self._get_min_confidence()
            if str(item.detection_source) == "policy-low-confidence":
                reason = f"low-confidence (<{min_conf:.2f})"
            return str(reason or "")

        def _format_normalization_hint(self, input_path: str, platform_id: str) -> str:
            if not input_path:
                return "-"
            try:
                norm = normalize_input(input_path, platform_hint=str(platform_id or ""))
                if norm.issues:
                    return "; ".join(issue.message for issue in norm.issues)
                return "ok"
            except Exception as exc:
                return f"Fehler: {exc}"

        def _show_why_unknown(self) -> None:
            row = self.table.currentRow()
            if row < 0 or row >= len(self._table_items):
                QtWidgets.QMessageBox.information(self, "Why Unknown", "Keine Scan-Zeile ausgewählt.")
                return
            item = self._table_items[row]
            raw = item.raw or {}
            reason = self._format_reason(item) or "-"
            signals = ", ".join(raw.get("signals") or []) if isinstance(raw.get("signals"), list) else "-"
            candidates = ", ".join(raw.get("candidates") or []) if isinstance(raw.get("candidates"), list) else "-"
            source = str(item.detection_source or "-")
            confidence = self._format_confidence(item.detection_confidence)
            exact = "ja" if getattr(item, "is_exact", False) else "nein"
            normalization_hint = self._format_normalization_hint(item.input_path, item.detected_system)
            msg = (
                f"System: {item.detected_system}\n"
                f"Reason: {reason}\n"
                f"Quelle: {source}\n"
                f"Sicherheit: {confidence}\n"
                f"Exact: {exact}\n"
                f"Signale: {signals}\n"
                f"Kandidaten: {candidates}\n"
                f"Normalisierung: {normalization_hint}"
            )
            QtWidgets.QMessageBox.information(self, "Why Unknown", msg)

        def _clear_filters(self) -> None:
            def _set_combo(combo, value: str) -> None:
                idx = combo.findText(value)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                else:
                    combo.setCurrentIndex(0)

            self._select_filter_values(self.lang_filter, ["All"])
            _set_combo(self.ver_filter, "All")
            self._select_filter_values(self.region_filter, ["All"])
            self.ext_filter_edit.clear()
            self.min_size_edit.clear()
            self.max_size_edit.clear()
            self.dedupe_checkbox.setChecked(True)
            self.hide_unknown_checkbox.setChecked(False)
            self._on_filters_changed()

        def _collect_preset_values(self) -> dict:
            return {
                "sort": {
                    "mode": str(self.mode_combo.currentText()),
                    "conflict": str(self.conflict_combo.currentText()),
                    "console_folders": bool(self.chk_console_folders.isChecked()),
                    "region_subfolders": bool(self.chk_region_subfolders.isChecked()),
                    "preserve_structure": bool(self.chk_preserve_structure.isChecked()),
                },
                "filters": {
                    "languages": self._get_selected_filter_values(self.lang_filter),
                    "version": str(self.ver_filter.currentText() or "All"),
                    "regions": self._get_selected_filter_values(self.region_filter),
                    "extension": str(self.ext_filter_edit.text() or ""),
                    "min_size": str(self.min_size_edit.text() or ""),
                    "max_size": str(self.max_size_edit.text() or ""),
                    "dedupe": bool(self.dedupe_checkbox.isChecked()),
                    "hide_unknown": bool(self.hide_unknown_checkbox.isChecked()),
                },
            }

        def _apply_preset_values(self, payload: dict) -> None:
            sort_cfg = payload.get("sort") or {}
            filters_cfg = payload.get("filters") or {}

            if str(sort_cfg.get("mode")) in ("copy", "move"):
                idx = self.mode_combo.findText(str(sort_cfg.get("mode")))
                if idx >= 0:
                    self.mode_combo.setCurrentIndex(idx)
            if str(sort_cfg.get("conflict")) in ("rename", "skip", "overwrite"):
                idx = self.conflict_combo.findText(str(sort_cfg.get("conflict")))
                if idx >= 0:
                    self.conflict_combo.setCurrentIndex(idx)
            self.chk_console_folders.setChecked(bool(sort_cfg.get("console_folders", True)))
            self.chk_region_subfolders.setChecked(bool(sort_cfg.get("region_subfolders", False)))
            self.chk_preserve_structure.setChecked(bool(sort_cfg.get("preserve_structure", False)))

            self._select_filter_values(self.lang_filter, filters_cfg.get("languages") or ["All"])
            ver_value = str(filters_cfg.get("version") or "All")
            ver_idx = self.ver_filter.findText(ver_value)
            self.ver_filter.setCurrentIndex(ver_idx if ver_idx >= 0 else 0)
            self._select_filter_values(self.region_filter, filters_cfg.get("regions") or ["All"])
            self.ext_filter_edit.setText(str(filters_cfg.get("extension") or ""))
            self.min_size_edit.setText(str(filters_cfg.get("min_size") or ""))
            self.max_size_edit.setText(str(filters_cfg.get("max_size") or ""))
            self.dedupe_checkbox.setChecked(bool(filters_cfg.get("dedupe", True)))
            self.hide_unknown_checkbox.setChecked(bool(filters_cfg.get("hide_unknown", False)))
            self._on_filters_changed()

        def _load_presets_from_config(self) -> None:
            self._presets = {}
            try:
                cfg = load_config()
                gui_cfg = cfg.get("gui_settings", {}) if isinstance(cfg, dict) else {}
                presets = gui_cfg.get("presets", []) or []
                for preset in presets:
                    name = str(preset.get("name") or "").strip()
                    if not name:
                        continue
                    self._presets[name] = preset
            except Exception:
                self._presets = {}
            self._refresh_presets_combo()

        def _save_presets_to_config(self) -> None:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    cfg = {}
                gui_cfg = cfg.get("gui_settings", {}) or {}
                gui_cfg["presets"] = list(self._presets.values())
                cfg["gui_settings"] = gui_cfg
                self._save_config_async(cfg)
            except Exception:
                return

        def _refresh_presets_combo(self) -> None:
            self.preset_combo.blockSignals(True)
            self.preset_combo.clear()
            self.preset_combo.addItem("-")
            for name in sorted(self._presets.keys()):
                self.preset_combo.addItem(name)
            self.preset_combo.blockSignals(False)

        def _apply_selected_preset(self) -> None:
            name = str(self.preset_combo.currentText() or "").strip()
            if not name or name == "-":
                QtWidgets.QMessageBox.information(self, "Preset", "Bitte ein Preset wählen.")
                return
            preset = self._presets.get(name)
            if not isinstance(preset, dict):
                return
            self._apply_preset_values(preset)

        def _save_preset(self) -> None:
            name = str(self.preset_name_edit.text() or "").strip()
            if not name:
                QtWidgets.QMessageBox.information(self, "Preset", "Bitte einen Namen eingeben.")
                return
            self._presets[name] = {"name": name, **self._collect_preset_values()}
            self._save_presets_to_config()
            self._refresh_presets_combo()
            self.preset_combo.setCurrentText(name)

        def _delete_selected_preset(self) -> None:
            name = str(self.preset_combo.currentText() or "").strip()
            if not name or name == "-":
                return
            if name in self._presets:
                self._presets.pop(name, None)
                self._save_presets_to_config()
                self._refresh_presets_combo()

        def _get_selected_plan_indices(self) -> list[int]:
            try:
                selection = self.table.selectionModel().selectedRows()
            except Exception:
                selection = []
            indices: list[int] = []
            for idx in selection:
                row = idx.row()
                item = self.table.item(row, 0)
                if item is None:
                    continue
                data = item.data(QtCore.Qt.ItemDataRole.UserRole)
                try:
                    action_index = int(data)
                except Exception:
                    action_index = int(row)
                indices.append(action_index)
            return sorted(set(indices))

        def _start_execute_selected(self) -> None:
            if self._sort_plan is None or self._last_view != "plan":
                QtWidgets.QMessageBox.information(self, "Auswahl ausführen", "Bitte zuerst einen Sortierplan anzeigen.")
                return
            indices = self._get_selected_plan_indices()
            if not indices:
                QtWidgets.QMessageBox.information(self, "Auswahl ausführen", "Bitte Zeilen in der Tabelle auswählen.")
                return
            self._start_operation("execute", only_indices=indices, conversion_mode="skip")

        def _build_library_report(self) -> dict:
            return build_library_report(self._scan_result, self._sort_plan)

        def _format_library_report_text(self, report: dict) -> str:
            lines: list[str] = []
            scan = report.get("scan") or {}
            plan = report.get("plan") or {}
            if scan:
                lines.append("Scan")
                lines.append(f"Quelle: {scan.get('source_path', '-')}")
                lines.append(f"Gesamt: {scan.get('total_items', 0)}")
                lines.append(f"Unknown: {scan.get('unknown_items', 0)}")
                systems = scan.get("systems") or {}
                if systems:
                    top = list(systems.items())[:5]
                    lines.append("Top Systeme: " + ", ".join(f"{k}={v}" for k, v in top))
                regions = scan.get("regions") or {}
                if regions:
                    top = list(regions.items())[:5]
                    lines.append("Top Regionen: " + ", ".join(f"{k}={v}" for k, v in top))
                lines.append("")
            if plan:
                lines.append("Plan")
                lines.append(f"Ziel: {plan.get('dest_path', '-')}")
                lines.append(f"Aktionen gesamt: {plan.get('total_actions', 0)}")
                actions = plan.get("actions") or {}
                if actions:
                    lines.append("Aktionen: " + ", ".join(f"{k}={v}" for k, v in actions.items()))
                statuses = plan.get("statuses") or {}
                if statuses:
                    lines.append("Status: " + ", ".join(f"{k}={v}" for k, v in statuses.items()))
            if not lines:
                return "Kein Report verfügbar. Bitte zuerst scannen oder planen."
            return "\n".join(lines)

        def _show_library_report(self) -> None:
            report = self._build_library_report()
            text = self._format_library_report_text(report)
            QtWidgets.QMessageBox.information(self, "Bibliothek-Report", text)

        def _save_library_report(self) -> None:
            report = self._build_library_report()
            if not report:
                QtWidgets.QMessageBox.information(self, "Bibliothek-Report", "Kein Report verfügbar.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Report speichern",
                "library_report.json",
                "JSON Files (*.json)",
            )
            if not filename:
                return
            try:
                write_json(report, filename)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Bibliothek-Report", f"Speichern fehlgeschlagen:\n{exc}")

        def _get_selected_filter_values(self, widget: object) -> list[str]:
            widget_list = cast(Any, widget)
            selected = [item.text() for item in widget_list.selectedItems()]
            return selected if selected else ["All"]

        def _select_filter_values(self, widget: object, values: Iterable[str]) -> None:
            widget_list = cast(Any, widget)
            widget_list.blockSignals(True)
            widget_list.clearSelection()
            values_set = {str(v) for v in values if str(v)} or {"All"}
            for idx in range(widget_list.count()):
                item = widget_list.item(idx)
                if item.text() in values_set:
                    item.setSelected(True)
            if not widget_list.selectedItems():
                for idx in range(widget_list.count()):
                    item = widget_list.item(idx)
                    if item.text() == "All":
                        item.setSelected(True)
                        break
            widget_list.blockSignals(False)

        def _enforce_all_exclusive(self, widget: object) -> None:
            widget_list = cast(Any, widget)
            selected = [item.text() for item in widget_list.selectedItems()]
            if "All" in selected and len(selected) > 1:
                self._select_filter_values(widget_list, ["All"])

        def _get_filtered_scan_result(self) -> ScanResult:
            if self._scan_result is None:
                raise RuntimeError("No scan result available")

            lang = self._get_selected_filter_values(self.lang_filter)
            ver = str(self.ver_filter.currentText() or "All")
            region = self._get_selected_filter_values(self.region_filter)
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
                self._select_filter_values(self.lang_filter, ["All"])
                self.ver_filter.clear()
                self.ver_filter.addItems(ver_defaults)
                self.region_filter.clear()
                self.region_filter.addItems(region_defaults)
                self._select_filter_values(self.region_filter, ["All"])
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

            current_langs = self._get_selected_filter_values(self.lang_filter)
            current_ver = str(self.ver_filter.currentText() or "All")
            current_regions = self._get_selected_filter_values(self.region_filter)

            self.lang_filter.blockSignals(True)
            self.lang_filter.clear()
            self.lang_filter.addItem("All")
            if has_unknown_lang:
                self.lang_filter.addItem("Unknown")
            for lang in sorted(langs):
                self.lang_filter.addItem(str(lang))
            self.lang_filter.blockSignals(False)
            self._select_filter_values(self.lang_filter, current_langs)

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
            self.region_filter.blockSignals(False)
            self._select_filter_values(self.region_filter, current_regions)

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
            text = (
                f"Processed: {report.processed} | Copied: {report.copied} | Moved: {report.moved} | "
                f"Skipped: {report.skipped} | Errors: {len(report.errors)} | Cancelled: {report.cancelled}"
            )
            item = QtWidgets.QTableWidgetItem(text)
            if report.errors:
                item.setToolTip("\n".join(report.errors))
            self.table.setItem(row, 0, item)
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(report.mode))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem("(Summary)"))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(""))
            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(""))
            self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(""))
            self.table.setItem(row, 6, QtWidgets.QTableWidgetItem(""))
            self.table.setItem(row, 7, QtWidgets.QTableWidgetItem(""))
            self.table.setItem(row, 8, QtWidgets.QTableWidgetItem(report.dest_path))
            self.table.setItem(row, 9, QtWidgets.QTableWidgetItem(""))
            self.table.setItem(row, 10, QtWidgets.QTableWidgetItem(""))

        def _update_results_empty_state(self) -> None:
            try:
                has_rows = self.table.rowCount() > 0
                self.results_empty_label.setVisible(not has_rows)
                self.table.setVisible(has_rows)
            except Exception:
                return

        def _append_log(self, text: str) -> None:
            if not text:
                return
            self._log_buffer.append(str(text))

        def _flush_log(self) -> None:
            if not self._log_buffer:
                return
            lines: List[str] = []
            for entry in self._log_buffer:
                lines.extend(str(entry).splitlines())
            self._log_buffer.clear()
            if lines:
                self._log_history.extend(lines)
                if len(self._log_history) > 2000:
                    self._log_history = self._log_history[-2000:]
            if not self._log_filter_text:
                if lines:
                    self.log_view.appendPlainText("\n".join(lines))
                return
            filtered = [line for line in lines if self._log_filter_text in line.lower()]
            if filtered:
                self.log_view.appendPlainText("\n".join(filtered))

        def _apply_log_filter(self) -> None:
            text = str(self.log_filter_edit.text() or "").strip().lower()
            self._log_filter_text = text
            try:
                self.log_view.clear()
            except Exception:
                return
            if not self._log_history:
                return
            if not text:
                self.log_view.appendPlainText("\n".join(self._log_history))
                return
            filtered = [line for line in self._log_history if text in line.lower()]
            if filtered:
                self.log_view.appendPlainText("\n".join(filtered))

        def _priority_value(self, label: str) -> int:
            value = str(label or "").strip().lower()
            if value == "high":
                return 0
            if value == "low":
                return 2
            return 1

        def _queue_or_run(self, op: str, label: str, func) -> None:
            priority = self._priority_value(self.queue_priority_combo.currentText())
            if self.queue_mode_checkbox.isChecked() or self._job_active is not None:
                self._enqueue_job(op, label, func, priority)
                return
            func()

        def _job_int(self, value: object, default: int = 0) -> int:
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    return int(default)
                try:
                    return int(float(text))
                except Exception:
                    return int(default)
            return int(default)

        def _activate_main_tab(self) -> None:
            try:
                if hasattr(self, "tabs") and hasattr(self, "_tab_index_main"):
                    self.tabs.setCurrentIndex(int(self._tab_index_main))
            except Exception:
                return

        def _enqueue_job(self, op: str, label: str, func, priority: int) -> None:
            self._job_counter += 1
            job = {
                "id": self._job_counter,
                "op": op,
                "label": label,
                "priority": priority,
                "status": "queued",
                "func": func,
            }
            self._job_queue.append(job)
            self._job_queue.sort(
                key=lambda item: (
                    self._job_int(item.get("priority", 1), 1),
                    self._job_int(item.get("id", 0), 0),
                )
            )
            self._refresh_job_queue()
            self._maybe_start_next_job()

        def _maybe_start_next_job(self) -> None:
            if self._job_active is not None:
                return
            if self._job_paused:
                return
            if not self._job_queue:
                return
            job = self._job_queue[0]
            job["status"] = "running"
            self._job_active = job
            self._refresh_job_queue()
            try:
                job_func = job.get("func")
                if callable(job_func):
                    job_func()
            except Exception:
                job["status"] = "error"
                self._job_active = None
                self._refresh_job_queue()

        def _complete_job(self, op: str) -> None:
            if not self._job_active:
                return
            if str(self._job_active.get("op")) != str(op):
                return
            try:
                self._job_queue.remove(self._job_active)
            except Exception:
                pass
            self._job_active = None
            if self._current_op == op:
                self._current_op = None
            self._refresh_job_queue()
            self._maybe_start_next_job()

        def _refresh_job_queue(self) -> None:
            try:
                self.queue_list.clear()
                for job in self._job_queue:
                    priority = self._job_int(job.get("priority", 1), 1)
                    label = str(job.get("label", "job"))
                    status = str(job.get("status", "queued"))
                    pid = self._job_int(job.get("id", 0), 0)
                    prio_text = {0: "High", 1: "Normal", 2: "Low"}.get(priority, "Normal")
                    self.queue_list.addItem(f"#{pid} [{prio_text}] {label} - {status}")
            except Exception:
                return

        def _pause_jobs(self) -> None:
            self._job_paused = True
            self.queue_pause_btn.setEnabled(False)
            self.queue_resume_btn.setEnabled(True)
            self.status_label.setText("Jobs pausiert")

        def _resume_jobs(self) -> None:
            self._job_paused = False
            self.queue_pause_btn.setEnabled(True)
            self.queue_resume_btn.setEnabled(False)
            self._maybe_start_next_job()

        def _clear_job_queue(self) -> None:
            self._job_queue = [job for job in self._job_queue if job is self._job_active]
            self._refresh_job_queue()

        def _toggle_log_visibility(self) -> None:
            self._set_log_visible(not self._log_visible)

        def _on_igir_advanced_toggle(self, state: int) -> None:
            self._set_igir_advanced_visible(state == QtCore.Qt.CheckState.Checked)

        def _set_igir_advanced_visible(self, visible: bool) -> None:
            if hasattr(self, "_igir_cfg_group"):
                self._igir_cfg_group.setVisible(bool(visible))

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
                if hasattr(self, "dashboard_source_edit"):
                    self.dashboard_source_edit.setText(text)
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
                if hasattr(self, "dashboard_dest_edit"):
                    self.dashboard_dest_edit.setText(text)
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
            self._refresh_dashboard()

        def _on_dest_text_changed(self, text: str) -> None:
            if self._syncing_paths:
                return
            self._set_dest_text(text)
            self._refresh_dashboard()

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
            self.btn_export_frontend_es.setEnabled(not running and self._sort_plan is not None)
            self.btn_export_frontend_launchbox.setEnabled(not running and self._sort_plan is not None)
            self.menu_export_audit_csv.setEnabled(not running and self._audit_report is not None)
            self.menu_export_audit_json.setEnabled(not running and self._audit_report is not None)
            self.menu_export_scan_csv.setEnabled(not running and self._scan_result is not None)
            self.menu_export_scan_json.setEnabled(not running and self._scan_result is not None)
            self.menu_export_plan_csv.setEnabled(not running and self._sort_plan is not None)
            self.menu_export_plan_json.setEnabled(not running and self._sort_plan is not None)
            self.menu_export_frontend_es.setEnabled(not running and self._sort_plan is not None)
            self.menu_export_frontend_launchbox.setEnabled(not running and self._sort_plan is not None)
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
            self.rebuild_checkbox.setEnabled(not running)
            self._sync_rebuild_controls(running=running)
            self.btn_clear_filters.setEnabled(not running)
            self.btn_add_dat.setEnabled(not running)
            self.btn_refresh_dat.setEnabled(not running)
            self.btn_cancel_dat.setEnabled(not running and self._dat_index_cancel_token is not None)
            self.btn_manage_dat.setEnabled(not running)
            self.btn_open_overrides.setEnabled(not running)
            self.dat_auto_load_checkbox.setEnabled(not running)
            self.btn_clear_dat_cache.setEnabled(not running)
            if not running:
                self._update_resume_buttons()
            self._is_running = bool(running)
            self._refresh_dashboard()
            self._update_quick_actions()

        def _has_required_paths(self) -> bool:
            source = self.source_edit.text().strip() if self.source_edit is not None else ""
            dest = self.dest_edit.text().strip() if self.dest_edit is not None else ""
            return bool(source and dest)

        def _update_quick_actions(self) -> None:
            ready = self._has_required_paths()
            enabled = ready and not self._is_running
            try:
                self.btn_dash_scan.setEnabled(enabled)
                self.btn_dash_preview.setEnabled(enabled)
                self.btn_dash_execute.setEnabled(enabled)
            except Exception:
                pass
            try:
                if hasattr(self, "dashboard_path_hint"):
                    self.dashboard_path_hint.setVisible(not ready)
            except Exception:
                pass

        def _refresh_dashboard(self) -> None:
            if not hasattr(self, "dashboard_status_label"):
                return
            source = self.source_edit.text().strip() if self.source_edit is not None else ""
            dest = self.dest_edit.text().strip() if self.dest_edit is not None else ""
            status = self.status_label.text() if self.status_label is not None else "-"
            dat_status = self.dat_status.text() if self.dat_status is not None else "-"
            self.dashboard_source_label.setText(source or "-")
            self.dashboard_dest_label.setText(dest or "-")
            self.dashboard_status_label.setText(status or "-")
            self.dashboard_dat_label.setText(dat_status or "-")
            if hasattr(self, "main_source_label"):
                self.main_source_label.setText(source or "-")
            if hasattr(self, "main_dest_label"):
                self.main_dest_label.setText(dest or "-")
            self._update_quick_actions()

        def _sync_rebuild_controls(self, *, running: bool = False) -> None:
            try:
                rebuild_active = bool(self.rebuild_checkbox.isChecked())
            except Exception:
                rebuild_active = False

            if rebuild_active:
                if self.mode_combo.currentText() != "copy":
                    self.mode_combo.setCurrentText("copy")
                if self.conflict_combo.currentText() != "skip":
                    self.conflict_combo.setCurrentText("skip")

            self.mode_combo.setEnabled(not running and not rebuild_active)
            self.conflict_combo.setEnabled(not running and not rebuild_active)

        def _on_rebuild_toggle(self, _state: int) -> None:
            self._sync_rebuild_controls(running=False)

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

            self._current_op = op

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

            self._activate_main_tab()

            self._cancel_token = CancelToken()
            self.progress.setValue(0)
            self.status_label.setText("Starte…")

            if op == "scan":
                self._scan_result = None
                self._sort_plan = None
                self.table.setRowCount(0)
                self._update_results_empty_state()
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
            self._queue_or_run("scan", "Scan", self._start_scan_now)

        def _start_scan_now(self) -> None:
            self._failed_action_indices.clear()
            self._audit_report = None
            self._update_resume_buttons()
            try:
                self._append_log("Scan requested")
            except Exception:
                pass
            self._start_operation("scan")

        def _start_preview(self) -> None:
            self._queue_or_run("plan", "Preview", self._start_preview_now)

        def _start_preview_now(self) -> None:
            self._failed_action_indices.clear()
            self._audit_report = None
            self._update_resume_buttons()
            self._start_operation("plan")

        def _start_execute(self) -> None:
            self._queue_or_run("execute", "Execute", self._start_execute_now)

        def _start_execute_now(self) -> None:
            self._failed_action_indices.clear()
            self._audit_report = None
            self._update_resume_buttons()
            self._start_operation("execute", conversion_mode="skip")

        def _start_convert_only(self) -> None:
            self._queue_or_run("execute", "Convert only", self._start_convert_only_now)

        def _start_convert_only_now(self) -> None:
            self._failed_action_indices.clear()
            self._audit_report = None
            self._update_resume_buttons()
            self._start_operation("execute", conversion_mode="only")

        def _start_audit(self) -> None:
            self._queue_or_run("audit", "Audit", self._start_audit_now)

        def _start_audit_now(self) -> None:
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
            try:
                self.status_label.setText("Abbrechen…")
            except Exception:
                pass
            self._cancel_token.cancel()
            self.btn_cancel.setEnabled(False)

        def _on_phase_changed(self, phase: str, total: int) -> None:
            if phase == "scan":
                self.status_label.setText("Scan läuft…")
                self.progress.setRange(0, 100)
                self.progress.setValue(0)
                if hasattr(self, "dashboard_progress"):
                    self.dashboard_progress.setRange(0, 100)
                    self.dashboard_progress.setValue(0)
            elif phase == "plan":
                self.status_label.setText("Plane…")
                self.progress.setRange(0, max(1, int(total)))
                self.progress.setValue(0)
                if hasattr(self, "dashboard_progress"):
                    self.dashboard_progress.setRange(0, max(1, int(total)))
                    self.dashboard_progress.setValue(0)
            elif phase == "execute":
                self.status_label.setText("Ausführen…")
                self.progress.setRange(0, max(1, int(total)))
                self.progress.setValue(0)
                if hasattr(self, "dashboard_progress"):
                    self.dashboard_progress.setRange(0, max(1, int(total)))
                    self.dashboard_progress.setValue(0)
            elif phase == "audit":
                self.status_label.setText("Prüfe Konvertierungen…")
                self.progress.setRange(0, max(1, int(total)))
                self.progress.setValue(0)
                if hasattr(self, "dashboard_progress"):
                    self.dashboard_progress.setRange(0, max(1, int(total)))
                    self.dashboard_progress.setValue(0)

        def _on_progress(self, current: int, total: int) -> None:
            if total and total > 0:
                self.progress.setRange(0, int(total))
                self.progress.setValue(int(current))
                if hasattr(self, "dashboard_progress"):
                    self.dashboard_progress.setRange(0, int(total))
                    self.dashboard_progress.setValue(int(current))
            else:
                self.progress.setRange(0, 0)
                if hasattr(self, "dashboard_progress"):
                    self.dashboard_progress.setRange(0, 0)

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
            self._table_items = list(scan.items)
            for row, item in enumerate(scan.items):

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
                self.table.setItem(row, 0, status_item)

                self.table.setItem(row, 1, QtWidgets.QTableWidgetItem("scan"))

                path_item = QtWidgets.QTableWidgetItem(str(item.input_path or ""))
                self.table.setItem(row, 2, path_item)

                name_item = QtWidgets.QTableWidgetItem(self._rom_display_name(item.input_path))
                if item.input_path:
                    name_item.setToolTip(str(item.input_path))
                self.table.setItem(row, 3, name_item)

                sys_item = QtWidgets.QTableWidgetItem(item.detected_system)
                self.table.setItem(row, 4, sys_item)
                conf_item = QtWidgets.QTableWidgetItem(self._format_confidence(item.detection_confidence))
                try:
                    source = str(item.detection_source or "-")
                    exact = "ja" if getattr(item, "is_exact", False) else "nein"
                    conf_item.setToolTip(f"Quelle: {source}\nExact: {exact}")
                except Exception:
                    pass
                self.table.setItem(row, 5, conf_item)
                self.table.setItem(row, 6, QtWidgets.QTableWidgetItem(self._format_signals(item)))
                self.table.setItem(row, 7, QtWidgets.QTableWidgetItem(self._format_candidates(item)))
                self.table.setItem(row, 8, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(
                    row,
                    9,
                    QtWidgets.QTableWidgetItem(
                        self._format_normalization_hint(item.input_path, item.detected_system)
                    ),
                )
                self.table.setItem(row, 10, QtWidgets.QTableWidgetItem(self._format_reason(item)))

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

            self._update_results_empty_state()

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
            self._table_items = []
            for row, act in enumerate(plan.actions):
                status_item = QtWidgets.QTableWidgetItem(act.error or act.status)
                status_item.setData(QtCore.Qt.ItemDataRole.UserRole, row)
                self.table.setItem(row, 0, status_item)
                self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(act.action))

                path_item = QtWidgets.QTableWidgetItem(str(act.input_path or ""))
                self.table.setItem(row, 2, path_item)

                name_item = QtWidgets.QTableWidgetItem(self._rom_display_name(act.input_path))
                if act.input_path:
                    name_item.setToolTip(str(act.input_path))
                self.table.setItem(row, 3, name_item)

                self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(act.detected_system))
                self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(row, 6, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(row, 7, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(row, 8, QtWidgets.QTableWidgetItem(act.planned_target_path or ""))
                self.table.setItem(
                    row,
                    9,
                    QtWidgets.QTableWidgetItem(
                        self._format_normalization_hint(act.input_path, act.detected_system)
                    ),
                )
                self.table.setItem(row, 10, QtWidgets.QTableWidgetItem(""))

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

            self._update_results_empty_state()

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
            self._table_items = []
            for row, item in enumerate(report.items):
                suggestion = item.current_extension
                if item.recommended_extension and item.recommended_extension != item.current_extension:
                    suggestion = f"{item.current_extension} -> {item.recommended_extension}".strip()

                action = "convert" if item.status == "should_convert" else "keep"
                status = item.status
                if item.reason:
                    status = f"{status}: {item.reason}"

                self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(status))
                self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(action))

                path_item = QtWidgets.QTableWidgetItem(str(item.input_path or ""))
                self.table.setItem(row, 2, path_item)

                name_item = QtWidgets.QTableWidgetItem(self._rom_display_name(item.input_path))
                if item.input_path:
                    name_item.setToolTip(str(item.input_path))
                self.table.setItem(row, 3, name_item)

                self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(item.detected_system))
                self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(row, 6, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(row, 7, QtWidgets.QTableWidgetItem(""))
                self.table.setItem(row, 8, QtWidgets.QTableWidgetItem(suggestion))
                self.table.setItem(row, 9, QtWidgets.QTableWidgetItem("-"))
                self.table.setItem(row, 10, QtWidgets.QTableWidgetItem(item.reason or ""))

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

            self._update_results_empty_state()

        def _on_action_status(self, row_index: int, status: str) -> None:
            try:
                row = int(row_index)
                if row < 0 or row >= self.table.rowCount():
                    return
                existing = self.table.item(row, 0)
                if existing is None:
                    existing = QtWidgets.QTableWidgetItem(str(status))
                    self.table.setItem(row, 0, existing)
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

        def _export_frontend_es(self) -> None:
            plan = self._sort_plan
            if plan is None:
                QtWidgets.QMessageBox.information(self, "Kein Plan", "Bitte zuerst Vorschau ausführen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save EmulationStation gamelist",
                "gamelist.xml",
                "XML Files (*.xml)",
            )
            if not filename:
                return
            self._run_export_task("Frontend EmulationStation", lambda: write_emulationstation_gamelist(plan, filename))

        def _export_frontend_launchbox(self) -> None:
            plan = self._sort_plan
            if plan is None:
                QtWidgets.QMessageBox.information(self, "Kein Plan", "Bitte zuerst Vorschau ausführen.")
                return
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save LaunchBox CSV",
                "launchbox_export.csv",
                "CSV Files (*.csv)",
            )
            if not filename:
                return
            self._run_export_task("Frontend LaunchBox", lambda: write_launchbox_csv(plan, filename))

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
                self._complete_job("scan")
                return

            if op == "plan":
                if not isinstance(payload, SortPlan):
                    raise RuntimeError("Plan worker returned unexpected payload")
                self._sort_plan = payload
                self.status_label.setText("Plan bereit")
                self._populate_plan_table(payload)
                self._last_view = "plan"
                QtWidgets.QMessageBox.information(self, "Vorschau bereit", f"Geplante Aktionen: {len(payload.actions)}")
                self._complete_job("plan")
                return

            if op == "execute":
                if not isinstance(payload, SortReport):
                    raise RuntimeError("Execute worker returned unexpected payload")
                self.status_label.setText("Abgebrochen" if payload.cancelled else "Fertig")
                self._append_summary_row(payload)
                self._update_results_empty_state()
                QtWidgets.QMessageBox.information(
                    self,
                    "Fertig",
                    f"Fertig. Kopiert: {payload.copied}, Verschoben: {payload.moved}\nFehler: {len(payload.errors)}\n\nSiehe Log für Details.",
                )
                self._complete_job("execute")
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
                self._complete_job("audit")
                self._set_running(False)
                return

        def _on_failed(self, message: str, tb: str) -> None:
            self._append_log(message)
            self._append_log(tb)
            self._cleanup_thread()
            self._set_running(False)
            self.status_label.setText("Error")
            self._set_log_visible(True, persist=False)
            QtWidgets.QMessageBox.critical(self, "Arbeitsfehler", f"{message}\n\n{tb}")
            if self._current_op:
                self._complete_job(self._current_op)
                self._current_op = None

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()

    exec_fn = getattr(app, "exec", None) or getattr(app, "exec_")
    return int(exec_fn())
