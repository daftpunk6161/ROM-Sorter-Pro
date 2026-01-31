from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..i18n import translate


@dataclass(frozen=True)
class PathsUI:
    frame: Any
    source_var: Any
    source_entry: Any
    dest_var: Any
    dest_entry: Any
    recent_source_combo: Any
    recent_dest_combo: Any
    btn_source: Any
    btn_dest: Any


@dataclass(frozen=True)
class ActionsUI:
    frame: Any
    mode_var: Any
    conflict_var: Any
    btn_scan: Any
    btn_preview: Any
    btn_execute: Any
    btn_cancel: Any
    btn_rule_tester: Any
    copy_first_var: Any
    btn_rename_builder: Any
    rename_template_var: Any
    rename_template_entry: Any


@dataclass(frozen=True)
class StatusUI:
    frame: Any
    status_var: Any
    summary_var: Any
    progress: Any


@dataclass(frozen=True)
class ResultsTableUI:
    frame: Any
    tree: Any
    btn_structure: Any
    btn_plan_undo: Any
    btn_plan_redo: Any
    btn_execute_selected: Any
    btn_bulk_override: Any
    btn_action_override: Any


@dataclass(frozen=True)
class LogUI:
    frame: Any
    log_text: Any
    log_filter_var: Any
    log_filter_entry: Any
    log_filter_clear_btn: Any
    log_level_combo: Any


def build_header_ui(ttk, parent, version: str) -> Any:
    header = ttk.Frame(parent)
    header.pack(fill="x", pady=(0, 8))
    ttk.Label(header, text="ROM Sorter Pro", font=("Segoe UI", 16, "bold")).pack(side="left")
    ttk.Label(header, text=f"v{version}").pack(side="left", padx=(6, 0))
    return header


def build_paths_ui(ttk, tk, parent, choose_source, choose_dest) -> PathsUI:
    frame = ttk.LabelFrame(parent, text=translate("paths"), padding=8)
    frame.pack(fill="x", pady=(0, 8))

    ttk.Label(frame, text=f"{translate('source')}:" ).grid(row=0, column=0, sticky="w")
    source_var = tk.StringVar()
    source_entry = ttk.Entry(frame, textvariable=source_var)
    source_entry.grid(row=0, column=1, sticky="ew", padx=6)
    btn_source = ttk.Button(frame, text=translate("choose_source"), command=choose_source)
    btn_source.grid(row=0, column=2)

    recent_source_combo = ttk.Combobox(frame, state="readonly", values=("-",))
    recent_source_combo.grid(row=0, column=3, sticky="ew", padx=(6, 0))

    ttk.Label(frame, text=f"{translate('dest')}:" ).grid(row=1, column=0, sticky="w")
    dest_var = tk.StringVar()
    dest_entry = ttk.Entry(frame, textvariable=dest_var)
    dest_entry.grid(row=1, column=1, sticky="ew", padx=6)
    btn_dest = ttk.Button(frame, text=translate("choose_dest"), command=choose_dest)
    btn_dest.grid(row=1, column=2)

    recent_dest_combo = ttk.Combobox(frame, state="readonly", values=("-",))
    recent_dest_combo.grid(row=1, column=3, sticky="ew", padx=(6, 0))

    frame.columnconfigure(1, weight=1)
    frame.columnconfigure(3, weight=1)

    return PathsUI(
        frame=frame,
        source_var=source_var,
        source_entry=source_entry,
        dest_var=dest_var,
        dest_entry=dest_entry,
        recent_source_combo=recent_source_combo,
        recent_dest_combo=recent_dest_combo,
        btn_source=btn_source,
        btn_dest=btn_dest,
    )


def build_actions_ui(ttk, tk, parent, on_scan, on_preview, on_execute, on_cancel) -> ActionsUI:
    frame = ttk.LabelFrame(parent, text=translate("actions"), padding=8)
    frame.pack(fill="x", pady=(0, 8))

    mode_var = tk.StringVar(value="copy")
    ttk.Label(frame, text=f"{translate('mode')}:" ).grid(row=0, column=0, sticky="w")
    ttk.OptionMenu(frame, mode_var, "copy", "copy", "move").grid(row=0, column=1, sticky="w")

    conflict_var = tk.StringVar(value="rename")
    ttk.Label(frame, text=f"{translate('conflicts')}:" ).grid(row=0, column=2, sticky="w", padx=(12, 0))
    ttk.OptionMenu(frame, conflict_var, "rename", "rename", "skip", "overwrite").grid(
        row=0, column=3, sticky="w"
    )

    btn_row = ttk.Frame(frame)
    btn_row.grid(row=1, column=0, columnspan=4, pady=(6, 0))
    btn_scan = ttk.Button(btn_row, text=translate("scan"), command=on_scan)
    btn_preview = ttk.Button(btn_row, text=translate("preview_sort"), command=on_preview)
    btn_execute = ttk.Button(btn_row, text=translate("execute_sort"), command=on_execute)
    btn_cancel = ttk.Button(btn_row, text=translate("cancel"), command=on_cancel)
    btn_rule_tester = ttk.Button(btn_row, text="Regel-Tester")
    btn_scan.pack(side="left", padx=4)
    btn_preview.pack(side="left", padx=4)
    btn_execute.pack(side="left", padx=4)
    btn_cancel.pack(side="left", padx=4)
    btn_rule_tester.pack(side="left", padx=4)
    btn_cancel.state(["disabled"])

    options_row = ttk.Frame(frame)
    options_row.grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))
    copy_first_var = tk.BooleanVar(value=False)
    chk_copy_first = ttk.Checkbutton(options_row, text="Copy-first Staging", variable=copy_first_var)
    btn_rename_builder = ttk.Button(options_row, text="Rename Pattern…")
    chk_copy_first.pack(side="left")
    btn_rename_builder.pack(side="left", padx=(8, 0))

    template_row = ttk.Frame(frame)
    template_row.grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 0))
    ttk.Label(template_row, text="Rename Template:").pack(side="left")
    rename_template_var = tk.StringVar(value="")
    rename_template_entry = ttk.Entry(template_row, textvariable=rename_template_var, width=40)
    rename_template_entry.pack(side="left", padx=(6, 0))

    return ActionsUI(
        frame=frame,
        mode_var=mode_var,
        conflict_var=conflict_var,
        btn_scan=btn_scan,
        btn_preview=btn_preview,
        btn_execute=btn_execute,
        btn_cancel=btn_cancel,
        btn_rule_tester=btn_rule_tester,
        copy_first_var=copy_first_var,
        btn_rename_builder=btn_rename_builder,
        rename_template_var=rename_template_var,
        rename_template_entry=rename_template_entry,
    )


