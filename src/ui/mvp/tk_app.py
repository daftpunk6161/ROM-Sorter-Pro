"""ROM Sorter Pro - MVP Tk GUI (fallback).

Used only when Qt is not available.

MVP requirements implemented here:
- Source folder picker
- Destination folder picker
- Buttons: Scan, Preview Sort (Dry-run), Execute Sort, Cancel
- Progress bar + live log (ring buffer)
- Result list (table): InputPath, DetectedConsole/Type, Confidence, Signals, Candidates, PlannedTargetPath, Action, Status/Error
- Worker thread + queue-based UI updates + cancel token
"""

from __future__ import annotations

import os
import logging
import time
import threading
import traceback
import re
import subprocess
import sys
import json
import csv
from pathlib import Path
from queue import Queue, Empty
from typing import Any, Callable, Dict, Optional, Tuple

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

from ...app.api import (
    CancelToken,
    ConversionAuditReport,
    ScanItem,
    ScanResult,
    SortPlan,
    SortReport,
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
from ...config.io import load_config, save_config
from ...core.dat_index_sqlite import DatIndexSqlite
from ...dnd_support import (
    DropFrame,
    get_dnd_mode,
    init_drag_drop,
    is_dnd_available,
    patch_tkinter_root,
)
from ...database.database_gui import DatabaseManagerDialog
from ...ui.theme_manager import ThemeManager
from ...utils.external_tools import probe_igir, igir_plan, igir_execute
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


class TkMVPApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ROM Sorter Pro - MVP GUI")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)

        self._dnd_available = self._is_drag_drop_enabled() and is_dnd_available()
        if self._dnd_available and get_dnd_mode() == "tkdnd":
            patch_tkinter_root(self.root)

        self._queue: "Queue[Tuple[str, Any]]" = Queue()
        self._cancel_token = CancelToken()
        self._worker_thread: Optional[threading.Thread] = None

        self._scan_result: Optional[ScanResult] = None
        self._sort_plan: Optional[SortPlan] = None
        self._audit_report: Optional[ConversionAuditReport] = None
        self._plan_row_iids: list[str] = []
        self._row_meta: dict[str, dict[str, object]] = {}
        self._failed_action_indices: set[int] = set()
        self._resume_path = str((Path(__file__).resolve().parents[3] / "cache" / "last_sort_resume.json").resolve())

        self.source_var = tk.StringVar()
        self.dest_var = tk.StringVar()
        self.igir_exe_var = tk.StringVar()
        self.igir_args_var = tk.StringVar()
        self.igir_status_var = tk.StringVar(value="IGIR nicht geprüft.")
        self.mode_var = tk.StringVar(value="copy")
        self.conflict_var = tk.StringVar(value="rename")
        self.lang_filter_var = tk.StringVar(value="All")
        self.ver_filter_var = tk.StringVar(value="All")
        self.region_filter_var = tk.StringVar(value="All")
        self.extension_filter_var = tk.StringVar()
        self.min_size_var = tk.StringVar()
        self.max_size_var = tk.StringVar()
        self.dedupe_var = tk.BooleanVar(value=True)
        self.hide_unknown_var = tk.BooleanVar(value=False)
        self.console_folders_var = tk.BooleanVar(value=True)
        self.region_subfolders_var = tk.BooleanVar(value=False)
        self.preserve_structure_var = tk.BooleanVar(value=False)

        self._theme_manager = ThemeManager()
        self.theme_var = tk.StringVar(value=self._theme_manager.get_current_theme_name())
        self._load_theme_from_config()
        self._dat_index: Optional[DatIndexSqlite] = None
        self._dat_poll_job: Optional[str] = None
        self._igir_cancel_token = CancelToken()
        self._igir_thread: Optional[threading.Thread] = None
        self._igir_plan_ready = False
        self._dat_index_thread: Optional[threading.Thread] = None
        self._dat_index_cancel_token: Optional[CancelToken] = None

        self._build_ui()
        self._log_buffer: list[str] = []
        self._log_flush_scheduled = False
        self._install_log_handler()
        self._apply_theme(self._theme_manager.get_theme())
        self._load_window_size()
        self._load_log_visibility()
        self._load_sort_settings_from_config()
        self._load_dat_settings_from_config()
        self._load_igir_settings_from_config()
        self._refresh_filter_options()
        self._set_running(False)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(50, self._poll_queue)

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True)

        main_tab = ttk.Frame(notebook, padding=10)
        conversions_tab = ttk.Frame(notebook, padding=10)
        igir_tab = ttk.Frame(notebook, padding=10)
        settings_tab = ttk.Frame(notebook, padding=10)
        notebook.add(main_tab, text="Haupt")
        notebook.add(conversions_tab, text="Konvertierungen")
        notebook.add(igir_tab, text="IGIR")
        notebook.add(settings_tab, text="Einstellungen")

        outer = main_tab

        grid = ttk.Frame(outer)
        grid.pack(fill=tk.X)

        ttk.Label(grid, text="Quelle:").grid(row=0, column=0, sticky="w")
        if self._dnd_available:
            self.source_frame = DropFrame(grid, drop_callback=self._on_drop_source)
            self.source_entry = ttk.Entry(self.source_frame, textvariable=self.source_var)
            self.source_entry.pack(fill=tk.X, expand=True)
            self.source_frame.grid(row=0, column=1, sticky="ew", padx=6)
        else:
            self.source_entry = ttk.Entry(grid, textvariable=self.source_var)
            self.source_entry.grid(row=0, column=1, sticky="ew", padx=6)
        self.btn_source = ttk.Button(grid, text="Quelle wählen…", command=self._choose_source)
        self.btn_source.grid(row=0, column=2)

        ttk.Label(grid, text="Ziel:").grid(row=1, column=0, sticky="w")
        if self._dnd_available:
            self.dest_frame = DropFrame(grid, drop_callback=self._on_drop_dest)
            self.dest_entry = ttk.Entry(self.dest_frame, textvariable=self.dest_var)
            self.dest_entry.pack(fill=tk.X, expand=True)
            self.dest_frame.grid(row=1, column=1, sticky="ew", padx=6)
        else:
            self.dest_entry = ttk.Entry(grid, textvariable=self.dest_var)
            self.dest_entry.grid(row=1, column=1, sticky="ew", padx=6)
        self.btn_dest = ttk.Button(grid, text="Ziel wählen…", command=self._choose_dest)
        self.btn_dest.grid(row=1, column=2)
        self.btn_open_dest = ttk.Button(grid, text="Ziel öffnen", command=self._open_dest)
        self.btn_open_dest.grid(row=1, column=3, padx=(6, 0))

        ttk.Label(grid, text="Aktion:").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.mode_combo = ttk.Combobox(grid, textvariable=self.mode_var, values=("copy", "move"), state="readonly")
        self.mode_combo.grid(row=3, column=1, sticky="w", pady=(6, 0))

        ttk.Label(grid, text="Bei Konflikt:").grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.conflict_combo = ttk.Combobox(
            grid,
            textvariable=self.conflict_var,
            values=("rename", "skip", "overwrite"),
            state="readonly",
        )
        self.conflict_combo.grid(row=4, column=1, sticky="w", pady=(6, 0))

        ttk.Label(grid, text="Sprachfilter:").grid(row=5, column=0, sticky="w", pady=(6, 0))
        self.lang_filter_combo = ttk.Combobox(
            grid,
            textvariable=self.lang_filter_var,
            values=("All",),
            state="readonly",
        )
        self.lang_filter_combo.grid(row=5, column=1, sticky="w", pady=(6, 0))

        ttk.Label(grid, text="Versionsfilter:").grid(row=6, column=0, sticky="w", pady=(6, 0))
        self.ver_filter_combo = ttk.Combobox(
            grid,
            textvariable=self.ver_filter_var,
            values=("All",),
            state="readonly",
        )
        self.ver_filter_combo.grid(row=6, column=1, sticky="w", pady=(6, 0))

        ttk.Label(grid, text="Regionsfilter:").grid(row=7, column=0, sticky="w", pady=(6, 0))
        self.region_filter_combo = ttk.Combobox(
            grid,
            textvariable=self.region_filter_var,
            values=("All",),
            state="readonly",
        )
        self.region_filter_combo.grid(row=7, column=1, sticky="w", pady=(6, 0))

        ttk.Label(grid, text="Erweiterungsfilter:").grid(row=8, column=0, sticky="w", pady=(6, 0))
        self.extension_entry = ttk.Entry(grid, textvariable=self.extension_filter_var)
        self.extension_entry.grid(row=8, column=1, sticky="ew", pady=(6, 0))
        ttk.Label(grid, text="z.B. iso, chd").grid(row=8, column=2, sticky="w", pady=(6, 0))

        ttk.Label(grid, text="Min (MB):").grid(row=9, column=0, sticky="w", pady=(6, 0))
        size_vcmd = (self.root.register(self._validate_size_entry), "%P")
        self.min_size_entry = ttk.Entry(
            grid,
            textvariable=self.min_size_var,
            width=12,
            validate="key",
            validatecommand=size_vcmd,
        )
        self.min_size_entry.grid(row=9, column=1, sticky="w", pady=(6, 0))

        ttk.Label(grid, text="Max (MB):").grid(row=10, column=0, sticky="w", pady=(6, 0))
        self.max_size_entry = ttk.Entry(
            grid,
            textvariable=self.max_size_var,
            width=12,
            validate="key",
            validatecommand=size_vcmd,
        )
        self.max_size_entry.grid(row=10, column=1, sticky="w", pady=(6, 0))

        self.dedupe_check = ttk.Checkbutton(
            grid,
            text="Duplikate vermeiden (Europa → USA)",
            variable=self.dedupe_var,
            command=self._on_filters_changed,
        )
        self.dedupe_check.grid(row=11, column=1, sticky="w", pady=(6, 0))

        self.hide_unknown_check = ttk.Checkbutton(
            grid,
            text="Unbekannt / Niedrige Sicherheit ausblenden",
            variable=self.hide_unknown_var,
            command=self._on_filters_changed,
        )
        self.hide_unknown_check.grid(row=11, column=2, sticky="w", pady=(6, 0))

        self.btn_clear_filters = ttk.Button(grid, text="Filter zurücksetzen", command=self._clear_filters)
        self.btn_clear_filters.grid(row=12, column=1, sticky="w", pady=(6, 0))

        self.lang_filter_combo.bind("<<ComboboxSelected>>", self._on_filters_changed)
        self.ver_filter_combo.bind("<<ComboboxSelected>>", self._on_filters_changed)
        self.region_filter_combo.bind("<<ComboboxSelected>>", self._on_filters_changed)
        self.extension_entry.bind("<KeyRelease>", self._on_filters_changed)
        self.min_size_entry.bind("<KeyRelease>", self._on_filters_changed)
        self.max_size_entry.bind("<KeyRelease>", self._on_filters_changed)

        grid.columnconfigure(1, weight=1)

        sort_frame = ttk.LabelFrame(outer, text="Sortieroptionen")
        sort_frame.pack(fill=tk.X, pady=(8, 0))

        self.console_folders_check = ttk.Checkbutton(
            sort_frame,
            text="Konsolenordner erstellen",
            variable=self.console_folders_var,
            command=self._on_sort_settings_changed,
        )
        self.console_folders_check.pack(side=tk.LEFT, padx=(6, 10))

        self.region_subfolders_check = ttk.Checkbutton(
            sort_frame,
            text="Regionsordner erstellen",
            variable=self.region_subfolders_var,
            command=self._on_sort_settings_changed,
        )
        self.region_subfolders_check.pack(side=tk.LEFT, padx=(0, 10))

        self.preserve_structure_check = ttk.Checkbutton(
            sort_frame,
            text="Quell-Unterordner beibehalten",
            variable=self.preserve_structure_var,
            command=self._on_sort_settings_changed,
        )
        self.preserve_structure_check.pack(side=tk.LEFT)

        btn_row = ttk.Frame(outer)
        ttk.Label(btn_row, text="Sortierung").pack(anchor="w", pady=(0, 4))
        btn_row.pack(fill=tk.X, pady=(10, 0))

        btn_row_top = ttk.Frame(btn_row)
        btn_row_top.pack(fill=tk.X)
        btn_row_bottom = ttk.Frame(btn_row)
        btn_row_bottom.pack(fill=tk.X, pady=(6, 0))

        self.btn_scan = ttk.Button(btn_row_top, text="Scannen", command=self._start_scan)
        self.btn_preview = ttk.Button(btn_row_top, text="Vorschau Sortierung (Dry-run)", command=self._start_preview)
        self.btn_execute = ttk.Button(btn_row_top, text="Sortieren ausführen (ohne Konvertierung)", command=self._start_execute)
        self.btn_resume = ttk.Button(btn_row_bottom, text="Fortsetzen", command=self._start_resume)
        self.btn_retry_failed = ttk.Button(btn_row_bottom, text="Fehlgeschlagene erneut", command=self._start_retry_failed)
        self.btn_cancel = ttk.Button(btn_row_bottom, text="Abbrechen", command=self._cancel)
        self.btn_db = ttk.Button(btn_row_bottom, text="DB-Manager", command=self._open_db_manager)

        self.btn_scan.pack(side=tk.LEFT)
        self.btn_preview.pack(side=tk.LEFT, padx=(8, 0))
        self.btn_execute.pack(side=tk.LEFT, padx=(8, 0))
        conversions_intro = ttk.Label(
            conversions_tab,
            text="Konvertierungen nutzen konfigurierte Tools und Regeln. Nutze die Prüfung für eine Vorschau.",
            wraplength=740,
        )
        conversions_intro.pack(anchor="w", pady=(0, 10))

        conversions_paths = ttk.LabelFrame(conversions_tab, text="Pfade", padding=6)
        conversions_paths.pack(fill=tk.X, pady=(0, 10))
        conversions_paths.columnconfigure(1, weight=1)

        ttk.Label(conversions_paths, text="Quelle:").grid(row=0, column=0, sticky="w")
        self.conv_source_entry = ttk.Entry(conversions_paths, textvariable=self.source_var)
        self.conv_source_entry.grid(row=0, column=1, sticky="ew", padx=6)
        self.conv_source_btn = ttk.Button(conversions_paths, text="Quelle wählen…", command=self._choose_source)
        self.conv_source_btn.grid(row=0, column=2)

        ttk.Label(conversions_paths, text="Ziel:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.conv_dest_entry = ttk.Entry(conversions_paths, textvariable=self.dest_var)
        self.conv_dest_entry.grid(row=1, column=1, sticky="ew", padx=6, pady=(6, 0))
        self.conv_dest_btn = ttk.Button(conversions_paths, text="Ziel wählen…", command=self._choose_dest)
        self.conv_dest_btn.grid(row=1, column=2, pady=(6, 0))
        self.conv_open_dest_btn = ttk.Button(conversions_paths, text="Ziel öffnen", command=self._open_dest)
        self.conv_open_dest_btn.grid(row=1, column=3, padx=(6, 0), pady=(6, 0))

        conversions_row_top = ttk.Frame(conversions_tab)
        conversions_row_top.pack(fill=tk.X, pady=(0, 6))
        self.btn_execute_convert = ttk.Button(
            conversions_row_top,
            text="Konvertierungen ausführen",
            command=self._start_convert_only,
        )
        self.btn_audit = ttk.Button(
            conversions_row_top,
            text="Konvertierungen prüfen",
            command=self._start_audit,
        )
        self.btn_execute_convert.pack(side=tk.LEFT)
        self.btn_audit.pack(side=tk.LEFT, padx=(8, 0))

        conversions_row_bottom = ttk.Frame(conversions_tab)
        conversions_row_bottom.pack(fill=tk.X)
        self.btn_export_audit_csv = ttk.Button(
            conversions_row_bottom,
            text="Audit CSV exportieren",
            command=self._export_audit_csv,
        )
        self.btn_export_audit_json = ttk.Button(
            conversions_row_bottom,
            text="Audit JSON exportieren",
            command=self._export_audit_json,
        )
        self.btn_export_scan_csv = ttk.Button(
            conversions_row_bottom,
            text="Scan CSV exportieren",
            command=self._export_scan_csv,
        )
        self.btn_export_scan_json = ttk.Button(
            conversions_row_bottom,
            text="Scan JSON exportieren",
            command=self._export_scan_json,
        )
        self.btn_export_plan_csv = ttk.Button(
            conversions_row_bottom,
            text="Plan CSV exportieren",
            command=self._export_plan_csv,
        )
        self.btn_export_plan_json = ttk.Button(
            conversions_row_bottom,
            text="Plan JSON exportieren",
            command=self._export_plan_json,
        )
        def _safe_pack(widget: ttk.Widget, *, side=tk.LEFT, padx=(0, 0)) -> None:
            try:
                if widget.master is not conversions_row_bottom:
                    widget.configure(master=conversions_row_bottom)
            except Exception:
                pass
            try:
                widget.pack(side=side, padx=padx)
            except Exception:
                return

        _safe_pack(self.btn_export_audit_csv)
        _safe_pack(self.btn_export_audit_json, padx=(8, 0))
        _safe_pack(self.btn_export_scan_csv, padx=(16, 0))
        _safe_pack(self.btn_export_scan_json, padx=(8, 0))
        _safe_pack(self.btn_export_plan_csv, padx=(16, 0))
        _safe_pack(self.btn_export_plan_json, padx=(8, 0))
        _safe_pack(self.btn_resume, padx=(8, 0))
        _safe_pack(self.btn_retry_failed, padx=(8, 0))
        _safe_pack(self.btn_cancel, padx=(8, 0))
        _safe_pack(self.btn_db, padx=(8, 0))

        igir_intro = ttk.Label(
            igir_tab,
            text="IGIR nutzt eine externe Konsole. Pfad/Argumente konfigurieren und dann ausführen.",
            wraplength=740,
        )
        igir_intro.pack(anchor="w", pady=(0, 10))

        igir_cfg = ttk.LabelFrame(igir_tab, text="Konfiguration", padding=6)
        igir_cfg.pack(fill=tk.X, pady=(0, 10))
        igir_cfg.columnconfigure(1, weight=1)

        ttk.Label(igir_cfg, text="IGIR Exe:").grid(row=0, column=0, sticky="w")
        self.igir_exe_entry = ttk.Entry(igir_cfg, textvariable=self.igir_exe_var)
        self.igir_exe_entry.grid(row=0, column=1, sticky="ew", padx=6)
        self.btn_igir_browse = ttk.Button(igir_cfg, text="IGIR wählen…", command=self._choose_igir_exe)
        self.btn_igir_browse.grid(row=0, column=2)
        self.btn_igir_save = ttk.Button(igir_cfg, text="IGIR speichern", command=self._save_igir_settings_to_config)
        self.btn_igir_save.grid(row=0, column=3, padx=(6, 0))

        ttk.Label(igir_cfg, text="Args:").grid(row=1, column=0, sticky="nw", pady=(6, 0))
        self.igir_args_text = tk.Text(igir_cfg, height=4, width=50)
        self.igir_args_text.grid(row=1, column=1, sticky="ew", padx=6, pady=(6, 0))
        self.btn_igir_probe = ttk.Button(igir_cfg, text="IGIR prüfen", command=self._probe_igir)
        self.btn_igir_probe.grid(row=1, column=2, padx=(0, 6), pady=(6, 0), sticky="n")
        igir_args_hint = ttk.Label(igir_cfg, text="Eine Zeile pro Argument. Nutze {input} und {output_dir}.")
        igir_args_hint.grid(row=2, column=1, sticky="w", padx=6)

        self.igir_status_label = ttk.Label(igir_cfg, textvariable=self.igir_status_var)
        self.igir_status_label.grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 0))

        igir_paths = ttk.LabelFrame(igir_tab, text="Ausführen", padding=6)
        igir_paths.pack(fill=tk.X, pady=(0, 10))
        igir_paths.columnconfigure(1, weight=1)

        ttk.Label(igir_paths, text="Quelle:").grid(row=0, column=0, sticky="w")
        self.igir_source_entry = ttk.Entry(igir_paths, textvariable=self.source_var)
        self.igir_source_entry.grid(row=0, column=1, sticky="ew", padx=6)
        self.btn_igir_source = ttk.Button(igir_paths, text="Quelle wählen…", command=self._choose_source)
        self.btn_igir_source.grid(row=0, column=2)

        ttk.Label(igir_paths, text="Ziel:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.igir_dest_entry = ttk.Entry(igir_paths, textvariable=self.dest_var)
        self.igir_dest_entry.grid(row=1, column=1, sticky="ew", padx=6, pady=(6, 0))
        self.btn_igir_dest = ttk.Button(igir_paths, text="Ziel wählen…", command=self._choose_dest)
        self.btn_igir_dest.grid(row=1, column=2, pady=(6, 0))
        self.btn_igir_open_dest = ttk.Button(igir_paths, text="Ziel öffnen", command=self._open_dest)
        self.btn_igir_open_dest.grid(row=1, column=3, padx=(6, 0), pady=(6, 0))

        igir_row = ttk.Frame(igir_tab)
        igir_row.pack(fill=tk.X, pady=(0, 10))
        self.btn_igir_plan = ttk.Button(igir_row, text="IGIR Plan", command=self._start_igir_plan)
        self.btn_igir_execute = ttk.Button(igir_row, text="IGIR Execute", command=self._start_igir_execute)
        self.btn_igir_execute.configure(state="disabled")
        self.btn_igir_cancel = ttk.Button(igir_row, text="IGIR abbrechen", command=self._cancel_igir)
        self.btn_igir_cancel.configure(state="disabled")
        self.btn_igir_plan.pack(side=tk.LEFT)
        self.btn_igir_execute.pack(side=tk.LEFT, padx=(8, 0))
        self.btn_igir_cancel.pack(side=tk.LEFT, padx=(8, 0))

        self.progress = ttk.Progressbar(outer, orient=tk.HORIZONTAL, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(10, 0))

        self.status_var = tk.StringVar(value="Bereit")
        self.status_label = ttk.Label(outer, textvariable=self.status_var)
        self.status_label.pack(anchor="w", pady=(6, 0))

        self.summary_var = tk.StringVar(value="-")
        self.summary_label = ttk.Label(outer, textvariable=self.summary_var)
        self.summary_label.pack(anchor="w", pady=(2, 0))

        self.dat_status_var = tk.StringVar(value="DAT: -")

        theme_row = ttk.Frame(settings_tab)
        theme_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(theme_row, text="Theme:").pack(side=tk.LEFT)
        self.theme_combo = ttk.Combobox(
            theme_row,
            textvariable=self.theme_var,
            values=tuple(["Auto"] + self._theme_manager.get_theme_names()),
            state="readonly",
        )
        self.theme_combo.pack(side=tk.LEFT, padx=(6, 0))
        self.theme_combo.bind("<<ComboboxSelected>>", self._on_theme_changed)

        self.dat_status_label = ttk.Label(settings_tab, textvariable=self.dat_status_var)
        self.dat_status_label.pack(anchor="w", pady=(2, 0))

        dat_controls = ttk.Frame(settings_tab)
        dat_controls.pack(fill=tk.X, pady=(4, 0))
        self.btn_add_dat = ttk.Button(dat_controls, text="DAT-Ordner hinzufügen…", command=self._add_dat_folder)
        self.btn_add_dat.pack(side=tk.LEFT)
        self.btn_refresh_dat = ttk.Button(dat_controls, text="DAT Index bauen", command=self._refresh_dat_sources)
        self.btn_refresh_dat.pack(side=tk.LEFT, padx=(8, 0))
        self.btn_cancel_dat = ttk.Button(dat_controls, text="DAT Abbrechen", command=self._cancel_dat_index)
        self.btn_cancel_dat.configure(state="disabled")
        self.btn_cancel_dat.pack(side=tk.LEFT, padx=(8, 0))
        self.dat_auto_load_var = tk.BooleanVar(value=False)
        self.dat_auto_load_check = ttk.Checkbutton(
            dat_controls,
            text="DATs beim Start automatisch laden",
            variable=self.dat_auto_load_var,
            command=self._on_dat_auto_load_changed,
        )
        self.dat_auto_load_check.pack(side=tk.LEFT, padx=(8, 0))
        self.btn_clear_dat_cache = ttk.Button(dat_controls, text="DAT-Cache löschen", command=self._clear_dat_cache)
        self.btn_clear_dat_cache.pack(side=tk.LEFT, padx=(8, 0))

        table_frame = ttk.Frame(outer)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self._table_column_defs = [
            ("input", "Eingabepfad", 320, 520),
            ("name", "Name", 220, 320),
            ("system", "Erkannte Konsole/Typ", 200, 260),
            ("confidence", "Sicherheit", 110, 140),
            ("signals", "Signale", 160, 220),
            ("candidates", "Kandidaten", 160, 220),
            ("target", "Geplantes Ziel", 280, 520),
            ("action", "Aktion", 90, 140),
            ("status", "Status/Fehler", 240, 360),
        ]

        self.table = ttk.Treeview(
            table_frame,
            columns=(
                "input",
                "name",
                "system",
                "confidence",
                "signals",
                "candidates",
                "target",
                "action",
                "status",
            ),
            show="headings",
            height=8,
        )
        for key, text, width, _max_width in self._table_column_defs:
            self.table.heading(key, text=text, command=lambda c=key: self._sort_table(c, False))
            self.table.column(key, width=width, stretch=True)
        self.table["displaycolumns"] = [col for col, _, _, _ in self._table_column_defs]
        self._heading_drag_col = None
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.table.tag_configure("unknown", background="#fce8e8")

        table_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.table.yview)
        table_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.table.configure(yscrollcommand=table_scroll.set)

        details_frame = ttk.LabelFrame(outer, text="Details")
        details_frame.pack(fill=tk.X, pady=(8, 0))

        details_inner = ttk.Frame(details_frame)
        details_inner.pack(fill=tk.X, expand=False)

        self.details_text = tk.Text(details_inner, wrap="word", height=5)
        self.details_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.details_text.configure(state="disabled")

        details_scroll = ttk.Scrollbar(details_inner, orient=tk.VERTICAL, command=self.details_text.yview)
        details_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text.configure(yscrollcommand=details_scroll.set)

        self.table.bind("<<TreeviewSelect>>", self._on_row_selected)
        self.table.bind("<ButtonPress-1>", self._on_table_heading_press, add="+")
        self.table.bind("<ButtonRelease-1>", self._on_table_heading_release, add="+")
        self._autosize_table_columns()

        self._log_visible = True
        self.log_frame = ttk.Frame(self.root)
        log_header = ttk.Frame(self.log_frame)
        log_header.pack(fill=tk.X)
        ttk.Label(log_header, text="Log").pack(side=tk.LEFT, pady=(0, 4))
        self.log_toggle_btn = ttk.Button(log_header, text="Log ausblenden", command=self._toggle_log)
        self.log_toggle_btn.pack(side=tk.RIGHT)
        self.log_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=(6, 8))

        self.log_text = tk.Text(self.log_frame, wrap="word", height=10)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)


    def _apply_theme(self, theme) -> None:
        try:
            colors = theme.colors
        except Exception:
            return

        self.root.configure(bg=colors.background)
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background=colors.background)
        style.configure("TLabel", background=colors.background, foreground=colors.text)
        style.configure("TButton", background=colors.primary, foreground="white")
        style.map("TButton", background=[("active", colors.secondary)])
        style.configure("TEntry", fieldbackground=colors.background, foreground=colors.text)
        style.configure("TCombobox", fieldbackground=colors.background, foreground=colors.text)
        style.configure("Treeview", background=colors.background, foreground=colors.text, fieldbackground=colors.background)
        style.configure("Treeview.Heading", background=colors.border, foreground=colors.text)

        try:
            self.log_text.configure(bg=colors.background, fg=colors.text, insertbackground=colors.text)
            self.details_text.configure(bg=colors.background, fg=colors.text, insertbackground=colors.text)
        except Exception:
            pass

    def _is_drag_drop_enabled(self) -> bool:
        try:
            cfg = load_config()
            if not isinstance(cfg, dict):
                return True
            gui_cfg = cfg.get("gui_settings", {}) or {}
            return bool(gui_cfg.get("drag_drop_enabled", True))
        except Exception:
            return True

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
            paths = dat_cfg.get("import_paths") or []
            if isinstance(paths, str):
                paths = [paths]
            paths = [p for p in paths if p]
            if hasattr(self, "dat_auto_load_var"):
                self.dat_auto_load_var.set(auto_load)
            if not paths:
                self.dat_status_var.set("DAT: nicht konfiguriert")
            else:
                self.dat_status_var.set(f"DAT: konfiguriert ({len(paths)} Pfade)")
            if auto_load and paths:
                self._start_dat_auto_load()
        except Exception:
            return

    def _on_dat_auto_load_changed(self) -> None:
        try:
            data = self._load_dat_config()
            cfg = data["cfg"]
            dat_cfg = data["dat"]
            dat_cfg["auto_build"] = bool(self.dat_auto_load_var.get())
            cfg["dats"] = dat_cfg
            save_config(cfg)
        except Exception:
            return

    def _start_dat_auto_load(self) -> None:
        try:
            cfg = load_config()
            dat_cfg = cfg.get("dats", {}) if isinstance(cfg, dict) else {}
            index_path = dat_cfg.get("index_path") or os.path.join("data", "index", "romsorter_dat_index.sqlite")
            if Path(index_path).exists():
                self.dat_status_var.set("DAT: index vorhanden")
            else:
                self.dat_status_var.set("DAT: index fehlt")
        except Exception as exc:
            self.dat_status_var.set(f"DAT: Fehler ({exc})")

    def _schedule_dat_poll(self) -> None:
        self._dat_poll_job = None

    def _poll_dat_status(self) -> None:
        self._dat_poll_job = None

    def _add_dat_folder(self) -> None:
        directory = filedialog.askdirectory(title="DAT-Ordner auswählen")
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
        self.dat_status_var.set("DAT: Pfade aktualisiert")
        if bool(dat_cfg.get("auto_build", False)):
            self._start_dat_auto_load()

    def _refresh_dat_sources(self) -> None:
        try:
            if self._dat_index_thread is not None:
                return
            self.dat_status_var.set("DAT: Index wird gebaut...")
            self._dat_index_cancel_token = CancelToken()

            def task() -> dict:
                return build_dat_index(cancel_token=self._dat_index_cancel_token)

            self._dat_index_thread = threading.Thread(
                target=self._run_dat_index_worker,
                args=(task,),
                daemon=True,
            )
            self.btn_refresh_dat.configure(state="disabled")
            if hasattr(self, "btn_cancel_dat"):
                self.btn_cancel_dat.configure(state="normal")
            self._dat_index_thread.start()
        except Exception as exc:
            self.dat_status_var.set(f"DAT: Fehler ({exc})")

    def _run_dat_index_worker(self, task: Callable[[], dict]) -> None:
        try:
            result = task()
            self._queue.put(("dat_index_done", result))
        except Exception as exc:
            self._queue.put(("dat_index_error", str(exc)))

    def _cancel_dat_index(self) -> None:
        if self._dat_index_cancel_token is None:
            return
        try:
            self._dat_index_cancel_token.cancel()
        except Exception:
            pass

    def _clear_dat_cache(self) -> None:
        try:
            confirm = messagebox.askyesno(
                "DAT-Cache löschen",
                "Zwischengespeicherten DAT-Index löschen? Er wird beim nächsten Aktualisieren neu aufgebaut.",
            )
            if not confirm:
                return
            cfg = load_config()
            dat_cfg = cfg.get("dats", {}) if isinstance(cfg, dict) else {}
            index_path = dat_cfg.get("index_path") or os.path.join("data", "index", "romsorter_dat_index.sqlite")
            index_file = Path(index_path)
            if index_file.exists():
                index_file.unlink()
                self.dat_status_var.set("DAT: Index gelöscht")
                self._append_log("DAT-Index gelöscht")
            else:
                self.dat_status_var.set("DAT: Index nicht gefunden")
        except Exception as exc:
            self.dat_status_var.set(f"DAT: Cache löschen fehlgeschlagen ({exc})")

    def _get_igir_args_list(self) -> list[str]:
        try:
            raw = self.igir_args_text.get("1.0", "end")
        except Exception:
            raw = ""
        lines = [line.strip() for line in str(raw).splitlines()]
        return [line for line in lines if line]

    def _build_igir_config_snapshot(self) -> dict:
        path = Path(__file__).resolve().parents[2] / "tools" / "igir.yaml"
        data: dict = {}
        try:
            if path.exists():
                raw = path.read_text(encoding="utf-8")
                try:
                    import yaml  # type: ignore

                    data = yaml.safe_load(raw)
                except Exception:
                    data = json.loads(raw)
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        data["exe_path"] = self.igir_exe_var.get().strip()
        data.setdefault("args_templates", {})
        if isinstance(data.get("args_templates"), dict):
            data["args_templates"]["execute"] = self._get_igir_args_list()
        return data

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
            exe_path = str(data.get("exe_path") or "").strip()
            args_templates = data.get("args_templates") or {}
            args = args_templates.get("execute") or []
            if isinstance(args, str):
                args = [args]
            args = [str(arg) for arg in args if str(arg).strip()]
            self.igir_exe_var.set(exe_path)
            try:
                self.igir_args_text.delete("1.0", "end")
                if args:
                    self.igir_args_text.insert("1.0", "\n".join(args))
            except Exception:
                pass
        except Exception:
            return

    def _save_igir_settings_to_config(self) -> None:
        try:
            path = Path(__file__).resolve().parents[2] / "tools" / "igir.yaml"
            data = self._build_igir_config_snapshot()
            payload = None
            try:
                import yaml  # type: ignore

                payload = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
            except Exception:
                payload = json.dumps(data, indent=2)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8")
            self.igir_status_var.set("IGIR gespeichert.")
        except Exception as exc:
            self.igir_status_var.set(f"IGIR speichern fehlgeschlagen ({exc})")

    def _choose_igir_exe(self) -> None:
        filename = filedialog.askopenfilename(
            title="IGIR auswählen",
            filetypes=[("Executables", "*.exe *.bat *.cmd"), ("All files", "*")],
        )
        if filename:
            self.igir_exe_var.set(filename)

    def _probe_igir(self) -> None:
        try:
            cfg = self._build_igir_config_snapshot()
            result = probe_igir(cfg)
            msg = result.probe_message or result.probe_status
            if result.version:
                msg = f"{msg} ({result.version})"
            self.igir_status_var.set(f"Status: {msg}")
        except Exception as exc:
            self.igir_status_var.set(f"Status: Probe fehlgeschlagen ({exc})")

    def _set_igir_running(self, running: bool) -> None:
        try:
            if running:
                self.btn_igir_plan.configure(state="disabled")
                self.btn_igir_execute.configure(state="disabled")
                self.btn_igir_cancel.configure(state="normal")
                self.btn_igir_probe.configure(state="disabled")
                self.btn_igir_save.configure(state="disabled")
            else:
                self.btn_igir_plan.configure(state="normal")
                self.btn_igir_execute.configure(state="normal" if self._igir_plan_ready else "disabled")
                self.btn_igir_cancel.configure(state="disabled")
                self.btn_igir_probe.configure(state="normal")
                self.btn_igir_save.configure(state="normal")
        except Exception:
            return

    def _update_igir_buttons(self) -> None:
        try:
            self.btn_igir_execute.configure(state="normal" if self._igir_plan_ready else "disabled")
        except Exception:
            return

    def _start_igir_plan(self) -> None:
        if self._igir_thread is not None and self._igir_thread.is_alive():
            messagebox.showinfo("IGIR", "IGIR läuft bereits.")
            return
        source = self.source_var.get().strip()
        dest = self.dest_var.get().strip()
        if not source:
            messagebox.showinfo("IGIR", "Bitte Quelle wählen.")
            return
        if not dest:
            messagebox.showinfo("IGIR", "Bitte Ziel wählen.")
            return

        self._save_igir_settings_to_config()
        self._igir_cancel_token = CancelToken()
        temp_dir = str((Path(__file__).resolve().parents[3] / "temp").resolve())
        report_dir = str((Path(__file__).resolve().parents[3] / "data" / "reports" / "igir").resolve())
        self._set_igir_running(True)
        self.igir_status_var.set("IGIR Plan läuft...")
        self._igir_thread = threading.Thread(
            target=self._run_igir_worker,
            args=("plan", source, dest, temp_dir, report_dir),
            daemon=True,
        )
        self._igir_thread.start()

    def _start_igir_execute(self) -> None:
        if not self._igir_plan_ready:
            messagebox.showinfo("IGIR", "Bitte zuerst IGIR Plan ausführen.")
            return
        if self._igir_thread is not None and self._igir_thread.is_alive():
            messagebox.showinfo("IGIR", "IGIR läuft bereits.")
            return
        source = self.source_var.get().strip()
        dest = self.dest_var.get().strip()
        if not source:
            messagebox.showinfo("IGIR", "Bitte Quelle wählen.")
            return
        if not dest:
            messagebox.showinfo("IGIR", "Bitte Ziel wählen.")
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
        confirm = messagebox.askyesno("IGIR Execute bestätigen", confirm_text)
        if not confirm:
            return

        self._save_igir_settings_to_config()
        self._igir_cancel_token = CancelToken()
        temp_dir = str((Path(__file__).resolve().parents[3] / "temp").resolve())
        report_dir = str((Path(__file__).resolve().parents[3] / "data" / "reports" / "igir").resolve())
        self._set_igir_running(True)
        self.igir_status_var.set("IGIR Execute läuft...")
        self._igir_thread = threading.Thread(
            target=self._run_igir_worker,
            args=("execute", source, dest, temp_dir, report_dir, True),
            daemon=True,
        )
        self._igir_thread.start()

    def _run_igir_worker(
        self,
        mode: str,
        source: str,
        dest: str,
        temp_dir: str,
        report_dir: str,
        explicit_user_action: bool = False,
    ) -> None:
        try:
            try:
                Path(temp_dir).mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            if mode == "plan":
                result = igir_plan(
                    input_path=source,
                    output_dir=dest,
                    dest_root=dest,
                    report_dir=report_dir,
                    temp_dir=temp_dir,
                    log_cb=lambda msg: self._queue.put(("log", f"[IGIR] {msg}")),
                    cancel_token=self._igir_cancel_token,
                )
                if result.cancelled:
                    self._queue.put(("igir_plan_done", result))
                    return
                if result.ok:
                    self._queue.put(("igir_plan_done", result))
                    return
                self._queue.put(("igir_error", result))
            else:
                result = igir_execute(
                    input_path=source,
                    output_dir=dest,
                    dest_root=dest,
                    temp_dir=temp_dir,
                    log_cb=lambda msg: self._queue.put(("log", f"[IGIR] {msg}")),
                    cancel_token=self._igir_cancel_token,
                    plan_confirmed=self._igir_plan_ready,
                    explicit_user_action=explicit_user_action,
                )
                if result.cancelled:
                    self._queue.put(("igir_execute_done", result))
                    return
                if result.success:
                    self._queue.put(("igir_execute_done", result))
                    return
                self._queue.put(("igir_error", result))
        except Exception as exc:
            tb = traceback.format_exc()
            self._queue.put(("igir_error", (f"IGIR Fehler: {exc}", tb)))

    def _cancel_igir(self) -> None:
        try:
            self._igir_cancel_token.cancel()
            self.igir_status_var.set("IGIR Abbruch angefordert...")
        except Exception:
            return

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
                self.theme_var.set("Auto")
            if theme_name in self._theme_manager.get_theme_names():
                self._theme_manager.set_current_theme(theme_name)
                if self.theme_var.get() != "Auto":
                    self.theme_var.set(theme_name)
        except Exception:
            return

    def _load_sort_settings_from_config(self) -> None:
        try:
            cfg = load_config()
            if not isinstance(cfg, dict):
                return
            sorting_cfg = cfg.get("features", {}).get("sorting", {}) or {}
            console_enabled = bool(sorting_cfg.get("console_sorting_enabled", True))
            create_console = bool(sorting_cfg.get("create_console_folders", True))
            self.console_folders_var.set(console_enabled and create_console)
            self.region_subfolders_var.set(bool(sorting_cfg.get("region_based_sorting", False)))
            self.preserve_structure_var.set(bool(sorting_cfg.get("preserve_folder_structure", False)))
        except Exception:
            return

    def _on_sort_settings_changed(self) -> None:
        try:
            cfg = load_config()
            if not isinstance(cfg, dict):
                cfg = {}
            features_cfg = cfg.get("features", {}) or {}
            sorting_cfg = features_cfg.get("sorting", {}) or {}
            console_checked = bool(self.console_folders_var.get())
            sorting_cfg["console_sorting_enabled"] = console_checked
            sorting_cfg["create_console_folders"] = console_checked
            sorting_cfg["region_based_sorting"] = bool(self.region_subfolders_var.get())
            sorting_cfg["preserve_folder_structure"] = bool(self.preserve_structure_var.get())
            features_cfg["sorting"] = sorting_cfg
            cfg["features"] = features_cfg
            save_config(cfg)
        except Exception:
            return

    def _on_theme_changed(self, _event=None) -> None:
        name = self.theme_var.get()
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
            save_config(cfg)
        except Exception:
            pass

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
                self.root.geometry(f"{width}x{height}")
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
            gui_cfg["window_width"] = int(self.root.winfo_width())
            gui_cfg["window_height"] = int(self.root.winfo_height())
            cfg["gui_settings"] = gui_cfg
            save_config(cfg)
        except Exception:
            return

    def _on_close(self) -> None:
        try:
            if self._igir_thread is not None and self._igir_thread.is_alive():
                self._igir_cancel_token.cancel()
        except Exception:
            pass
        self._save_window_size()
        self._remove_log_handler()
        self.root.destroy()

    def _install_log_handler(self) -> None:
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            if getattr(handler, "_tk_gui_handler", False):
                root_logger.removeHandler(handler)

        handler = _TkLogHandler(self)
        handler._tk_gui_handler = True
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
            if getattr(handler, "_tk_gui_handler", False):
                try:
                    root_logger.removeHandler(handler)
                except Exception:
                    pass

    def _open_db_manager(self) -> None:
        DatabaseManagerDialog(self.root)

    def _normalize_drop_path(self, files: list[str]) -> Optional[str]:
        if not files:
            return None
        raw = files[0]
        if not raw:
            return None
        path = os.path.normpath(raw)
        if os.path.isfile(path):
            return os.path.dirname(path)
        if os.path.isdir(path):
            return path
        return None

    def _on_drop_source(self, files: list[str]) -> None:
        path = self._normalize_drop_path(files)
        if path:
            self.source_var.set(path)
            self._append_log(f"DnD source: {path}")

    def _on_drop_dest(self, files: list[str]) -> None:
        path = self._normalize_drop_path(files)
        if path:
            self.dest_var.set(path)
            self._append_log(f"DnD destination: {path}")

    def _choose_source(self) -> None:
        directory = filedialog.askdirectory(title="Select source folder")
        if directory:
            self.source_var.set(directory)

    def _choose_dest(self) -> None:
        directory = filedialog.askdirectory(title="Select destination folder")
        if directory:
            self.dest_var.set(directory)

    def _open_dest(self) -> None:
        directory = self.dest_var.get().strip()
        if not directory:
            messagebox.showinfo("Kein Ziel", "Bitte zuerst einen Zielordner wählen.")
            return
        try:
            if os.name == "nt":
                os.startfile(directory)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", directory])
            else:
                subprocess.Popen(["xdg-open", directory])
        except Exception:
            messagebox.showwarning("Öffnen fehlgeschlagen", "Zielordner konnte nicht geöffnet werden.")

    def _append_log(self, text: str) -> None:
        if not text:
            return
        self._log_buffer.append(str(text))
        if not self._log_flush_scheduled:
            self._log_flush_scheduled = True
            self.root.after(100, self._flush_log)

    def _flush_log(self) -> None:
        self._log_flush_scheduled = False
        if not self._log_buffer:
            return
        payload = "\n".join(self._log_buffer) + "\n"
        self._log_buffer.clear()
        # Ringbuffer: keep last ~2000 lines.
        self.log_text.insert(tk.END, payload)
        try:
            lines = int(self.log_text.index("end-1c").split(".")[0])
            if lines > 2000:
                self.log_text.delete("1.0", f"{lines - 2000}.0")
        except Exception:
            pass
        self.log_text.see(tk.END)

    def _toggle_log(self) -> None:
        self._set_log_visible(not self._log_visible)

    def _set_log_visible(self, visible: bool, persist: bool = True) -> None:
        self._log_visible = bool(visible)
        if self._log_visible:
            self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            for child in self.log_frame.winfo_children():
                if isinstance(child, ttk.Scrollbar):
                    child.pack(side=tk.RIGHT, fill=tk.Y)
            self.log_toggle_btn.configure(text="Log ausblenden")
        else:
            for child in list(self.log_frame.winfo_children()):
                if isinstance(child, ttk.Scrollbar):
                    child.pack_forget()
            self.log_text.pack_forget()
            self.log_toggle_btn.configure(text="Log anzeigen")
        if persist:
            self._save_log_visibility()

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

    def _save_log_visibility(self) -> None:
        try:
            cfg = load_config()
            if not isinstance(cfg, dict):
                cfg = {}
            gui_cfg = cfg.get("gui_settings", {}) or {}
            gui_cfg["log_visible"] = bool(self._log_visible)
            cfg["gui_settings"] = gui_cfg
            save_config(cfg)
        except Exception:
            return

    def _set_details(self, text: str) -> None:
        self.details_text.configure(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(tk.END, text)
        self.details_text.configure(state="disabled")

    def _on_row_selected(self, _event: object = None) -> None:
        try:
            selection = self.table.selection()
            if not selection:
                return
            iid = selection[0]
            values = self.table.item(iid, "values")
            if not values:
                return
            status = values[8] if len(values) >= 9 else ""
            confidence = values[3] if len(values) >= 4 else ""
            signals = values[4] if len(values) >= 5 else ""
            candidates = values[5] if len(values) >= 6 else ""
            full = values[0] if len(values) >= 1 else ""

            meta = self._row_meta.get(str(iid), {})
            source = meta.get("source") or "-"
            exact = meta.get("is_exact")
            if exact is True:
                exact_text = "ja"
            elif exact is False:
                exact_text = "nein"
            else:
                exact_text = "-"

            extra_lines = []
            if meta.get("action"):
                extra_lines.append(f"Aktion: {meta.get('action')}")
            if meta.get("target"):
                extra_lines.append(f"Ziel: {meta.get('target')}")
            if meta.get("conversion_rule"):
                extra_lines.append(f"Regel: {meta.get('conversion_rule')}")
            if meta.get("conversion_tool"):
                extra_lines.append(f"Tool: {meta.get('conversion_tool')}")
            if meta.get("conversion_output"):
                extra_lines.append(f"Output: {meta.get('conversion_output')}")
            if meta.get("current_extension"):
                extra_lines.append(f"Aktuell: {meta.get('current_extension')}")
            if meta.get("recommended_extension"):
                extra_lines.append(f"Empfohlen: {meta.get('recommended_extension')}")
            if meta.get("rule_name"):
                extra_lines.append(f"Audit‑Regel: {meta.get('rule_name')}")
            if meta.get("tool_key"):
                extra_lines.append(f"Audit‑Tool: {meta.get('tool_key')}")
            if meta.get("reason"):
                extra_lines.append(f"Hinweis: {meta.get('reason')}")

            self._set_details(
                f"{full}\n\nConfidence: {confidence}\nQuelle: {source}\nExact: {exact_text}"
                f"\nSignale: {signals}\nKandidaten: {candidates}"
                + ("\n" + "\n".join(extra_lines) if extra_lines else "")
                + f"\n\n{status}"
            )
        except Exception:
            return

    def _format_confidence(self, value: Optional[float]) -> str:
        return format_confidence(value)

    def _format_signals(self, item: object, default: str = "-") -> str:
        return format_signals(item, default=default)

    def _format_candidates(self, item: object) -> str:
        return format_candidates(item)

    def _validate_size_entry(self, value: str) -> bool:
        if value == "":
            return True
        if value in (".", ","):
            return True
        if not re.match(r"^\d*(?:[\.,]\d*)?$", value):
            return False
        try:
            return float(value.replace(",", ".")) >= 0
        except Exception:
            return False

    def _on_filters_changed(self, _event: object = None) -> None:
        if self._sort_plan is not None:
            self._sort_plan = None
            self._append_log("Filters changed: sort plan invalidated. Please run Preview Sort again.")

        if self._scan_result is not None:
            self._populate_scan_table(self._get_filtered_scan_result())

    def _clear_filters(self) -> None:
        self.lang_filter_var.set("All")
        self.ver_filter_var.set("All")
        self.region_filter_var.set("All")
        self.extension_filter_var.set("")
        self.min_size_var.set("")
        self.max_size_var.set("")
        self.dedupe_var.set(True)
        self.hide_unknown_var.set(False)
        self._on_filters_changed()

    def _get_filtered_scan_result(self) -> ScanResult:
        if self._scan_result is None:
            raise RuntimeError("No scan result available")

        lang = (self.lang_filter_var.get() or "All").strip() or "All"
        ver = (self.ver_filter_var.get() or "All").strip() or "All"
        region = (self.region_filter_var.get() or "All").strip() or "All"
        extension_filter = (self.extension_filter_var.get() or "").strip()
        min_size = self._parse_size_mb(self.min_size_var.get())
        max_size = self._parse_size_mb(self.max_size_var.get())
        dedupe = bool(self.dedupe_var.get())
        hide_unknown = bool(self.hide_unknown_var.get())

        filtered = filter_scan_items(
            list(self._scan_result.items),
            language_filter=lang,
            version_filter=ver,
            region_filter=region,
            extension_filter=extension_filter,
            min_size_mb=min_size,
            max_size_mb=max_size,
            dedupe_variants=dedupe,
        )

        if hide_unknown:
            min_conf = self._get_min_confidence()
            filtered = [it for it in filtered if self._is_confident_for_display(it, min_conf)]

        return ScanResult(
            source_path=self._scan_result.source_path,
            items=filtered,
            stats=dict(self._scan_result.stats),
            cancelled=bool(self._scan_result.cancelled),
        )

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

    def _parse_size_mb(self, text: str) -> Optional[float]:
        cleaned = (text or "").strip()
        if not cleaned:
            return None
        try:
            value = float(cleaned)
        except Exception:
            return None
        if value < 0:
            return None
        return value

    def _is_confident_for_display(self, item: "ScanItem", min_confidence: float) -> bool:
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
            lang_values, ver_values, region_values = self._load_filter_defaults()
            self.lang_filter_combo.configure(values=tuple(lang_values))
            self.lang_filter_var.set(lang_values[0])
            self.ver_filter_combo.configure(values=tuple(ver_values))
            self.ver_filter_var.set(ver_values[0])
            self.region_filter_combo.configure(values=tuple(region_values))
            self.region_filter_var.set(region_values[0])
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
                try:
                    r = infer_region_from_name(item.input_path)
                except Exception:
                    r = None
            if not r or str(r) == "Unknown":
                has_unknown_region = True
            else:
                regions.add(str(r))

        lang_values = ["All"]
        if has_unknown_lang:
            lang_values.append("Unknown")
        lang_values.extend(sorted(langs))

        ver_values = ["All"]
        if has_unknown_ver:
            ver_values.append("Unknown")
        ver_values.extend(sorted(vers))

        region_values = ["All"]
        if has_unknown_region:
            region_values.append("Unknown")
        region_values.extend(sorted(regions))

        self.lang_filter_combo.configure(values=tuple(lang_values))
        if self.lang_filter_var.get() not in lang_values:
            self.lang_filter_var.set("All")

        self.ver_filter_combo.configure(values=tuple(ver_values))
        if self.ver_filter_var.get() not in ver_values:
            self.ver_filter_var.set("All")

        self.region_filter_combo.configure(values=tuple(region_values))
        if self.region_filter_var.get() not in region_values:
            self.region_filter_var.set("All")

    def _load_filter_defaults(self) -> Tuple[list[str], list[str], list[str]]:
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

    def _on_row_selected(self, _event: object = None) -> None:
        try:
            selection = self.table.selection()
            if not selection:
                return
            iid = selection[0]
            values = self.table.item(iid, "values")
            if not values:
                return
            # values: (input, name, system, confidence, signals, candidates, target, action, status)
            status = values[8] if len(values) >= 9 else ""
            confidence = values[3] if len(values) >= 4 else ""
            signals = values[4] if len(values) >= 5 else ""
            candidates = values[5] if len(values) >= 6 else ""
            # Show full input path + status in details for convenience.
            full = values[0] if len(values) >= 1 else ""
            self._set_details(
                f"{full}\n\nConfidence: {confidence}\nSignals: {signals}\nCandidates: {candidates}\n\n{status}"
            )
        except Exception:
            return

    def _rom_display_name(self, input_path: str) -> str:
        return rom_display_name(input_path)

    def _sort_table(self, col: str, descending: bool) -> None:
        try:
            items = [(self.table.set(k, col), k) for k in self.table.get_children("")]
            items.sort(reverse=descending)
            for index, (_val, k) in enumerate(items):
                self.table.move(k, "", index)
            self.table.heading(col, command=lambda: self._sort_table(col, not descending))
        except Exception:
            return

    def _autosize_table_columns(self) -> None:
        try:
            font = tkfont.nametofont("TkDefaultFont")
            for key, text, min_width, max_width in self._table_column_defs:
                width = max(min_width, font.measure(text) + 24)
                if max_width:
                    width = min(width, max_width)
                self.table.column(key, width=width)
        except Exception:
            return

    def _on_table_heading_press(self, event: tk.Event) -> None:
        try:
            if self.table.identify_region(event.x, event.y) != "heading":
                return
            self._heading_drag_col = self.table.identify_column(event.x)
        except Exception:
            self._heading_drag_col = None

    def _on_table_heading_release(self, event: tk.Event) -> None:
        try:
            if not self._heading_drag_col:
                return
            if self.table.identify_region(event.x, event.y) != "heading":
                return
            target = self.table.identify_column(event.x)
            if not target or target == self._heading_drag_col:
                return
            order = list(self.table["displaycolumns"])
            if not order:
                order = list(self.table["columns"])
            src_index = int(self._heading_drag_col.replace("#", "")) - 1
            dst_index = int(target.replace("#", "")) - 1
            if src_index < 0 or dst_index < 0 or src_index >= len(order) or dst_index >= len(order):
                return
            col = order.pop(src_index)
            order.insert(dst_index, col)
            self.table["displaycolumns"] = order
            self._autosize_table_columns()
        except Exception:
            return
        finally:
            self._heading_drag_col = None

    def _choose_source(self) -> None:
        directory = filedialog.askdirectory(title="Select source folder")
        if directory:
            self.source_var.set(directory)

    def _choose_dest(self) -> None:
        directory = filedialog.askdirectory(title="Select destination folder")
        if directory:
            self.dest_var.set(directory)

    def _open_dest(self) -> None:
        directory = self.dest_var.get().strip()
        if not directory:
            messagebox.showinfo("Kein Ziel", "Bitte zuerst einen Zielordner wählen.")
            return
        try:
            if os.name == "nt":
                os.startfile(directory)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", directory])
            else:
                subprocess.Popen(["xdg-open", directory])
        except Exception:
            messagebox.showwarning("Öffnen fehlgeschlagen", "Zielordner konnte nicht geöffnet werden.")

    def _set_running(self, running: bool) -> None:
        state_normal = "disabled" if running else "normal"

        self.btn_scan.configure(state=state_normal)
        self.btn_preview.configure(state=state_normal)
        self.btn_execute.configure(state=state_normal)
        self.btn_execute_convert.configure(state=state_normal)
        self.btn_audit.configure(state=state_normal)
        export_scan_state = "normal" if (not running and self._scan_result is not None) else "disabled"
        export_plan_state = "normal" if (not running and self._sort_plan is not None) else "disabled"
        self.btn_export_scan_csv.configure(state=export_scan_state)
        self.btn_export_scan_json.configure(state=export_scan_state)
        self.btn_export_plan_csv.configure(state=export_plan_state)
        self.btn_export_plan_json.configure(state=export_plan_state)
        export_state = "normal" if (not running and self._audit_report is not None) else "disabled"
        self.btn_export_audit_csv.configure(state=export_state)
        self.btn_export_audit_json.configure(state=export_state)
        self.btn_resume.configure(state="disabled" if running else ("normal" if self._can_resume() else "disabled"))
        self.btn_retry_failed.configure(state="disabled" if running else ("normal" if self._can_retry_failed() else "disabled"))
        self.btn_cancel.configure(state="normal" if running else "disabled")
        self.btn_source.configure(state=state_normal)
        self.btn_dest.configure(state=state_normal)
        self.btn_open_dest.configure(state=state_normal)
        self.source_entry.configure(state=state_normal)
        self.dest_entry.configure(state=state_normal)
        self.mode_combo.configure(state="disabled" if running else "readonly")
        self.conflict_combo.configure(state="disabled" if running else "readonly")
        self.lang_filter_combo.configure(state="disabled" if running else "readonly")
        self.ver_filter_combo.configure(state="disabled" if running else "readonly")
        self.region_filter_combo.configure(state="disabled" if running else "readonly")
        self.extension_entry.configure(state=state_normal)
        self.min_size_entry.configure(state=state_normal)
        self.max_size_entry.configure(state=state_normal)
        self.btn_clear_filters.configure(state=state_normal)
        self.console_folders_check.configure(state=state_normal)
        self.region_subfolders_check.configure(state=state_normal)
        self.preserve_structure_check.configure(state=state_normal)
        self.dedupe_check.configure(state="disabled" if running else "normal")
        self.hide_unknown_check.configure(state="disabled" if running else "normal")
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
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return
        self.btn_resume.configure(state="normal" if self._can_resume() else "disabled")
        self.btn_retry_failed.configure(state="normal" if self._can_retry_failed() else "disabled")

    def _on_filters_changed(self, _event: object = None) -> None:
        # Changing filters invalidates existing plan.
        if self._sort_plan is not None:
            self._sort_plan = None
            self._append_log("Filters changed: sort plan invalidated. Please run Preview Sort again.")

        if self._scan_result is not None:
            self._populate_scan_table(self._get_filtered_scan_result())

    def _clear_filters(self) -> None:
        self.lang_filter_var.set("All")
        self.ver_filter_var.set("All")
        self.region_filter_var.set("All")
        self.extension_filter_var.set("")
        self.min_size_var.set("")
        self.max_size_var.set("")
        self.dedupe_var.set(True)
        self.hide_unknown_var.set(False)
        self._on_filters_changed()

    def _validate_size_entry(self, value: str) -> bool:
        if value == "":
            return True
        if value in (".", ","):
            return True
        if not re.match(r"^\d*(?:[\.,]\d*)?$", value):
            return False
        try:
            return float(value.replace(",", ".")) >= 0
        except Exception:
            return False

    def _get_filtered_scan_result(self) -> ScanResult:
        if self._scan_result is None:
            raise RuntimeError("No scan result available")

        lang = (self.lang_filter_var.get() or "All").strip() or "All"
        ver = (self.ver_filter_var.get() or "All").strip() or "All"

        region = (self.region_filter_var.get() or "All").strip() or "All"
        extension_filter = (self.extension_filter_var.get() or "").strip()
        min_size = self._parse_size_mb(self.min_size_var.get())
        max_size = self._parse_size_mb(self.max_size_var.get())
        dedupe = bool(self.dedupe_var.get())
        hide_unknown = bool(self.hide_unknown_var.get())

        filtered = filter_scan_items(
            list(self._scan_result.items),
            language_filter=lang,
            version_filter=ver,
            region_filter=region,
            extension_filter=extension_filter,
            min_size_mb=min_size,
            max_size_mb=max_size,
            dedupe_variants=dedupe,
        )

        if hide_unknown:
            min_conf = self._get_min_confidence()
            filtered = [it for it in filtered if self._is_confident_for_display(it, min_conf)]

        return ScanResult(
            source_path=self._scan_result.source_path,
            items=filtered,
            stats=dict(self._scan_result.stats),
            cancelled=bool(self._scan_result.cancelled),
        )

    def _get_min_confidence(self) -> float:
        try:
            from ...config.io import load_config
            cfg = load_config()
        except Exception:
            return 0.95
        try:
            sorting_cfg = cfg.get("features", {}).get("sorting", {}) or {}
            return float(sorting_cfg.get("confidence_threshold", 0.95))
        except Exception:
            return 0.95

    def _parse_size_mb(self, text: str) -> Optional[float]:
        cleaned = (text or "").strip()
        if not cleaned:
            return None
        try:
            value = float(cleaned)
        except Exception:
            return None
        if value < 0:
            return None
        return value

    def _is_confident_for_display(self, item: "ScanItem", min_confidence: float) -> bool:
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
            lang_values, ver_values, region_values = self._load_filter_defaults()
            self.lang_filter_combo.configure(values=tuple(lang_values))
            self.lang_filter_var.set(lang_values[0])
            self.ver_filter_combo.configure(values=tuple(ver_values))
            self.ver_filter_var.set(ver_values[0])
            self.region_filter_combo.configure(values=tuple(region_values))
            self.region_filter_var.set(region_values[0])
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
                try:
                    r = infer_region_from_name(item.input_path)
                except Exception:
                    r = None
            if not r or str(r) == "Unknown":
                has_unknown_region = True
            else:
                regions.add(str(r))

        lang_values = ["All"]
        if has_unknown_lang:
            lang_values.append("Unknown")
        lang_values.extend(sorted(langs))

        ver_values = ["All"]
        if has_unknown_ver:
            ver_values.append("Unknown")
        ver_values.extend(sorted(vers))

        region_values = ["All"]
        if has_unknown_region:
            region_values.append("Unknown")
        region_values.extend(sorted(regions))

        self.lang_filter_combo.configure(values=tuple(lang_values))
        if self.lang_filter_var.get() not in lang_values:
            self.lang_filter_var.set("All")

        self.ver_filter_combo.configure(values=tuple(ver_values))
        if self.ver_filter_var.get() not in ver_values:
            self.ver_filter_var.set("All")

        self.region_filter_combo.configure(values=tuple(region_values))
        if self.region_filter_var.get() not in region_values:
            self.region_filter_var.set("All")

    def _load_filter_defaults(self) -> Tuple[list[str], list[str], list[str]]:
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

    def _validate_paths(self, *, require_dest: bool = True) -> Optional[Tuple[str, str]]:
        source = self.source_var.get().strip()
        dest = self.dest_var.get().strip()
        if not source:
            messagebox.showwarning("Quelle fehlt", "Bitte einen Quellordner wählen.")
            return None
        if require_dest and not dest:
            messagebox.showwarning("Ziel fehlt", "Bitte einen Zielordner wählen.")
            return None
        return source, dest

    def _clear_table(self) -> None:
        for item in self.table.get_children():
            self.table.delete(item)
        self._row_meta.clear()

    def _populate_scan_table(self, scan: ScanResult) -> None:
        self._clear_table()
        for item in scan.items:
            min_conf = self._get_min_confidence()
            is_confident = self._is_confident_for_display(item, min_conf)
            status = "found" if is_confident else "unknown/low-confidence"
            tags = ("unknown",) if not is_confident else ()
            iid = self.table.insert(
                "",
                tk.END,
                values=(
                    str(item.input_path or ""),
                    self._rom_display_name(item.input_path),
                    item.detected_system,
                    self._format_confidence(item.detection_confidence),
                    self._format_signals(item),
                    self._format_candidates(item),
                    "",
                    "scan",
                    status,
                ),
                tags=tags,
            )
            self._row_meta[str(iid)] = {
                "source": getattr(item, "detection_source", None),
                "is_exact": bool(getattr(item, "is_exact", False)),
            }

        try:
            total = len(self._scan_result.items) if self._scan_result else len(scan.items)
            self.status_var.set(f"Scan-Ergebnisse: {len(scan.items)} (gefiltert von {total})")
        except Exception:
            pass

        try:
            min_conf = self._get_min_confidence()
            unknown_count = sum(1 for item in scan.items if not self._is_confident_for_display(item, min_conf))
            self.summary_var.set(f"{len(scan.items)} gesamt | {unknown_count} unbekannt/niedrige Sicherheit")
        except Exception:
            self.summary_var.set("-")

    def _populate_plan_table(self, plan: SortPlan) -> None:
        self._clear_table()
        self._plan_row_iids = []
        self._set_details("")
        for act in plan.actions:
            iid = self.table.insert(
                "",
                tk.END,
                values=(
                    str(act.input_path or ""),
                    self._rom_display_name(act.input_path),
                    act.detected_system,
                    "",
                    "",
                    "",
                    act.planned_target_path or "",
                    act.action,
                    act.error or act.status,
                ),
            )
            self._plan_row_iids.append(str(iid))
            self._row_meta[str(iid)] = {
                "target": act.planned_target_path,
                "action": act.action,
                "status": act.status,
                "error": act.error,
                "conversion_rule": getattr(act, "conversion_rule", None),
                "conversion_tool": getattr(act, "conversion_tool_key", None),
                "conversion_output": getattr(act, "conversion_output_extension", None),
            }

        try:
            planned = sum(1 for act in plan.actions if str(act.status).startswith("planned"))
            skipped = sum(1 for act in plan.actions if str(act.status).startswith("skipped"))
            errors = sum(1 for act in plan.actions if str(act.status).startswith("error"))
            converts = sum(1 for act in plan.actions if str(act.action) == "convert")
            renames = sum(1 for act in plan.actions if "rename" in str(act.status))
            self.summary_var.set(
                f"{planned} geplant | {converts} konvertieren | {renames} umbenennen | {skipped} übersprungen | {errors} Fehler"
            )
        except Exception:
            self.summary_var.set("-")

    def _populate_audit_table(self, report: ConversionAuditReport) -> None:
        self._clear_table()
        self._plan_row_iids = []
        self._set_details("")

        for item in report.items:
            suggestion = item.current_extension
            if item.recommended_extension and item.recommended_extension != item.current_extension:
                suggestion = f"{item.current_extension} -> {item.recommended_extension}".strip()

            action = "convert" if item.status == "should_convert" else "keep"
            status = item.status
            if item.reason:
                status = f"{status}: {item.reason}"

            iid = self.table.insert(
                "",
                tk.END,
                values=(
                    str(item.input_path or ""),
                    self._rom_display_name(item.input_path),
                    item.detected_system,
                    "",
                    "",
                    "",
                    suggestion,
                    action,
                    status,
                ),
            )
            self._row_meta[str(iid)] = {
                "current_extension": item.current_extension,
                "recommended_extension": item.recommended_extension,
                "rule_name": item.rule_name,
                "tool_key": item.tool_key,
                "status": item.status,
                "reason": item.reason,
            }

        try:
            totals = report.totals or {}
            summary_parts = [f"{key} {totals.get(key, 0)}" for key in sorted(totals.keys())]
            self.summary_var.set(" | ".join(summary_parts))
        except Exception:
            self.summary_var.set("-")

    def _append_summary_row(self, report: SortReport) -> None:
        text = (
            f"Processed: {report.processed} | Copied: {report.copied} | Moved: {report.moved} | "
            f"Skipped: {report.skipped} | Errors: {len(report.errors)} | Cancelled: {report.cancelled}"
        )
        self.table.insert(
            "",
            tk.END,
            values=("(Summary)", "", "", "", "", "", report.dest_path, report.mode, text),
        )

    def _start_op(
        self,
        op: str,
        *,
        start_index: int = 0,
        only_indices: Optional[list[int]] = None,
        resume_path: Optional[str] = None,
        conversion_mode: str = "all",
    ) -> None:
        validated = self._validate_paths(require_dest=op in ("plan", "execute"))
        if validated is None:
            return
        source, dest = validated

        try:
            self._append_log(f"Starting {op}…")
        except Exception:
            pass

        if op in ("plan", "execute") and self._scan_result is None:
            messagebox.showinfo("Keine Scan-Ergebnisse", "Bitte zuerst scannen.")
            return
        if op == "execute" and self._sort_plan is None:
            messagebox.showinfo("Kein Sortierplan", "Bitte zuerst Vorschau ausführen.")
            return

        self._cancel_token = CancelToken()
        self._set_running(True)

        mode = self.mode_var.get().strip() or "copy"
        on_conflict = self.conflict_var.get().strip() or "rename"

        if op == "execute" and resume_path is None:
            resume_path = self._resume_path

        def worker() -> None:
            try:
                if op == "scan":
                    self._queue.put(("phase", ("scan", 0)))
                    self._queue.put(("log", f"Scan started: source={source}"))
                    scan = run_scan(
                        source,
                        config=None,
                        progress_cb=lambda c, t: self._queue.put(("progress", (int(c), int(t)))),
                        log_cb=lambda msg: self._queue.put(("log", str(msg))),
                        cancel_token=self._cancel_token,
                    )
                    self._queue.put(("log", f"Scan finished: items={len(scan.items)} cancelled={scan.cancelled}"))
                    self._queue.put(("scan_done", scan))
                    return

                if op == "plan":
                    self._queue.put(("phase", ("plan", len(self._scan_result.items if self._scan_result else []))))
                    filtered_scan = self._get_filtered_scan_result()
                    self._queue.put(
                        (
                            "log",
                            f"Plan started: items={len(filtered_scan.items)} mode={mode} conflict={on_conflict}",
                        )
                    )
                    plan = plan_sort(
                        filtered_scan,
                        dest,
                        config=None,
                        mode=mode,
                        on_conflict=on_conflict,
                        cancel_token=self._cancel_token,
                    )
                    self._queue.put(("log", f"Plan finished: actions={len(plan.actions)}"))
                    self._queue.put(("plan_done", plan))
                    return

                if op == "execute":
                    total_actions = len(self._sort_plan.actions if self._sort_plan else [])
                    if only_indices:
                        filtered = [i for i in only_indices if 0 <= int(i) < total_actions]
                        total = len(set(filtered))
                    elif start_index > 0:
                        total = max(0, total_actions - int(start_index))
                    else:
                        total = total_actions
                    if conversion_mode != "all":
                        convert_count = sum(1 for action in self._sort_plan.actions if action.action == "convert")
                        if conversion_mode == "only":
                            total = convert_count
                        elif conversion_mode == "skip":
                            total = max(0, total_actions - convert_count)
                    self._queue.put(("phase", ("execute", total)))
                    self._queue.put(
                        (
                            "log",
                            f"Execute started: total={total} resume={start_index} only_indices={only_indices} conversion_mode={conversion_mode}",
                        )
                    )
                    report = execute_sort(
                        self._sort_plan,
                        progress_cb=lambda c, t: self._queue.put(("progress", (int(c), int(t)))),
                        log_cb=lambda msg: self._queue.put(("log", str(msg))),
                        action_status_cb=lambda i, status: self._queue.put(("row_status", (int(i), str(status)))),
                        cancel_token=self._cancel_token,
                        dry_run=False,
                        resume_path=resume_path,
                        start_index=start_index,
                        only_indices=only_indices,
                        conversion_mode=conversion_mode,
                    )
                    self._queue.put(
                        (
                            "log",
                            f"Execute finished: processed={report.processed} copied={report.copied} moved={report.moved} errors={len(report.errors)} cancelled={report.cancelled}",
                        )
                    )
                    self._queue.put(("exec_done", report))
                    return

                if op == "audit":
                    self._queue.put(("phase", ("audit", 0)))
                    self._queue.put(("log", f"Audit started: source={source}"))
                    report = audit_conversion_candidates(
                        source,
                        config=None,
                        progress_cb=lambda c, t: self._queue.put(("progress", (int(c), int(t)))),
                        log_cb=lambda msg: self._queue.put(("log", str(msg))),
                        cancel_token=self._cancel_token,
                        include_disabled=True,
                    )
                    self._queue.put(("log", f"Audit finished: items={len(report.items)} cancelled={report.cancelled}"))
                    self._queue.put(("audit_done", report))
                    return

                raise RuntimeError(f"Unknown operation: {op}")

            except Exception as exc:
                self._queue.put(("error", (str(exc), traceback.format_exc())))

        self._worker_thread = threading.Thread(target=worker, daemon=True)
        self._worker_thread.start()

    def _start_scan(self) -> None:
        self.log_text.delete("1.0", tk.END)
        self.progress.configure(mode="determinate", maximum=100, value=0)
        self.status_var.set("Scan startet…")
        self.dat_status_var.set("DAT: -")
        self._failed_action_indices.clear()
        self._audit_report = None
        self._update_resume_buttons()
        self._scan_result = None
        self._sort_plan = None
        self._clear_table()
        self._set_details("")
        self._start_op("scan")

    def _start_preview(self) -> None:
        self.progress.configure(mode="determinate", maximum=1, value=0)
        self.status_var.set("Plane…")
        self._failed_action_indices.clear()
        self._audit_report = None
        self._update_resume_buttons()
        self._start_op("plan")

    def _start_execute(self) -> None:
        self.progress.configure(mode="determinate", maximum=1, value=0)
        self.status_var.set("Ausführen…")
        self._failed_action_indices.clear()
        self._audit_report = None
        self._update_resume_buttons()
        self._start_op("execute", conversion_mode="skip")

    def _start_convert_only(self) -> None:
        self.progress.configure(mode="determinate", maximum=1, value=0)
        self.status_var.set("Konvertiere…")
        self._failed_action_indices.clear()
        self._audit_report = None
        self._update_resume_buttons()
        self._start_op("execute", conversion_mode="only")

    def _start_audit(self) -> None:
        self.progress.configure(mode="determinate", maximum=1, value=0)
        self.status_var.set("Checking conversions…")
        self._failed_action_indices.clear()
        self._audit_report = None
        self._update_resume_buttons()
        self._start_op("audit")

    def _audit_report_to_dict(self, report: ConversionAuditReport) -> dict:
        return audit_report_to_dict(report)

    def _scan_report_to_dict(self, scan: ScanResult) -> dict:
        return scan_report_to_dict(scan)

    def _plan_report_to_dict(self, plan: SortPlan) -> dict:
        return plan_report_to_dict(plan)

    def _export_scan_json(self) -> None:
        scan = self._scan_result
        if scan is None:
            messagebox.showinfo("Kein Scan", "Bitte zuerst scannen.")
            return
        filename = filedialog.asksaveasfilename(
            title="Save Scan JSON",
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
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
            messagebox.showinfo("Kein Scan", "Bitte zuerst scannen.")
            return
        filename = filedialog.asksaveasfilename(
            title="Save Scan CSV",
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not filename:
            return
        self._run_export_task("Scan CSV", lambda: write_scan_csv(scan, filename))

    def _export_plan_json(self) -> None:
        plan = self._sort_plan
        if plan is None:
            messagebox.showinfo("Kein Plan", "Bitte zuerst Vorschau ausführen.")
            return
        filename = filedialog.asksaveasfilename(
            title="Save Plan JSON",
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
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
            messagebox.showinfo("Kein Plan", "Bitte zuerst Vorschau ausführen.")
            return
        filename = filedialog.asksaveasfilename(
            title="Save Plan CSV",
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not filename:
            return
        self._run_export_task("Plan CSV", lambda: write_plan_csv(plan, filename))

    def _export_audit_json(self) -> None:
        report = self._audit_report
        if report is None:
            messagebox.showinfo("Kein Audit", "Bitte zuerst Konvertierungen prüfen.")
            return
        filename = filedialog.asksaveasfilename(
            title="Save Audit JSON",
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
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
            messagebox.showinfo("Kein Audit", "Bitte zuerst Konvertierungen prüfen.")
            return
        filename = filedialog.asksaveasfilename(
            title="Save Audit CSV",
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not filename:
            return
        self._run_export_task("Audit CSV", lambda: write_audit_csv(report, filename))

    def _run_export_task(self, label: str, task) -> None:
        def _worker():
            try:
                task()
                self._queue.put(("export_done", label))
            except Exception as exc:
                self._queue.put(("export_error", str(exc)))

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def _start_resume(self) -> None:
        if not self._can_resume():
            messagebox.showinfo("Kein Fortsetzen möglich", "Kein Fortsetzungsstand gefunden.")
            return
        try:
            state = load_sort_resume_state(self._resume_path)
        except Exception as exc:
            messagebox.showwarning("Fortsetzen fehlgeschlagen", f"Fortsetzungsstand konnte nicht geladen werden: {exc}")
            return
        self._sort_plan = state.sort_plan
        self._populate_plan_table(state.sort_plan)
        self.progress.configure(mode="determinate", maximum=1, value=0)
        self.status_var.set("Ausführen…")
        self._failed_action_indices.clear()
        self._update_resume_buttons()
        self._start_op("execute", start_index=state.resume_from_index)

    def _start_retry_failed(self) -> None:
        if not self._can_retry_failed():
            messagebox.showinfo("Keine fehlgeschlagenen Aktionen", "Es gibt keine fehlgeschlagenen Aktionen zum Wiederholen.")
            return
        indices = sorted(self._failed_action_indices)
        self._failed_action_indices.clear()
        self._update_resume_buttons()
        self.progress.configure(mode="determinate", maximum=1, value=0)
        self.status_var.set("Ausführen…")
        self._start_op("execute", only_indices=indices)

    def _cancel(self) -> None:
        self._append_log("Cancel requested by user")
        self._cancel_token.cancel()
        self.btn_cancel.configure(state="disabled")

    def _poll_queue(self) -> None:
        try:
            while True:
                event, payload = self._queue.get_nowait()
                if event == "log":
                    self._append_log(str(payload))
                elif event == "dat":
                    self.dat_status_var.set(str(payload))
                elif event == "phase":
                    phase, total = payload
                    if phase == "scan":
                        self.status_var.set("Scanning…")
                        self.progress.configure(mode="determinate", maximum=100, value=0)
                    elif phase == "plan":
                        self.status_var.set("Plane…")
                        self.progress.configure(mode="determinate", maximum=max(1, int(total)), value=0)
                    elif phase == "execute":
                        self.status_var.set("Ausführen…")
                        self.progress.configure(mode="determinate", maximum=max(1, int(total)), value=0)
                    elif phase == "audit":
                        self.status_var.set("Checking conversions…")
                        self.progress.configure(mode="determinate", maximum=max(1, int(total)), value=0)
                elif event == "progress":
                    current, total = payload
                    if total and total > 0:
                        self.progress.configure(mode="determinate", maximum=int(total), value=int(current))
                    else:
                        self.progress.configure(mode="indeterminate")
                        self.progress.start(20)
                elif event == "row_status":
                    row_index, status = payload
                    try:
                        row = int(row_index)
                        if row < 0 or row >= len(self._plan_row_iids):
                            continue
                        iid = self._plan_row_iids[row]
                        self.table.set(iid, "status", str(status))
                        if str(status).lower().startswith("error"):
                            self._failed_action_indices.add(row)
                            self._update_resume_buttons()
                    except Exception:
                        continue
                elif event == "scan_done":
                    scan = payload
                    self._scan_result = scan
                    self._refresh_filter_options()
                    self._populate_scan_table(self._get_filtered_scan_result())
                    self._set_running(False)
                    if scan.cancelled:
                        self.status_var.set("Cancelled")
                        messagebox.showinfo("Abgebrochen", "Scan abgebrochen.")
                    else:
                        self.status_var.set("Scan done")
                        messagebox.showinfo("Scan abgeschlossen", f"ROMs gefunden: {len(scan.items)}")
                elif event == "plan_done":
                    plan = payload
                    self._sort_plan = plan
                    self._populate_plan_table(plan)
                    self._set_running(False)
                    self.status_var.set("Plan ready")
                    messagebox.showinfo("Vorschau bereit", f"Geplante Aktionen: {len(plan.actions)}")
                elif event == "exec_done":
                    report: SortReport = payload
                    self._set_running(False)
                    # Add summary row after execution, so row-index updates remain aligned.
                    self._append_summary_row(report)
                    self._update_resume_buttons()
                    if report.cancelled:
                        self.status_var.set("Cancelled")
                        messagebox.showinfo("Abgebrochen", "Vorgang abgebrochen.")
                    else:
                        self.status_var.set("Done")
                        messagebox.showinfo(
                            "Fertig",
                            f"Fertig. Kopiert: {report.copied}, Verschoben: {report.moved}\nFehler: {len(report.errors)}\n\nSiehe Log für Details.",
                        )
                elif event == "audit_done":
                    report: ConversionAuditReport = payload
                    self._set_running(False)
                    self._audit_report = report
                    self._populate_audit_table(report)
                    self._update_resume_buttons()
                    if report.cancelled:
                        self.status_var.set("Cancelled")
                        messagebox.showinfo("Abgebrochen", "Audit abgebrochen.")
                    else:
                        self.status_var.set("Audit ready")
                        messagebox.showinfo("Audit abgeschlossen", f"Geprüft: {len(report.items)}")
                elif event == "dat_index_done":
                    result = payload
                    self._dat_index_thread = None
                    self._dat_index_cancel_token = None
                    try:
                        self.btn_refresh_dat.configure(state="normal")
                        if hasattr(self, "btn_cancel_dat"):
                            self.btn_cancel_dat.configure(state="disabled")
                    except Exception:
                        pass
                    self.dat_status_var.set(f"DAT: Index fertig ({result})")
                elif event == "dat_index_error":
                    message = str(payload)
                    self._dat_index_thread = None
                    self._dat_index_cancel_token = None
                    try:
                        self.btn_refresh_dat.configure(state="normal")
                        if hasattr(self, "btn_cancel_dat"):
                            self.btn_cancel_dat.configure(state="disabled")
                    except Exception:
                        pass
                    self.dat_status_var.set(f"DAT: Index fehlgeschlagen ({message})")
                    messagebox.showerror("DAT", f"DAT-Index fehlgeschlagen: {message}")
                elif event == "igir_plan_done":
                    result = payload
                    self._set_igir_running(False)
                    self._igir_thread = None
                    try:
                        if getattr(result, "stdout", ""):
                            self._append_log(f"[IGIR] {result.stdout}")
                        if getattr(result, "stderr", ""):
                            self._append_log(f"[IGIR] {result.stderr}")
                    except Exception:
                        pass
                    if getattr(result, "cancelled", False):
                        self._igir_plan_ready = False
                        self._update_igir_buttons()
                        self.igir_status_var.set("IGIR Plan abgebrochen")
                        messagebox.showinfo("IGIR", "IGIR Plan abgebrochen.")
                    elif getattr(result, "ok", False):
                        self._igir_plan_ready = True
                        self._update_igir_buttons()
                        self.igir_status_var.set("IGIR Plan fertig")
                        messagebox.showinfo("IGIR", "IGIR Plan abgeschlossen. Diff exportiert.")
                    else:
                        self._igir_plan_ready = False
                        self._update_igir_buttons()
                        self.igir_status_var.set("IGIR Plan fehlgeschlagen")
                        messagebox.showwarning("IGIR", f"IGIR Plan fehlgeschlagen: {getattr(result, 'message', 'Fehler')}")
                elif event == "igir_execute_done":
                    result = payload
                    self._set_igir_running(False)
                    self._igir_thread = None
                    try:
                        if getattr(result, "raw_output", ""):
                            self._append_log(f"[IGIR] {result.raw_output}")
                    except Exception:
                        pass
                    if getattr(result, "cancelled", False):
                        self.igir_status_var.set("IGIR Execute abgebrochen")
                        messagebox.showinfo("IGIR", "IGIR Execute abgebrochen.")
                    elif getattr(result, "success", False):
                        self.igir_status_var.set("IGIR Execute fertig")
                        messagebox.showinfo("IGIR", "IGIR Execute abgeschlossen.")
                    else:
                        self.igir_status_var.set("IGIR Execute fehlgeschlagen")
                        messagebox.showwarning("IGIR", f"IGIR Execute fehlgeschlagen: {getattr(result, 'message', 'Fehler')}")
                elif event == "igir_error":
                    self._set_igir_running(False)
                    self._igir_thread = None
                    if isinstance(payload, tuple):
                        msg, tb = payload
                        self._append_log(str(msg))
                        self._append_log(str(tb))
                        self.igir_status_var.set("IGIR Fehler")
                        messagebox.showerror("IGIR", f"{msg}\n\n{tb}")
                    else:
                        result = payload
                        self.igir_status_var.set("IGIR Fehler")
                        try:
                            if getattr(result, "raw_output", ""):
                                self._append_log(f"[IGIR] {result.raw_output}")
                        except Exception:
                            pass
                        messagebox.showerror("IGIR", f"IGIR Fehler: {getattr(result, 'message', 'Unbekannt')}" )
                elif event == "export_done":
                    label = str(payload)
                    messagebox.showinfo("Export abgeschlossen", f"{label} gespeichert.")
                elif event == "export_error":
                    messagebox.showwarning("Export fehlgeschlagen", str(payload))
                elif event == "error":
                    msg, tb = payload
                    self._append_log(msg)
                    self._append_log(tb)
                    self.status_var.set("Error")
                    self.dat_status_var.set("DAT: -")
                    self._set_running(False)
                    messagebox.showerror("Arbeitsfehler", f"{msg}\n\n{tb}")
        except Empty:
            pass
        finally:
            self.root.after(50, self._poll_queue)

    def run(self) -> int:
        self.root.mainloop()
        return 0


class _TkLogHandler(logging.Handler):
    def __init__(self, app: "TkMVPApp") -> None:
        super().__init__()
        self._app = app
        self._last_message = ""
        self._last_ts = 0.0

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
            self._app.root.after(0, self._app._append_log, msg)
        except Exception:
            return


def run() -> int:
    init_drag_drop()
    app = TkMVPApp()
    return app.run()
