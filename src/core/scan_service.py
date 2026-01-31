"""ROM Sorter Pro - scan service."""

from __future__ import annotations

import threading
import time
import os
import cProfile
import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from ..config import Config, load_config
from ..security.security_utils import is_valid_directory, sanitize_path
from ..scanning.high_performance_scanner import HighPerformanceScanner

ProgressCallback = Callable[[int, int], None]
LogCallback = Callable[[str], None]
StatusCallback = Callable[[str], None]


def _log(on_log: Optional[LogCallback], message: str) -> None:
    if on_log is not None:
        on_log(message)


def _status(on_status: Optional[StatusCallback], message: str) -> None:
    if on_status is not None:
        on_status(message)


def run_scan(
    source: str,
    config: Optional[Config] = None,
    on_progress: Optional[ProgressCallback] = None,
    on_log: Optional[LogCallback] = None,
    on_status: Optional[StatusCallback] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Dict[str, Any]:
    """Scan a source directory and return discovered ROM metadata.

    Returns:
        {
          "source": str,
          "roms": List[Dict[str, Any]],
          "stats": Dict[str, Any],
          "cancelled": bool,
        }
    """

    profiler = None
    if os.getenv("ROM_SORTER_PROFILE") == "1":
        profiler = cProfile.Profile()
        profiler.enable()

    source_sanitized = sanitize_path(str(source or ""))
    if not source_sanitized:
        raise ValueError("Source directory is empty")

    if not is_valid_directory(source_sanitized, must_exist=True):
        raise ValueError(f"Invalid source directory: {source_sanitized}")

    if config is None:
        try:
            cfg = load_config()
        except Exception:
            cfg = Config()
    else:
        cfg = config

    roms: list[Dict[str, Any]] = []
    stats_holder: Dict[str, Any] = {}
    done = threading.Event()
    error_holder: list[BaseException] = []
    start_time = time.perf_counter()
    last_progress_log = 0

    scanner = HighPerformanceScanner(cfg)

    incremental_cfg = {}
    try:
        incremental_cfg = (cfg.get("features", {}) or {}).get("scan", {}) or {}
    except Exception:
        incremental_cfg = {}
    incremental_enabled = bool(incremental_cfg.get("incremental", False))

    resume_cfg = {}
    try:
        resume_cfg = (cfg.get("features", {}) or {}).get("progress_persistence", {}) or {}
    except Exception:
        resume_cfg = {}
    resume_path = resume_cfg.get("scan_resume_path") or os.path.join("cache", "last_scan_resume.json")

    if incremental_enabled and resume_path:
        try:
            resume_file = Path(str(resume_path))
            if resume_file.exists():
                payload = json.loads(resume_file.read_text(encoding="utf-8"))
                if str(payload.get("source_path")) == str(source_sanitized):
                    items = payload.get("items") or []
                    seeded = 0
                    for item in items:
                        input_path = str(item.get("input_path") or "")
                        if not input_path:
                            continue
                        path_obj = Path(input_path)
                        if not path_obj.exists():
                            continue
                        raw = item.get("raw") if isinstance(item, dict) else None
                        rom_info = dict(raw) if isinstance(raw, dict) else {}
                        rom_info.setdefault("path", input_path)
                        rom_info.setdefault("name", path_obj.name)
                        rom_info.setdefault("system", item.get("detected_system") or "Unknown")
                        rom_info.setdefault("detection_confidence", item.get("detection_confidence"))
                        rom_info.setdefault("detection_source", item.get("detection_source"))
                        try:
                            stat = path_obj.stat()
                            rom_info.setdefault("last_modified", stat.st_mtime)
                            rom_info.setdefault("size", stat.st_size)
                        except Exception:
                            pass
                        try:
                            scanner._save_to_cache(input_path, rom_info)
                            seeded += 1
                        except Exception:
                            continue
                    _log(on_log, f"Incremental scan cache seeded: {seeded} entries")
        except Exception as exc:
            _log(on_log, f"Incremental scan cache seed failed: {exc}")

    # DAT status (best-effort). Prefer new dats config, keep legacy dat_matching gate.
    dat_cfg = {}
    legacy_dat_cfg = {}
    try:
        dat_cfg = cfg.get("dats", {}) or {}
    except Exception:
        dat_cfg = {}
    try:
        legacy_dat_cfg = cfg.get("dat_matching", {}) or {}
    except Exception:
        legacy_dat_cfg = {}
    legacy_enabled = bool(legacy_dat_cfg.get("enabled", True))
    dat_enabled = bool(dat_cfg or legacy_dat_cfg) and legacy_enabled

    dat_index = None
    dat_index_path = None
    if dat_enabled:
        try:
            dat_index = scanner._get_dat_index()
        except Exception:
            dat_index = None
        try:
            dat_index_path = dat_cfg.get("index_path") or os.path.join("data", "index", "romsorter_dat_index.sqlite")
        except Exception:
            dat_index_path = None

    def _format_dat_status() -> str:
        if not dat_enabled:
            return "DAT: disabled"
        if dat_index is not None:
            return "DAT: index loaded"
        if dat_index_path and Path(str(dat_index_path)).exists():
            return "DAT: index vorhanden"
        return "DAT: index fehlt"

    def on_file_found(path: str) -> None:
        if cancel_event is not None and cancel_event.is_set():
            try:
                scanner.stop()
            except Exception:
                pass
            return
        _log(on_log, f"Found file: {path}")

    def on_rom_found(rom_info: Dict[str, Any]) -> None:
        if cancel_event is not None and cancel_event.is_set():
            try:
                scanner.stop()
            except Exception:
                pass
            return
        roms.append(rom_info)
        name = rom_info.get("name") or Path(rom_info.get("path", "")).name
        system = rom_info.get("system", "Unknown")
        source = rom_info.get("detection_source")
        source_label_map = {
            "conflict-group": "Konfliktgruppe",
            "ambiguous-candidates": "Uneindeutige Kandidaten",
            "contradiction-candidates": "Widersprüchliche Kandidaten",
            "policy-low-confidence": "Niedrige Sicherheit",
            "extension": "Erweiterung",
            "extension-unique": "Erweiterung (eindeutig)",
            "override": "Override",
        }
        conf = rom_info.get("detection_confidence")
        details = []
        if isinstance(conf, (int, float)):
            details.append(f"{int(conf * 100)}%")
        if source:
            details.append(str(source_label_map.get(str(source), source)))
        suffix = f" [{' / '.join(details)}]" if details else ""
        _log(on_log, f"ROM: {name} ({system}){suffix}")

    def on_progress_cb(current: int, total: int) -> None:
        if on_progress is not None:
            on_progress(int(current), int(total))
        nonlocal last_progress_log
        if current and current % 1000 == 0 and current != last_progress_log:
            last_progress_log = current
            _log(on_log, f"Scan progress: {current}/{total} files")

    def on_complete_cb(stats: Dict[str, Any]) -> None:
        stats_holder.update(stats or {})
        done.set()

    def on_error_cb(error: str) -> None:
        error_holder.append(RuntimeError(error))
        done.set()

    scanner.on_file_found = on_file_found
    scanner.on_rom_found = on_rom_found
    scanner.on_progress = on_progress_cb
    scanner.on_complete = on_complete_cb
    scanner.on_error = on_error_cb

    _log(on_log, f"Starting scan: {source_sanitized}")
    _status(on_status, _format_dat_status())
    started = scanner.scan(source_sanitized, recursive=True)
    if not started:
        raise RuntimeError("Scan could not be started")

    cancelled = False

    last_dat_status: Optional[str] = None
    last_dat_check = 0.0

    while scanner.is_running and not done.is_set():
        if cancel_event is not None and cancel_event.is_set():
            cancelled = True
            _log(on_log, "Cancellation requested. Stopping scan…")
            scanner.stop()

        # Refresh DAT status occasionally (avoid spamming the UI).
        now = time.time()
        if on_status is not None and (now - last_dat_check) >= 0.25:
            last_dat_check = now
            current_status = _format_dat_status()
            if current_status != last_dat_status:
                last_dat_status = current_status
                _status(on_status, current_status)
        time.sleep(0.05)

    # Ensure completion callback has been processed
    done.wait(timeout=2.0)

    if error_holder:
        raise error_holder[0]

    duration = time.perf_counter() - start_time
    total_files = int(stats_holder.get("total_files", 0) or 0)
    stats_holder.setdefault("rom_count", len(roms))
    stats_holder.setdefault("duration_seconds", round(duration, 3))
    if duration > 0 and total_files:
        stats_holder.setdefault("files_per_second", round(total_files / duration, 2))

    throughput = f", {stats_holder['files_per_second']} files/s" if "files_per_second" in stats_holder else ""
    _log(
        on_log,
        f"Scan finished. ROMs found: {len(roms)} in {duration:.2f}s{throughput}",
    )

    result = {
        "source": source_sanitized,
        "roms": roms,
        "stats": stats_holder,
        "cancelled": cancelled,
    }

    if profiler is not None:
        profiler.disable()
        try:
            override = os.getenv("ROM_SORTER_PROFILE_PATH", "").strip()
            if override:
                output_path = Path(override)
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                cache_dir = Path(os.getcwd()) / "cache" / "logs"
                cache_dir.mkdir(parents=True, exist_ok=True)
                output_path = cache_dir / f"scan_profile_{int(time.time())}.prof"
            profiler.dump_stats(str(output_path))
            _log(on_log, f"Profile saved: {output_path}")
        except Exception:
            pass

    return result