def build_status_ui(ttk, tk, parent) -> StatusUI:
    frame = ttk.LabelFrame(parent, text=translate("status"), padding=8)
    frame.pack(fill="x", pady=(0, 8))
    status_var = tk.StringVar(value=translate("ready"))
    ttk.Label(frame, textvariable=status_var).pack(side="left")
    summary_var = tk.StringVar(value="-")
    ttk.Label(frame, textvariable=summary_var).pack(side="left", padx=(8, 0))
    progress = ttk.Progressbar(frame, orient=tk.HORIZONTAL, mode="determinate")
    progress.pack(side="right", fill="x", expand=True)
    return StatusUI(frame=frame, status_var=status_var, summary_var=summary_var, progress=progress)


def build_results_table_ui(ttk, tk, parent) -> ResultsTableUI:
    frame = ttk.LabelFrame(parent, text=translate("results"), padding=8)
    frame.pack(fill="both", expand=True)
    toolbar = ttk.Frame(frame)
    toolbar.pack(fill="x", pady=(0, 6))
    btn_structure = ttk.Button(toolbar, text="Zielstruktur anzeigen")
    btn_structure.pack(side="left")
    btn_plan_undo = ttk.Button(toolbar, text="Plan Undo")
    btn_plan_undo.pack(side="left", padx=(6, 0))
    btn_plan_redo = ttk.Button(toolbar, text="Plan Redo")
    btn_plan_redo.pack(side="left", padx=(6, 0))
    btn_execute_selected = ttk.Button(toolbar, text="Auswahl ausführen")
    btn_execute_selected.pack(side="left", padx=(6, 0))
    btn_bulk_override = ttk.Button(toolbar, text="Mehrfach überschreiben")
    btn_bulk_override.pack(side="left", padx=(6, 0))
    btn_action_override = ttk.Button(toolbar, text="Aktion override")
    btn_action_override.pack(side="left", padx=(6, 0))
    tree = ttk.Treeview(
        frame,
        columns=("input", "system", "target", "action", "status"),
        show="headings",
    )
    tree.heading("input", text="InputPath")
    tree.heading("system", text="DetectedConsole/Type")
    tree.heading("target", text="PlannedTargetPath")
    tree.heading("action", text="Action")
    tree.heading("status", text="Status/Error")
    tree.column("input", width=280, anchor="w")
    tree.column("system", width=160, anchor="w")
    tree.column("target", width=280, anchor="w")
    tree.column("action", width=90, anchor="w")
    tree.column("status", width=200, anchor="w")
    tree.pack(fill="both", expand=True)
    return ResultsTableUI(
        frame=frame,
        tree=tree,
        btn_structure=btn_structure,
        btn_plan_undo=btn_plan_undo,
        btn_plan_redo=btn_plan_redo,
        btn_execute_selected=btn_execute_selected,
        btn_bulk_override=btn_bulk_override,
        btn_action_override=btn_action_override,
    )


def build_log_ui(ttk, tk, parent) -> LogUI:
    frame = ttk.LabelFrame(parent, text=translate("log"), padding=8)
    frame.pack(fill="both", expand=False)
    header = ttk.Frame(frame)
    header.pack(fill="x", pady=(0, 4))
    log_filter_var = tk.StringVar(value="")
    log_filter_entry = ttk.Entry(header, textvariable=log_filter_var, width=24)
    log_filter_entry.pack(side="left", padx=(0, 6))
    log_filter_clear_btn = ttk.Button(header, text="Filter löschen")
    log_filter_clear_btn.pack(side="left")
    log_level_combo = ttk.Combobox(header, state="readonly", values=("Alle", "Info", "Warnung", "Fehler", "Debug"))
    log_level_combo.set("Alle")
    log_level_combo.pack(side="left", padx=(6, 0))
    log_text = tk.Text(frame, height=8)
    log_text.pack(fill="both", expand=True)
    return LogUI(
        frame=frame,
        log_text=log_text,
        log_filter_var=log_filter_var,
        log_filter_entry=log_filter_entry,
        log_filter_clear_btn=log_filter_clear_btn,
        log_level_combo=log_level_combo,
    )