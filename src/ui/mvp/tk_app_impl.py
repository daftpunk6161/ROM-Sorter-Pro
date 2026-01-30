"""ROM Sorter Pro - MVP Tk GUI (fallback)."""

from __future__ import annotations

import importlib
import logging
import os
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, cast

from ...version import load_version
from .tk_ui_builders import (
    build_actions_ui,
    build_header_ui,
    build_log_ui,
    build_paths_ui,
    build_results_table_ui,
    build_status_ui,
)

logger = logging.getLogger(__name__)


def handle_worker_failure(
    message: str,
    traceback_text: str,
    log_cb,
    dialog_cb,
) -> None:
    """Log worker failures and route them to an error dialog callback."""
    if log_cb is not None:
        if message:
            log_cb(message)
        if traceback_text:
            log_cb(traceback_text)
    if dialog_cb is not None:
        dialog_cb(message, traceback_text)


def run() -> int:
    tk = importlib.import_module("tkinter")
    ttk = importlib.import_module("tkinter.ttk")
    messagebox = importlib.import_module("tkinter.messagebox")
    filedialog = importlib.import_module("tkinter.filedialog")

    from ...app.api import (
        CancelToken,
        ConflictPolicy,
        ConversionMode,
        ScanItem,
        ScanResult,
        SortPlan,
        SortReport,
        SortMode,
        filter_scan_items,
        plan_sort,
        run_scan,
        execute_sort,
        normalize_input,
        infer_languages_and_version_from_name,
        infer_region_from_name,
    )
    from ...ui.state_machine import UIStateMachine, UIState
    from ...ui.backend_worker import BackendWorkerHandle
    from ...config.io import load_config

    class OperationWorker:
        def __init__(
            self,
            op: str,
            source: str,
            dest: str,
            mode: str,
            on_conflict: str,
            scan_result: Optional[ScanResult],
            sort_plan: Optional[SortPlan],
            cancel_token: CancelToken,
            on_progress: Callable[[int, int], None],
            on_log: Callable[[str], None],
            on_finished: Callable[[object], None],
            on_failed: Callable[[str, str], None],
        ):
            self.op = op
            self.source = source
            self.dest = dest
            self.mode = mode
            self.on_conflict = on_conflict
            self.scan_result = scan_result
            self.sort_plan = sort_plan
            self.cancel_token = cancel_token
            self.on_progress = on_progress
            self.on_log = on_log
            self.on_finished = on_finished
            self.on_failed = on_failed

        def run(self) -> None:
            try:
                if self.op == "scan":
                    self.on_log(f"Scan started: source={self.source}")
                    scan = run_scan(
                        self.source,
                        config=None,
                        progress_cb=lambda c, t: self.on_progress(int(c), int(t)),
                        log_cb=lambda msg: self.on_log(str(msg)),
                        cancel_token=self.cancel_token,
                    )
                    self.on_log(f"Scan finished: items={len(scan.items)} cancelled={scan.cancelled}")
                    self.on_finished(scan)
                    return

                if self.op == "plan":
                    if self.scan_result is None:
                        raise RuntimeError("No scan result available")
                    self.on_log(
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
                    self.on_log(f"Plan finished: actions={len(plan.actions)}")
                    self.on_finished(plan)
                    return

                if self.op == "execute":
                    if self.sort_plan is None:
                        raise RuntimeError("No sort plan available")
                    total_actions = len(self.sort_plan.actions)
                    self.on_log(f"Execute started: total={total_actions}")
                    report = execute_sort(
                        self.sort_plan,
                        progress_cb=lambda c, t: self.on_progress(int(c), int(t)),
                        log_cb=lambda msg: self.on_log(str(msg)),
                        cancel_token=self.cancel_token,
                        dry_run=False,
                        conversion_mode=cast(ConversionMode, "skip"),
                    )
                    self.on_log(
                        f"Execute finished: processed={report.processed} copied={report.copied} moved={report.moved} errors={len(report.errors)} cancelled={report.cancelled}"
                    )
                    self.on_finished(report)
                    return

                raise RuntimeError(f"Unknown operation: {self.op}")

            except Exception as exc:
                self.on_failed(str(exc), traceback.format_exc())

    class MainWindow:
        def __init__(self, root: Any):
            self.root = root
            self.root.title(f"ROM Sorter Pro v{load_version()} - Tk MVP GUI")
            self.root.geometry("1000x700")

            self._cancel_token = CancelToken()
            self._worker_thread: Optional[threading.Thread] = None
            self._worker_handle: Optional[BackendWorkerHandle] = None
            self._scan_result: Optional[ScanResult] = None
            self._sort_plan: Optional[SortPlan] = None
            self._ui_fsm = UIStateMachine()

            self._table_items: List[ScanItem] = []

            self._build_ui()
            self._bind_shortcuts()

        def _bind_shortcuts(self) -> None:
            try:
                self.root.bind("<Control-s>", lambda _evt: self._start_scan())
                self.root.bind("<Control-p>", lambda _evt: self._start_preview())
                self.root.bind("<Control-e>", lambda _evt: self._start_execute())
            except Exception:
                return

        def _build_ui(self) -> None:
            main = ttk.Frame(self.root, padding=8)
            main.pack(fill=tk.BOTH, expand=True)

            build_header_ui(ttk, main, load_version())

            paths_ui = build_paths_ui(ttk, tk, main, self._choose_source, self._choose_dest)
            self.source_var = paths_ui.source_var
            self.source_entry = paths_ui.source_entry
            self.dest_var = paths_ui.dest_var
            self.dest_entry = paths_ui.dest_entry

            actions_ui = build_actions_ui(
                ttk,
                tk,
                main,
                self._start_scan,
                self._start_preview,
                self._start_execute,
                self._cancel,
            )
            self.mode_var = actions_ui.mode_var
            self.conflict_var = actions_ui.conflict_var
            self.btn_scan = actions_ui.btn_scan
            self.btn_preview = actions_ui.btn_preview
            self.btn_execute = actions_ui.btn_execute
            self.btn_cancel = actions_ui.btn_cancel

            status_ui = build_status_ui(ttk, tk, main)
            self.status_var = status_ui.status_var
            self.progress = status_ui.progress

            table_ui = build_results_table_ui(ttk, tk, main)
            self.tree = table_ui.tree

            log_ui = build_log_ui(ttk, tk, main)
            self.log_text = log_ui.log_text

        def _choose_source(self) -> None:
            directory = filedialog.askdirectory()
            if directory:
                self.source_var.set(directory)

        def _choose_dest(self) -> None:
            directory = filedialog.askdirectory()
            if directory:
                self.dest_var.set(directory)

        def _append_log(self, text: str) -> None:
            if not text:
                return
            self.log_text.insert(tk.END, f"{text}\n")
            self.log_text.see(tk.END)

        def _set_running(self, running: bool) -> None:
            if running:
                self._ui_fsm.transition(UIState.EXECUTING)
            else:
                self._ui_fsm.transition(UIState.IDLE)
            state = "disabled" if running else "normal"
            for btn in (self.btn_scan, self.btn_preview, self.btn_execute):
                btn.state([state])
            if running:
                self.btn_cancel.state(["!disabled"])
            else:
                self.btn_cancel.state(["disabled"])

        def _validate_paths(self, require_dest: bool = True) -> Optional[dict]:
            source = self.source_var.get().strip()
            dest = self.dest_var.get().strip()
            if not source:
                messagebox.showwarning("Quelle fehlt", "Bitte einen Quellordner wählen.")
                return None
            if require_dest and not dest:
                messagebox.showwarning("Ziel fehlt", "Bitte einen Zielordner wählen.")
                return None
            return {"source": source, "dest": dest}

        def _start_operation(self, op: str) -> None:
            values = self._validate_paths(require_dest=op in ("plan", "execute"))
            if values is None:
                return

            if op in ("plan", "execute") and self._scan_result is None:
                messagebox.showinfo("Keine Scan-Ergebnisse", "Bitte zuerst scannen.")
                return
            if op == "execute" and self._sort_plan is None:
                messagebox.showinfo("Kein Sortierplan", "Bitte zuerst Vorschau ausführen.")
                return

            self._cancel_token = CancelToken()
            self.progress["value"] = 0
            self.status_var.set("Starte…")

            if op == "scan":
                self._scan_result = None
                self._sort_plan = None
                self._clear_table()

            def on_progress(current: int, total: int) -> None:
                if total > 0:
                    self.progress["maximum"] = total
                    self.progress["value"] = current
                else:
                    self.progress.config(mode="indeterminate")
                    self.progress.start()

            def on_finished(payload: object) -> None:
                self.progress.stop()
                self.progress.config(mode="determinate")
                self._set_running(False)

                if op == "scan":
                    if not isinstance(payload, ScanResult):
                        raise RuntimeError("Scan worker returned unexpected payload")
                    self._scan_result = payload
                    self._populate_scan_table(payload)
                    self.status_var.set("Abgebrochen" if payload.cancelled else "Scan abgeschlossen")
                    if payload.cancelled:
                        messagebox.showinfo("Abgebrochen", "Scan abgebrochen.")
                    else:
                        messagebox.showinfo("Scan abgeschlossen", f"ROMs gefunden: {len(payload.items)}")
                    return

                if op == "plan":
                    if not isinstance(payload, SortPlan):
                        raise RuntimeError("Plan worker returned unexpected payload")
                    self._sort_plan = payload
                    self._populate_plan_table(payload)
                    self.status_var.set("Plan bereit")
                    messagebox.showinfo("Vorschau bereit", f"Geplante Aktionen: {len(payload.actions)}")
                    return

                if op == "execute":
                    if not isinstance(payload, SortReport):
                        raise RuntimeError("Execute worker returned unexpected payload")
                    self.status_var.set("Abgebrochen" if payload.cancelled else "Fertig")
                    messagebox.showinfo(
                        "Fertig",
                        f"Fertig. Kopiert: {payload.copied}, Verschoben: {payload.moved}\nFehler: {len(payload.errors)}",
                    )
                    return

            def on_failed(message: str, tb: str) -> None:
                self.progress.stop()
                self.progress.config(mode="determinate")
                handle_worker_failure(
                    message,
                    tb,
                    self._append_log,
                    lambda msg, trace: messagebox.showerror("Arbeitsfehler", f"{msg}\n\n{trace}"),
                )
                self._set_running(False)
                self.status_var.set("Fehler")

            worker = OperationWorker(
                op=op,
                source=values["source"],
                dest=values["dest"],
                mode=str(self.mode_var.get()),
                on_conflict=str(self.conflict_var.get()),
                scan_result=self._scan_result,
                sort_plan=self._sort_plan,
                cancel_token=self._cancel_token,
                on_progress=on_progress,
                on_log=self._append_log,
                on_finished=lambda payload: self.root.after(0, lambda: on_finished(payload)),
                on_failed=lambda msg, tb: self.root.after(0, lambda: on_failed(msg, tb)),
            )

            thread = threading.Thread(target=worker.run, daemon=True)
            self._worker_thread = thread
            self._worker_handle = BackendWorkerHandle(thread, self._cancel_token)
            self._set_running(True)
            thread.start()

        def _start_scan(self) -> None:
            self._start_operation("scan")

        def _start_preview(self) -> None:
            self._start_operation("plan")

        def _start_execute(self) -> None:
            self._start_operation("execute")

        def _cancel(self) -> None:
            self._append_log("Cancel requested")
            self.status_var.set("Abbrechen…")
            self._cancel_token.cancel()
            if self._worker_handle is not None:
                self._worker_handle.cancel()
            self.btn_cancel.state(["disabled"])

        def _clear_table(self) -> None:
            for row in self.tree.get_children():
                self.tree.delete(row)

        def _populate_scan_table(self, scan: ScanResult) -> None:
            self._clear_table()
            for item in scan.items:
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        str(item.input_path or ""),
                        str(item.detected_system or ""),
                        "",
                        "scan",
                        str(item.detection_source or ""),
                    ),
                )

        def _populate_plan_table(self, plan: SortPlan) -> None:
            self._clear_table()
            for act in plan.actions:
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        str(act.input_path or ""),
                        str(act.detected_system or ""),
                        str(act.planned_target_path or ""),
                        str(act.action),
                        str(act.status or ""),
                    ),
                )

    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
    return 0
