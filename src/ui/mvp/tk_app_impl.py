"""ROM Sorter Pro - MVP Tk GUI (fallback)."""

from __future__ import annotations

import importlib
import logging
import os
import threading
import traceback
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, cast

from ...version import load_version
from .tk_ui_builders import (
    build_actions_ui,
    build_header_ui,
    build_log_ui,
    build_paths_ui,
    build_results_table_ui,
    build_status_ui,
)
from .tk_log_utils import TkLogBuffer

logger = logging.getLogger(__name__)


class _Tooltip:
    def __init__(self, tk, ttk, widget, text: str) -> None:
        self._tk = tk
        self._ttk = ttk
        self._widget = widget
        self._text = text
        self._tip_window = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None) -> None:
        if self._tip_window or not self._text:
            return
        try:
            x = self._widget.winfo_rootx() + 20
            y = self._widget.winfo_rooty() + 20
            tip = self._tk.Toplevel(self._widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{x}+{y}")
            label = self._ttk.Label(tip, text=self._text, padding=6)
            label.pack()
            self._tip_window = tip
        except Exception:
            self._tip_window = None

    def _hide(self, _event=None) -> None:
        if self._tip_window is None:
            return
        try:
            self._tip_window.destroy()
        except Exception:
            pass
        self._tip_window = None


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
    simpledialog = importlib.import_module("tkinter.simpledialog")

    from ...app.api import (
        CancelToken,
        ConflictPolicy,
        ConversionMode,
        ScanItem,
        ScanResult,
        SortPlan,
        SortReport,
        SortMode,
        add_identification_overrides_bulk,
        diff_sort_plans,
        filter_scan_items,
        get_symlink_warnings,
        plan_sort,
        run_scan,
        execute_sort,
        normalize_input,
        infer_languages_and_version_from_name,
        infer_region_from_name,
    )
    from ...app.plan_stats import compute_plan_stats
    from .model_utils import format_system_badge
    from ...ui.state_machine import UIStateMachine, UIState
    from ...ui.backend_worker import BackendWorkerHandle
    from ...config.io import load_config, save_config

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
            only_indices: Optional[List[int]],
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
            self.only_indices = only_indices
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
                        only_indices=self.only_indices,
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
            self._last_plan: Optional[SortPlan] = None
            self._plan_stats: Dict[str, int] = {"total_actions": 0, "total_bytes": 0}
            self._plan_history: List[SortPlan] = []
            self._plan_history_index: int = -1
            self._ui_fsm = UIStateMachine()

            self._log_filter_text = ""
            self._log_level = "ALL"
            self._syncing_paths = False

            self._table_items: List[ScanItem] = []

            self._build_ui()
            self._bind_shortcuts()
            self.root.after(200, self._maybe_show_first_run_wizard)

        def _bind_shortcuts(self) -> None:
            try:
                self.root.bind("<Control-s>", lambda _evt: self._start_scan())
                self.root.bind("<Control-p>", lambda _evt: self._start_preview())
                self.root.bind("<Control-e>", lambda _evt: self._start_execute())
                self.root.bind("<F1>", lambda _evt: self._show_shortcuts_dialog())
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
            self.btn_source = paths_ui.btn_source
            self.btn_dest = paths_ui.btn_dest
            self.recent_source_combo = paths_ui.recent_source_combo
            self.recent_dest_combo = paths_ui.recent_dest_combo
            self.recent_source_combo.bind("<<ComboboxSelected>>", lambda _evt: self._on_recent_source_selected())
            self.recent_dest_combo.bind("<<ComboboxSelected>>", lambda _evt: self._on_recent_dest_selected())
            self.source_var.trace_add("write", lambda *_: self._on_source_changed())
            self.dest_var.trace_add("write", lambda *_: self._on_dest_changed())

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
            self.btn_rule_tester = actions_ui.btn_rule_tester
            self.btn_rule_tester.configure(command=self._open_rule_tester)
            self.copy_first_var = actions_ui.copy_first_var
            self.btn_rename_builder = actions_ui.btn_rename_builder
            self.rename_template_var = actions_ui.rename_template_var
            self.rename_template_entry = actions_ui.rename_template_entry
            self.btn_rename_builder.configure(command=self._open_rename_pattern_builder)
            self.copy_first_var.trace_add("write", lambda *_: self._on_copy_first_changed())
            self.rename_template_var.trace_add("write", lambda *_: self._on_rename_template_changed())

            status_ui = build_status_ui(ttk, tk, main)
            self.status_var = status_ui.status_var
            self.summary_var = status_ui.summary_var
            self.progress = status_ui.progress

            table_ui = build_results_table_ui(ttk, tk, main)
            self.tree = table_ui.tree
            self.btn_structure_preview = table_ui.btn_structure
            self.btn_structure_preview.configure(command=self._show_structure_preview)
            self.btn_plan_undo = table_ui.btn_plan_undo
            self.btn_plan_redo = table_ui.btn_plan_redo
            self.btn_plan_undo.configure(command=self._undo_plan)
            self.btn_plan_redo.configure(command=self._redo_plan)
            self.btn_execute_selected = table_ui.btn_execute_selected
            self.btn_execute_selected.configure(command=self._start_execute_selected)
            self.btn_bulk_override = table_ui.btn_bulk_override
            self.btn_bulk_override.configure(command=self._start_bulk_override_selected)
            self.btn_action_override = table_ui.btn_action_override
            self.btn_action_override.configure(command=self._start_action_override_selected)
            self._sync_plan_history_buttons()

            log_ui = build_log_ui(ttk, tk, main)
            self.log_text = log_ui.log_text
            self.log_filter_var = log_ui.log_filter_var
            self.log_filter_entry = log_ui.log_filter_entry
            self.log_filter_clear_btn = log_ui.log_filter_clear_btn
            self.log_level_combo = log_ui.log_level_combo
            self.log_filter_clear_btn.configure(command=lambda: self.log_filter_var.set(""))
            self.log_filter_var.trace_add("write", lambda *_: self._apply_log_filter())
            self.log_level_combo.bind("<<ComboboxSelected>>", lambda _evt: self._apply_log_filter())
            self.log_frame = log_ui.frame
            self._log_helper = TkLogBuffer(
                self.root,
                self.log_text,
                lambda: self._log_filter_text,
                lambda: self._log_level,
                max_lines=5000,
            )

            options_frame = ttk.LabelFrame(main, text="Anzeige", padding=8)
            options_frame.pack(fill=tk.X, pady=(0, 8))
            self.compact_var = tk.BooleanVar(value=False)
            self.pro_var = tk.BooleanVar(value=False)
            compact_cb = ttk.Checkbutton(
                options_frame,
                text="Compact Mode",
                variable=self.compact_var,
                command=self._on_compact_mode_changed,
            )
            pro_cb = ttk.Checkbutton(
                options_frame,
                text="Pro Mode",
                variable=self.pro_var,
                command=self._on_pro_mode_changed,
            )
            btn_shortcuts = ttk.Button(options_frame, text="Shortcuts anzeigen", command=self._show_shortcuts_dialog)
            compact_cb.pack(side=tk.LEFT)
            pro_cb.pack(side=tk.LEFT, padx=(8, 0))
            btn_shortcuts.pack(side=tk.LEFT, padx=(8, 0))

            self._apply_tooltips(tk, ttk)
            self._load_general_settings_from_config()
            self._load_sorting_settings_from_config()
            self._refresh_recent_paths_dropdowns()

        def _choose_source(self) -> None:
            directory = filedialog.askdirectory()
            if directory:
                self.source_var.set(directory)

        def _choose_dest(self) -> None:
            directory = filedialog.askdirectory()
            if directory:
                self.dest_var.set(directory)

        def _load_recent_paths(self) -> List[Dict[str, str]]:
            try:
                cfg = load_config()
                gui_cfg = cfg.get("gui_settings", {}) if isinstance(cfg, dict) else {}
                raw = gui_cfg.get("recent_paths", []) or []
            except Exception:
                raw = []
            recent: List[Dict[str, str]] = []
            for item in raw:
                if not isinstance(item, dict):
                    continue
                source = str(item.get("source") or "").strip()
                dest = str(item.get("dest") or "").strip()
                if source and dest:
                    recent.append({"source": source, "dest": dest})
            return recent[:5]

        def _save_recent_paths(self, recent: List[Dict[str, str]]) -> None:
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    cfg = {}
                gui_cfg = cfg.get("gui_settings", {}) or {}
                gui_cfg["recent_paths"] = recent
                cfg["gui_settings"] = gui_cfg
                save_config(cfg)
            except Exception:
                return

        def _refresh_recent_paths_dropdowns(self) -> None:
            recent = self._load_recent_paths()
            values_source = ["-"] + [item["source"] for item in recent]
            values_dest = ["-"] + [item["dest"] for item in recent]
            self.recent_source_combo.configure(values=tuple(values_source))
            self.recent_dest_combo.configure(values=tuple(values_dest))
            self.recent_source_combo.set("-")
            self.recent_dest_combo.set("-")

        def _track_recent_paths(self) -> None:
            source = str(self.source_var.get() or "").strip()
            dest = str(self.dest_var.get() or "").strip()
            if not source or not dest:
                return
            recent = self._load_recent_paths()
            recent = [r for r in recent if not (r.get("source") == source and r.get("dest") == dest)]
            recent.insert(0, {"source": source, "dest": dest})
            recent = recent[:5]
            self._save_recent_paths(recent)
            self._refresh_recent_paths_dropdowns()

        def _on_recent_source_selected(self) -> None:
            value = str(self.recent_source_combo.get() or "").strip()
            if value and value != "-":
                self.source_var.set(value)

        def _on_recent_dest_selected(self) -> None:
            value = str(self.recent_dest_combo.get() or "").strip()
            if value and value != "-":
                self.dest_var.set(value)

        def _on_source_changed(self) -> None:
            if self._syncing_paths:
                return
            self._syncing_paths = True
            try:
                self._track_recent_paths()
            finally:
                self._syncing_paths = False

        def _on_dest_changed(self) -> None:
            if self._syncing_paths:
                return
            self._syncing_paths = True
            try:
                self._track_recent_paths()
            finally:
                self._syncing_paths = False

        def _apply_log_filter(self) -> None:
            text = str(self.log_filter_var.get() or "").strip().lower()
            level = str(self.log_level_combo.get() or "").strip().lower()
            level_map = {
                "alle": "ALL",
                "info": "INFO",
                "warnung": "WARNING",
                "fehler": "ERROR",
                "debug": "DEBUG",
            }
            self._log_filter_text = text
            self._log_level = level_map.get(level, "ALL")
            self._log_helper.apply_filter(text)

        def _apply_tooltips(self, tk, ttk) -> None:
            _Tooltip(tk, ttk, self.btn_source, "Quellordner auswählen")
            _Tooltip(tk, ttk, self.btn_dest, "Zielordner auswählen")
            _Tooltip(tk, ttk, self.btn_scan, "Scan starten")
            _Tooltip(tk, ttk, self.btn_preview, "Vorschau (Dry-run)")
            _Tooltip(tk, ttk, self.btn_execute, "Sortierung ausführen")
            _Tooltip(tk, ttk, self.btn_cancel, "Vorgang abbrechen")
            _Tooltip(tk, ttk, self.recent_source_combo, "Zuletzt verwendete Quellen")
            _Tooltip(tk, ttk, self.recent_dest_combo, "Zuletzt verwendete Ziele")
            _Tooltip(tk, ttk, self.log_filter_entry, "Log nach Text filtern")
            _Tooltip(tk, ttk, self.log_level_combo, "Log nach Severity filtern")
            _Tooltip(tk, ttk, self.rename_template_entry, "Rename-Template für Zielnamen")
            _Tooltip(tk, ttk, self.btn_rename_builder, "Rename-Pattern-Builder öffnen")
            _Tooltip(tk, ttk, self.btn_plan_undo, "Plan zurücksetzen (Undo)")
            _Tooltip(tk, ttk, self.btn_plan_redo, "Plan wiederholen (Redo)")
            _Tooltip(tk, ttk, self.btn_action_override, "Aktion für Auswahl überschreiben")

        def _load_sorting_settings_from_config(self) -> None:
            try:
                cfg = load_config()
                features_cfg = cfg.get("features", {}) if isinstance(cfg, dict) else {}
                sorting_cfg = features_cfg.get("sorting", {}) if isinstance(features_cfg, dict) else {}
                self.copy_first_var.set(bool(sorting_cfg.get("copy_first_staging", False)))
                template = str(sorting_cfg.get("rename_template") or "")
                self.rename_template_var.set(template)
            except Exception:
                return

        def _load_general_settings_from_config(self) -> None:
            try:
                cfg = load_config()
                gui_cfg = cfg.get("gui_settings", {}) if isinstance(cfg, dict) else {}
                self.compact_var.set(bool(gui_cfg.get("compact_mode", False)))
                self.pro_var.set(bool(gui_cfg.get("pro_mode", False)))
                self._apply_compact_mode(self.compact_var.get())
                self._apply_pro_mode(self.pro_var.get())
            except Exception:
                return

        def _apply_compact_mode(self, enabled: bool) -> None:
            try:
                compact = bool(enabled)
                if compact:
                    self.log_frame.pack_forget()
                else:
                    self.log_frame.pack(fill=tk.BOTH, expand=False)
            except Exception:
                return

        def _apply_pro_mode(self, enabled: bool) -> None:
            try:
                pro = bool(enabled)
                if not pro:
                    self.btn_rule_tester.pack_forget()
                    self.btn_execute_selected.pack_forget()
                    self.btn_bulk_override.pack_forget()
                    self.btn_action_override.pack_forget()
                else:
                    if not self.btn_execute_selected.winfo_manager():
                        self.btn_execute_selected.pack(side=tk.LEFT, padx=(6, 0))
                    if not self.btn_bulk_override.winfo_manager():
                        self.btn_bulk_override.pack(side=tk.LEFT, padx=(6, 0))
                    if not self.btn_rule_tester.winfo_manager():
                        self.btn_rule_tester.pack(side=tk.LEFT, padx=4)
                    if not self.btn_action_override.winfo_manager():
                        self.btn_action_override.pack(side=tk.LEFT, padx=(6, 0))
            except Exception:
                return

        def _on_compact_mode_changed(self) -> None:
            enabled = bool(self.compact_var.get())
            self._apply_compact_mode(enabled)
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    cfg = {}
                gui_cfg = cfg.get("gui_settings", {}) or {}
                gui_cfg["compact_mode"] = enabled
                cfg["gui_settings"] = gui_cfg
                save_config(cfg)
            except Exception:
                return

        def _on_pro_mode_changed(self) -> None:
            enabled = bool(self.pro_var.get())
            self._apply_pro_mode(enabled)
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    cfg = {}
                gui_cfg = cfg.get("gui_settings", {}) or {}
                gui_cfg["pro_mode"] = enabled
                cfg["gui_settings"] = gui_cfg
                save_config(cfg)
            except Exception:
                return

        def _on_copy_first_changed(self) -> None:
            enabled = bool(self.copy_first_var.get())
            try:
                cfg = load_config()
                if not isinstance(cfg, dict):
                    cfg = {}
                features_cfg = cfg.get("features", {}) or {}
                sorting_cfg = features_cfg.get("sorting", {}) or {}
                sorting_cfg["copy_first_staging"] = enabled
                features_cfg["sorting"] = sorting_cfg
                cfg["features"] = features_cfg
                save_config(cfg)
            except Exception:
                return

        def _on_rename_template_changed(self) -> None:
            try:
                template = str(self.rename_template_var.get() or "").strip()
                cfg = load_config()
                if not isinstance(cfg, dict):
                    cfg = {}
                features_cfg = cfg.get("features", {}) or {}
                sorting_cfg = features_cfg.get("sorting", {}) or {}
                sorting_cfg["rename_template"] = template
                features_cfg["sorting"] = sorting_cfg
                cfg["features"] = features_cfg
                save_config(cfg)
            except Exception:
                return

        def _show_shortcuts_dialog(self) -> None:
            dialog = tk.Toplevel(self.root)
            dialog.title("Tastenkürzel")
            dialog.geometry("360x220")
            ttk.Label(dialog, text="Shortcuts", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 6))
            lines = [
                "Ctrl+S – Scan starten",
                "Ctrl+P – Preview Sort",
                "Ctrl+E – Execute Sort",
            ]
            ttk.Label(dialog, text="\n".join(lines)).pack(anchor="w", padx=10)
            ttk.Button(dialog, text="Schließen", command=dialog.destroy).pack(pady=10)

        def _open_rename_pattern_builder(self) -> None:
            dialog = tk.Toplevel(self.root)
            dialog.title("Rename-Pattern-Builder")
            dialog.geometry("520x200")
            ttk.Label(
                dialog,
                text="Tokens: {system} {name} {ext} {ext_dot} {region} {version} {languages}",
                wraplength=480,
            ).pack(anchor="w", padx=10, pady=(10, 6))
            template_var = tk.StringVar(value=str(self.rename_template_var.get() or ""))
            entry = ttk.Entry(dialog, textvariable=template_var, width=60)
            entry.pack(anchor="w", padx=10)
            preview_label = ttk.Label(dialog, text="Vorschau: -", wraplength=480)
            preview_label.pack(anchor="w", padx=10, pady=(6, 10))

            def _get_sample() -> tuple[str, object, str]:
                try:
                    selection = list(self.tree.selection())
                    if selection:
                        row = int(self.tree.index(selection[0]))
                        if 0 <= row < len(self._table_items):
                            item = self._table_items[row]
                            return str(item.input_path or ""), item, str(item.detected_system or "Unknown")
                except Exception:
                    pass
                from types import SimpleNamespace

                sample_item = SimpleNamespace(
                    region="USA",
                    version="v1.0",
                    languages=("EN",),
                    raw={},
                    detected_system="Sample",
                )
                return "C:/ROMs/Sample Game (USA).zip", sample_item, "Sample"

            def _update_preview() -> None:
                src_path, item, system = _get_sample()
                try:
                    from ...app.sorting_helpers import _apply_rename_template

                    rendered = _apply_rename_template(str(template_var.get() or ""), item, Path(src_path), system)
                    preview_label.configure(text=f"Vorschau: {rendered}")
                except Exception as exc:
                    preview_label.configure(text=f"Vorschau: Fehler ({exc})")

            def _apply_template() -> None:
                self.rename_template_var.set(str(template_var.get() or "").strip())
                dialog.destroy()

            entry.bind("<KeyRelease>", lambda _evt: _update_preview())
            _update_preview()

            btn_row = ttk.Frame(dialog)
            btn_row.pack(anchor="e", padx=10, pady=(0, 10))
            ttk.Button(btn_row, text="Abbrechen", command=dialog.destroy).pack(side="right")
            ttk.Button(btn_row, text="Übernehmen", command=_apply_template).pack(side="right", padx=(0, 8))

        def _append_log(self, text: str) -> None:
            if not text:
                return
            self._log_helper.append(str(text))

        def _open_rule_tester(self) -> None:
            try:
                value = simpledialog.askstring("Detection-Rule-Tester", "Dateiname oder Pfad:", parent=self.root)
            except Exception:
                value = None
            if not value:
                return
            try:
                from ..core.platform_heuristics import evaluate_platform_candidates
                result = evaluate_platform_candidates(str(value))
            except Exception as exc:
                messagebox.showwarning("Detection-Rule-Tester", f"Fehler: {exc}")
                return
            candidates = ", ".join(result.get("candidates") or []) or "-"
            signals = ", ".join(result.get("signals") or []) or "-"
            details = result.get("candidate_details") or []
            detail_lines = []
            for entry in details[:5]:
                if not isinstance(entry, dict):
                    continue
                platform_id = str(entry.get("platform_id") or "-")
                score = float(entry.get("score") or 0.0)
                detail_lines.append(f"{platform_id} (score {score:.2f})")
            detail_text = "\n".join(detail_lines) if detail_lines else "-"
            msg = f"Kandidaten: {candidates}\nSignale: {signals}\nDetails:\n{detail_text}"
            messagebox.showinfo("Detection-Rule-Tester", msg)

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
            if hasattr(self, "btn_structure_preview"):
                self.btn_structure_preview.state(["disabled" if running or self._sort_plan is None else "!disabled"])
            if hasattr(self, "btn_execute_selected"):
                self.btn_execute_selected.state(["disabled" if running or self._sort_plan is None else "!disabled"])
            if hasattr(self, "btn_bulk_override"):
                self.btn_bulk_override.state(["disabled" if running or self._sort_plan is None else "!disabled"])

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

        def _start_operation(self, op: str, *, only_indices: Optional[List[int]] = None) -> None:
            values = self._validate_paths(require_dest=op in ("plan", "execute"))
            if values is None:
                return

            warnings = get_symlink_warnings(
                values.get("source"),
                values.get("dest") if op in ("plan", "execute") else None,
            )
            if warnings:
                message = "Symlink-Warnung:\n" + "\n".join(warnings) + "\n\nTrotzdem fortfahren?"
                if not messagebox.askyesno("Symlink-Warnung", message):
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
                self._last_plan = None
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
                    try:
                        self.summary_var.set(f"{len(payload.items)} gefunden")
                    except Exception:
                        self.summary_var.set("-")
                    if payload.cancelled:
                        messagebox.showinfo("Abgebrochen", "Scan abgebrochen.")
                    else:
                        messagebox.showinfo("Scan abgeschlossen", f"ROMs gefunden: {len(payload.items)}")
                    return

                if op == "plan":
                    if not isinstance(payload, SortPlan):
                        raise RuntimeError("Plan worker returned unexpected payload")
                    prev_plan = self._last_plan
                    self._set_active_plan(payload, record_history=True)
                    self.status_var.set("Plan bereit")
                    if self._maybe_prompt_conflicts(payload):
                        return
                    if prev_plan is not None:
                        try:
                            diff = diff_sort_plans(prev_plan, payload)
                            self._append_log(
                                f"Plan diff: +{diff['added']} -{diff['removed']} ~{diff['changed']}"
                            )
                            messagebox.showinfo(
                                "Plan-Diff",
                                "Plan-Änderungen erkannt:\n"
                                f"Neu: {diff['added']} | Entfernt: {diff['removed']} | Geändert: {diff['changed']}",
                            )
                        except Exception:
                            pass
                    self._last_plan = payload
                    messagebox.showinfo("Vorschau bereit", f"Geplante Aktionen: {len(payload.actions)}")
                    return

                if op == "execute":
                    if not isinstance(payload, SortReport):
                        raise RuntimeError("Execute worker returned unexpected payload")
                    self.status_var.set("Abgebrochen" if payload.cancelled else "Fertig")
                    try:
                        self.summary_var.set(
                            f"Processed {payload.processed} | Errors {len(payload.errors)}"
                        )
                    except Exception:
                        self.summary_var.set("-")
                    messagebox.showinfo(
                        "Fertig",
                        f"Fertig. Kopiert: {payload.copied}, Verschoben: {payload.moved}\nFehler: {len(payload.errors)}",
                    )
                    if payload.mode == "move" and not payload.cancelled:
                        self.status_var.set("Rollback verfügbar (CLI)")
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
                only_indices=only_indices,
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
            if not self._confirm_execute_if_warnings():
                return
            self._start_operation("execute")

        def _get_selected_plan_indices(self) -> List[int]:
            indices: List[int] = []
            try:
                for item in self.tree.selection():
                    indices.append(int(self.tree.index(item)))
            except Exception:
                return []
            return sorted(set(indices))

        def _start_execute_selected(self) -> None:
            if self._sort_plan is None:
                messagebox.showinfo("Auswahl ausführen", "Bitte zuerst einen Sortierplan anzeigen.")
                return
            indices = self._get_selected_plan_indices()
            if not indices:
                messagebox.showinfo("Auswahl ausführen", "Bitte Zeilen in der Tabelle auswählen.")
                return
            if not self._confirm_execute_if_warnings():
                return
            self._start_operation("execute", only_indices=indices)

        def _start_bulk_override_selected(self) -> None:
            if self._sort_plan is None:
                messagebox.showinfo("Mehrfach-Override", "Bitte zuerst einen Sortierplan anzeigen.")
                return
            indices = self._get_selected_plan_indices()
            if not indices:
                messagebox.showinfo("Mehrfach-Override", "Bitte Zeilen in der Tabelle auswählen.")
                return
            input_paths: List[str] = []
            for idx in indices:
                try:
                    action = self._sort_plan.actions[idx]
                except Exception:
                    continue
                input_path = str(getattr(action, "input_path", "") or "")
                if input_path:
                    input_paths.append(input_path)
            if not input_paths:
                messagebox.showinfo("Mehrfach-Override", "Keine gültigen Pfade gefunden.")
                return
            platform_id = simpledialog.askstring(
                "Mehrfach-Override",
                "Plattform-ID für alle ausgewählten ROMs:",
                parent=self.root,
            )
            if platform_id is None:
                return
            platform_id = str(platform_id or "").strip()
            if not platform_id:
                messagebox.showinfo("Mehrfach-Override", "Plattform-ID darf nicht leer sein.")
                return
            cfg = load_config()
            ok, message, path = add_identification_overrides_bulk(
                input_paths,
                platform_id,
                config=cfg,
                name="manual-ui-bulk",
                confidence=1.0,
            )
            if not ok:
                messagebox.showerror("Mehrfach-Override", f"Speichern fehlgeschlagen:\n{message}")
                return
            self._append_log(
                f"Bulk-Override gespeichert: {platform_id} für {len(input_paths)} ROMs"
            )
            messagebox.showinfo(
                "Mehrfach-Override",
                f"Override gespeichert für {len(input_paths)} ROMs.\n\nDatei: {path}",
            )

        def _start_action_override_selected(self) -> None:
            if self._sort_plan is None:
                messagebox.showinfo("Aktion überschreiben", "Bitte zuerst einen Sortierplan anzeigen.")
                return
            indices = self._get_selected_plan_indices()
            if not indices:
                messagebox.showinfo("Aktion überschreiben", "Bitte Zeilen in der Tabelle auswählen.")
                return
            action_value = simpledialog.askstring(
                "Aktion überschreiben",
                "Aktion für Auswahl (copy|move|skip):",
                parent=self.root,
            )
            if action_value is None:
                return
            normalized = str(action_value or "").strip().lower()
            if normalized not in ("copy", "move", "skip"):
                messagebox.showinfo("Aktion überschreiben", "Ungültige Aktion.")
                return
            self._override_action_for_rows(indices, normalized)

        def _override_action_for_rows(self, rows: List[int], action_value: str) -> None:
            if self._sort_plan is None:
                return
            normalized = str(action_value).strip().lower()
            if normalized not in ("copy", "move", "skip", "convert"):
                return
            new_actions = []
            for idx, action in enumerate(self._sort_plan.actions):
                if idx in rows:
                    new_actions.append(replace(action, action=normalized))
                else:
                    new_actions.append(action)
            new_plan = SortPlan(
                dest_path=self._sort_plan.dest_path,
                mode=self._sort_plan.mode,
                on_conflict=self._sort_plan.on_conflict,
                actions=new_actions,
            )
            self._set_active_plan(new_plan, record_history=True)

        def _confirm_execute_if_warnings(self) -> bool:
            total_actions = int(self._plan_stats.get("total_actions", 0) or 0)
            total_bytes = int(self._plan_stats.get("total_bytes", 0) or 0)
            over_count = total_actions >= 1000
            over_size = total_bytes >= 10 * 1024 * 1024 * 1024
            if not over_count and not over_size:
                return True
            details = []
            if over_count:
                details.append(f">=1000 Dateien ({total_actions})")
            if over_size:
                details.append(f">=10 GB ({round(total_bytes / (1024 ** 3), 2)} GB)")
            reason = ", ".join(details) if details else "Review erforderlich"
            return messagebox.askyesno(
                "Review Gate",
                "Review erforderlich: " + reason + "\n\nTrotzdem ausführen?",
            )

        def _maybe_prompt_conflicts(self, plan: SortPlan) -> bool:
            try:
                if str(plan.on_conflict) != "skip":
                    return False
            except Exception:
                return False
            conflicts = [
                act
                for act in plan.actions
                if (act.error or "").strip().lower() == "target exists (skip)"
            ]
            if not conflicts:
                return False
            choice = messagebox.askyesnocancel(
                "Konflikte erkannt",
                f"{len(conflicts)} Ziele existieren bereits.\n\n"
                "Ja = Umbenennen, Nein = Überschreiben, Abbrechen = Überspringen",
            )
            if choice is None:
                return False
            if choice:
                self.conflict_var.set("rename")
            else:
                self.conflict_var.set("overwrite")
            self.root.after(0, lambda: self._start_operation("plan"))
            return True

        def _show_structure_preview(self) -> None:
            if self._sort_plan is None:
                messagebox.showinfo("Zielstruktur", "Kein Sortierplan vorhanden.")
                return
            plan = self._sort_plan
            win = tk.Toplevel(self.root)
            win.title("Zielstruktur (Preview)")
            win.geometry("640x480")

            tree = ttk.Treeview(win)
            tree.pack(fill=tk.BOTH, expand=True)
            tree.heading("#0", text="Zielstruktur")

            root_label = str(plan.dest_path or "Ziel")
            root = tree.insert("", "end", text=root_label, open=True)
            node_cache: Dict[tuple[str, str], str] = {("", root_label): root}

            for act in plan.actions:
                target = str(act.planned_target_path or "")
                if not target:
                    continue
                try:
                    rel = Path(target).resolve().relative_to(Path(plan.dest_path).resolve())
                    parts = rel.parts
                except Exception:
                    parts = Path(target).parts
                parent = root
                for idx, part in enumerate(parts):
                    if not part:
                        continue
                    if idx == len(parts) - 1:
                        tree.insert(parent, "end", text=part)
                        continue
                    cache_key = (parent, part)
                    existing = node_cache.get(cache_key)
                    if existing is None:
                        existing = tree.insert(parent, "end", text=part, open=False)
                        node_cache[cache_key] = existing
                    parent = existing

        def _maybe_show_first_run_wizard(self) -> None:
            try:
                cfg = load_config()
            except Exception:
                cfg = {}
            gui_cfg = cfg.get("gui_settings", {}) if isinstance(cfg, dict) else {}
            if gui_cfg.get("first_run_complete"):
                return

            win = tk.Toplevel(self.root)
            win.title("Erststart-Assistent")
            win.geometry("520x320")
            win.transient(self.root)
            win.grab_set()

            header = ttk.Label(win, text="Willkommen bei ROM-Sorter-Pro", font=("Segoe UI", 12, "bold"))
            header.pack(anchor="w", padx=12, pady=(12, 6))
            ttk.Label(win, text="Wähle Quelle und Ziel für deinen ersten Scan.").pack(anchor="w", padx=12)

            form = ttk.Frame(win)
            form.pack(fill="x", padx=12, pady=12)
            ttk.Label(form, text="Quelle:").grid(row=0, column=0, sticky="w")
            src_var = tk.StringVar(value=self.source_var.get())
            src_entry = ttk.Entry(form, textvariable=src_var)
            src_entry.grid(row=0, column=1, sticky="ew", padx=6)
            ttk.Button(form, text="Wählen…", command=lambda: src_var.set(filedialog.askdirectory() or src_var.get())).grid(row=0, column=2)

            ttk.Label(form, text="Ziel:").grid(row=1, column=0, sticky="w", pady=(6, 0))
            dst_var = tk.StringVar(value=self.dest_var.get())
            dst_entry = ttk.Entry(form, textvariable=dst_var)
            dst_entry.grid(row=1, column=1, sticky="ew", padx=6, pady=(6, 0))
            ttk.Button(form, text="Wählen…", command=lambda: dst_var.set(filedialog.askdirectory() or dst_var.get())).grid(row=1, column=2, pady=(6, 0))
            form.columnconfigure(1, weight=1)

            footer = ttk.Frame(win)
            footer.pack(fill="x", padx=12, pady=(0, 12))
            ttk.Button(footer, text="Überspringen", command=win.destroy).pack(side="right")

            def finish() -> None:
                self.source_var.set(src_var.get())
                self.dest_var.set(dst_var.get())
                if isinstance(cfg, dict):
                    gui_cfg = cfg.get("gui_settings", {}) or {}
                    gui_cfg["first_run_complete"] = True
                    cfg["gui_settings"] = gui_cfg
                    try:
                        save_config(cfg)
                    except Exception:
                        pass
                win.destroy()

            ttk.Button(footer, text="Fertig", command=finish).pack(side="right", padx=(0, 8))

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
            self._table_items = list(scan.items)
            for item in scan.items:
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        str(item.input_path or ""),
                        format_system_badge(str(item.detected_system or "")),
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
                        format_system_badge(str(act.detected_system or "")),
                        str(act.planned_target_path or ""),
                        str(act.action),
                        str(act.status or ""),
                    ),
                )
            try:
                self._plan_stats = compute_plan_stats(plan)
            except Exception:
                self._plan_stats = {"total_actions": 0, "total_bytes": 0}

        def _set_active_plan(self, plan: SortPlan, record_history: bool = True) -> None:
            self._sort_plan = plan
            self._populate_plan_table(plan)
            self._update_plan_summary(plan)
            if record_history:
                if self._plan_history_index < len(self._plan_history) - 1:
                    self._plan_history = self._plan_history[: self._plan_history_index + 1]
                self._plan_history.append(plan)
                self._plan_history_index = len(self._plan_history) - 1
            self._sync_plan_history_buttons()

        def _sync_plan_history_buttons(self) -> None:
            try:
                if self._plan_history_index <= 0:
                    self.btn_plan_undo.state(["disabled"])
                else:
                    self.btn_plan_undo.state(["!disabled"])
                if self._plan_history_index >= len(self._plan_history) - 1:
                    self.btn_plan_redo.state(["disabled"])
                else:
                    self.btn_plan_redo.state(["!disabled"])
            except Exception:
                return

        def _undo_plan(self) -> None:
            if self._plan_history_index <= 0:
                return
            self._plan_history_index -= 1
            plan = self._plan_history[self._plan_history_index]
            self._set_active_plan(plan, record_history=False)

        def _redo_plan(self) -> None:
            if self._plan_history_index >= len(self._plan_history) - 1:
                return
            self._plan_history_index += 1
            plan = self._plan_history[self._plan_history_index]
            self._set_active_plan(plan, record_history=False)

        def _update_plan_summary(self, plan: SortPlan) -> None:
            try:
                planned = len(plan.actions)
                eta = self._format_eta_from_plan()
                self.summary_var.set(f"Aktionen: {planned} | ETA {eta}")
            except Exception:
                self.summary_var.set("-")

        def _format_eta_from_plan(self) -> str:
            try:
                total_bytes = int(self._plan_stats.get("total_bytes", 0))
            except Exception:
                total_bytes = 0
            if total_bytes <= 0:
                return "-"
            try:
                cfg = load_config()
                sorting_cfg = (cfg.get("features", {}) or {}).get("sorting", {}) if isinstance(cfg, dict) else {}
                throughput = float(sorting_cfg.get("estimated_throughput_mb_s", 120.0) or 120.0)
            except Exception:
                throughput = 120.0
            if throughput <= 0:
                throughput = 120.0
            seconds = total_bytes / (throughput * 1024 * 1024)
            if seconds < 1:
                return "<1s"
            minutes = int(seconds // 60)
            rem = int(seconds % 60)
            if minutes >= 60:
                hours = int(minutes // 60)
                minutes = int(minutes % 60)
                return f"{hours}h {minutes}m"
            return f"{minutes}m {rem}s"

    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
    return 0
