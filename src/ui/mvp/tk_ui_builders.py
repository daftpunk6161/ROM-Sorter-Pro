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


@dataclass(frozen=True)
class StatusUI:
    frame: Any
    status_var: Any
    progress: Any


@dataclass(frozen=True)
class ResultsTableUI:
    frame: Any
    tree: Any


@dataclass(frozen=True)
class LogUI:
    frame: Any
    log_text: Any


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

    ttk.Label(frame, text=f"{translate('dest')}:" ).grid(row=1, column=0, sticky="w")
    dest_var = tk.StringVar()
    dest_entry = ttk.Entry(frame, textvariable=dest_var)
    dest_entry.grid(row=1, column=1, sticky="ew", padx=6)
    btn_dest = ttk.Button(frame, text=translate("choose_dest"), command=choose_dest)
    btn_dest.grid(row=1, column=2)

    frame.columnconfigure(1, weight=1)

    return PathsUI(
        frame=frame,
        source_var=source_var,
        source_entry=source_entry,
        dest_var=dest_var,
        dest_entry=dest_entry,
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
    btn_scan.pack(side="left", padx=4)
    btn_preview.pack(side="left", padx=4)
    btn_execute.pack(side="left", padx=4)
    btn_cancel.pack(side="left", padx=4)
    btn_cancel.state(["disabled"])

    return ActionsUI(
        frame=frame,
        mode_var=mode_var,
        conflict_var=conflict_var,
        btn_scan=btn_scan,
        btn_preview=btn_preview,
        btn_execute=btn_execute,
        btn_cancel=btn_cancel,
    )


def build_status_ui(ttk, tk, parent) -> StatusUI:
    frame = ttk.LabelFrame(parent, text=translate("status"), padding=8)
    frame.pack(fill="x", pady=(0, 8))
    status_var = tk.StringVar(value=translate("ready"))
    ttk.Label(frame, textvariable=status_var).pack(side="left")
    progress = ttk.Progressbar(frame, orient=tk.HORIZONTAL, mode="determinate")
    progress.pack(side="right", fill="x", expand=True)
    return StatusUI(frame=frame, status_var=status_var, progress=progress)


def build_results_table_ui(ttk, tk, parent) -> ResultsTableUI:
    frame = ttk.LabelFrame(parent, text=translate("results"), padding=8)
    frame.pack(fill="both", expand=True)
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
    return ResultsTableUI(frame=frame, tree=tree)


def build_log_ui(ttk, tk, parent) -> LogUI:
    frame = ttk.LabelFrame(parent, text=translate("log"), padding=8)
    frame.pack(fill="both", expand=False)
    log_text = tk.Text(frame, height=8)
    log_text.pack(fill="both", expand=True)
    return LogUI(frame=frame, log_text=log_text)