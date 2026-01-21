#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""Rom Sarter Pro -High -performance scanner V2.1.8 Phase 1 implementation: Desktop Optimization This module Implements A High -performance scanner for rome files with Advanced Thread Management, Optimized Memory Usage, and Enhanced Error Handling. Features: - Multi -Threading for Maximum CPU Utilization - Advanced Processing for Optimal Performance - Intelligent Chunking of Large Files Files for Reduced Memory Usage - Robust Error Handling With Recovery Capabilities - Adaptive Scanning for Different Systems - Support for Delayed and Incremental Processing.

Notes:
- Thread count and chunk size are derived from config (scanner/performance.processing).
- Progress updates are throttled when batching is enabled.
- In-memory cache avoids repeated work within a scan session.
"""

import os
import sys
import time
import hashlib
import logging
import threading
import queue
import zipfile
import concurrent.futures
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Callable, Union, Any, Generator, TypeVar

# Define the type alias for the config class
ConfigType = TypeVar('ConfigType')

# Local imports
from ..exceptions import ScannerError
from ..config import Config

# Set up logging
logger = logging.getLogger(__name__)

# Constants
MAX_WORKERS = os.cpu_count() or 4  # Fallback auf 4 Threads
DEFAULT_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB for file chunking

# Archive types are handled separately (ROM detection happens on extracted content in future work).
ARCHIVE_EXTENSIONS = ['.zip', '.7z', '.rar']
IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
    ".svg",
    ".pdf",
}

NON_ROM_EXTENSIONS = {
    ".nfo",
    ".txt",
    ".md",
    ".log",
    ".diz",
    ".json",
    ".yaml",
    ".yml",
    ".ini",
}

DEFAULT_IGNORE_EXTENSIONS = IMAGE_EXTENSIONS | NON_ROM_EXTENSIONS

class HighPerformanceScanner:
    """A Highly Optimized Scanner for Rome Files with Advanced Processing."""

    def __init__(self, config: Optional[ConfigType] = None):
        """Initialized the scanner. Args: Config: Optional configuration instance. If None, the standard configuration is used."""
        self.config = config or Config()
        self.is_running = False
        self.is_paused = False
        self.should_stop = False

        # Make sure that the directory structure exists
        self._ensure_directories()

        # Initialized counters for the statistics
        self._reset_counters()

        # Threads and cues
        self.worker_threads = []
        self.file_queue = queue.Queue()
        self.result_queue = queue.Queue()

        # Determine the optimal thread number based on config + CPU
        self.max_workers = self._resolve_max_workers()
        self.chunk_size = self._resolve_chunk_size()
        logger.info(f"Scanner konfiguriert mit {self.max_workers} Threads (chunk={self.chunk_size} bytes)")

        # Callbacks for event handler
        # Define default empty callback functions to ensure they're always callable
        self.on_file_found = lambda path: None  # Callback: (path: str) -> None
        self.on_rom_found = lambda rom_info: None   # Callback: (rom_info: Dict) -> None
        self.on_progress = lambda current, total: None    # Callback: (current: int, total: int) -> None
        self.on_complete = lambda stats: None    # Callback: (stats: Dict) -> None
        self.on_error = lambda error: None       # Callback: (error: str) -> None

        # Optional DAT index (lazy). Provides accurate mapping for No-Intro/Redump/TOSEC/MAME style sets.
        self._dat_index = None
        self._dat_lock = threading.Lock()

        # Ignore extensions configured from config
        self._ignore_exts = self._resolve_ignore_extensions()

        # In-memory cache to skip repeated work within a session
        self._cache: Dict[Tuple[str, int, int], Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

    def _resolve_max_workers(self) -> int:
        try:
            scanner_cfg = self.config.get("scanner", {}) or {}
            configured = int(scanner_cfg.get("max_threads", 0) or 0)
        except Exception:
            configured = 0

        if configured > 0:
            return min(32, max(1, configured))

        cpu_count = os.cpu_count() or 4
        return min(32, max(4, cpu_count * 2))

    def _resolve_chunk_size(self) -> int:
        size = None
        try:
            scanner_cfg = self.config.get("scanner", {}) or {}
            size = scanner_cfg.get("chunk_size")
        except Exception:
            size = None
        if not size:
            try:
                perf_cfg = self.config.get("performance", {}).get("processing", {}) or {}
                size = perf_cfg.get("chunk_size")
            except Exception:
                size = None
        try:
            size = int(size or DEFAULT_CHUNK_SIZE)
        except Exception:
            size = DEFAULT_CHUNK_SIZE
        return max(64 * 1024, min(32 * 1024 * 1024, size))

    def _resolve_ignore_extensions(self) -> Set[str]:
        ignore_exts: Set[str] = set()
        try:
            scanner_cfg = self.config.get("scanner", {}) or {}
            ignore_images = bool(scanner_cfg.get("ignore_images", True))
            if ignore_images:
                ignore_exts.update(IMAGE_EXTENSIONS)

            custom = scanner_cfg.get("ignore_extensions") or []
            if isinstance(custom, str):
                custom = [custom]
            for ext in custom:
                if not ext:
                    continue
                val = str(ext).lower().strip()
                if not val:
                    continue
                if not val.startswith("."):
                    val = f".{val}"
                ignore_exts.add(val)
        except Exception:
            ignore_exts.update(DEFAULT_IGNORE_EXTENSIONS)

        if not ignore_exts:
            ignore_exts.update(DEFAULT_IGNORE_EXTENSIONS)

        return ignore_exts

    def _get_dat_index(self):
        if self._dat_index is not None:
            return self._dat_index
        with self._dat_lock:
            if self._dat_index is not None:
                return self._dat_index
            try:
                from ..core.dat_index_sqlite import DatIndexSqlite
                cfg = self.config or {}
                dat_cfg = cfg.get("dats", {}) or {}
                index_path = dat_cfg.get("index_path") or os.path.join("data", "index", "romsorter_dat_index.sqlite")
                if not os.path.exists(index_path):
                    self._dat_index = None
                else:
                    self._dat_index = DatIndexSqlite(Path(index_path))
            except Exception:
                self._dat_index = None
            return self._dat_index

    def _reset_counters(self):
        """Reset all statistics meters."""
        self.files_processed = 0
        self.files_found = 0
        self.roms_found = 0
        self.archives_found = 0
        self.errors = 0
        self.start_time = 0
        self.end_time = 0

# Extended tracking for detailed analysis
        self.system_counts = {}  # Counts Roms per system
        self.extension_counts = {}  # Counts files per expansion
        self.size_distribution = {
            'small': 0,    # <1MB
            'medium': 0,   # 1-50MB
            'large': 0,    # 50-500MB
            'xl': 0        # >500MB
        }

    def _ensure_directories(self):
        """Make sure that all the required directories exist."""
        cache_dir = self.config.get("cache_directory", "cache")
        os.makedirs(cache_dir, exist_ok=True)

# Other required directories
        temp_dir = os.path.join(cache_dir, "temp")
        log_dir = os.path.join(cache_dir, "logs")

        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)

    def scan(self, directory: str, recursive: bool = True, file_types: Optional[List[str]] = None,
             max_depth: int = -1, follow_symlinks: bool = False, use_cache: bool = True):
        """Starts an asynchronous scan of the specified directory. Args: Directory: The directory to be searched Recursive: Whether subdirectaries should be searched File_types: List of file extensions that are to be searched (None for all known Rome types) Max_depth: Maximum depth of recursion (-1 for unlimited) Follow_symlinks: Whether symbolic links should be followed use_cache: Whether cache data should be used Return: True when the scan was successfully started, otherwise false"""
        if self.is_running:
            logger.warning("Ein Scan läuft bereits. Bitte warten Sie, bis dieser abgeschlossen ist.")
            return False

# Check whether the directory exists
        if not os.path.isdir(directory):
            error_msg = f"Verzeichnis existiert nicht: {directory}"
            logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)
            return False

# Reset scanner status
        self.is_running = True
        self.should_stop = False
        self.is_paused = False
        self._reset_counters()

# Pack Scan options in a dictionary
        scan_options = {
            'recursive': recursive,
            'file_types': file_types,
            'max_depth': max_depth,
            'follow_symlinks': follow_symlinks,
            'use_cache': use_cache
        }

# Starts the scan in a separate thread
        threading.Thread(
            target=self._scan_thread,
            args=(directory, scan_options),
            daemon=True
        ).start()

        return True

    def pause(self):
        """Pauses the running scan. Return: True when the scan was successfully paused, otherwise false"""
        if self.is_running and not self.is_paused:
            logger.info("Scan pausiert")
            self.is_paused = True
            return True
        return False

    def resume(self):
        """Stop a paused scan. Return: True when the scan was successfully continued, OtherWise False"""
        if self.is_running and self.is_paused:
            logger.info("Scan fortgesetzt")
            self.is_paused = False
            return True
        return False

    def stop(self):
        """Stop the running scan. Return: True when the scan was successfully stopped, otherwise false"""
        if self.is_running:
            logger.info("Scan wird gestoppt...")
            self.should_stop = True
            self.is_paused = False
            return True
        return False

    def _scan_thread(self, directory: str, options: Dict[str, Any]):
        """Main thread for the scanning process. Coordinates the worker threads and collects the results. Args: Directory: The directory to be searched Options: Dictionary with scan options"""
        try:
            self.start_time = time.time()

# Unpack options
            recursive = options.get('recursive', True)
            file_types = options.get('file_types')
            max_depth = options.get('max_depth', -1)
            follow_symlinks = options.get('follow_symlinks', False)
            use_cache = options.get('use_cache', True)

# Write a Message Into the Log
            logger.info(f"Starte Scan von {directory} mit Optionen: recursive={recursive}, "
                       f"max_depth={max_depth}, follow_symlinks={follow_symlinks}")

# Collect all files to be scanned
            file_list = self._collect_files(directory, recursive, file_types, max_depth, follow_symlinks)
            total_files = len(file_list)

# No files found?
            if total_files == 0:
                self._finish_scan("Keine Dateien gefunden")
                return

            logger.info(f"{total_files} zu scannende Dateien gefunden")

# Initialize the thread pool with an optimal number of thread
            num_workers = min(self.max_workers, max(1, total_files // 10))
            logger.info(f"Starte Scan mit {num_workers} Worker-Threads")

            progress_batch = True
            try:
                perf_cfg = self.config.get("performance", {}).get("optimization", {}) or {}
                progress_batch = bool(perf_cfg.get("enable_progress_batching", True))
            except Exception:
                progress_batch = True

            progress_every = max(1, total_files // 100) if progress_batch else 1
            last_progress_ts = 0.0

# Use a thread pool for file processing
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
# Starts with the processing of the files
                futures = {executor.submit(self._process_file, file_path, use_cache): file_path
                          for file_path in file_list}

# Process the results while you arrive
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
# Check whether the scan should be stopped
                    if self.should_stop:
                        for f in futures:
                            f.cancel()
                        break

# Wait when paused
                    while self.is_paused and not self.should_stop:
                        time.sleep(0.1)

# Processes the result
                    try:
                        file_path = futures[future]
                        rom_info = future.result() or {}  # Ensure we have a valid dict, not None

# If a valid rome was found
                        if rom_info:
                            self.roms_found += 1

# Updates the system statistics
                            system = rom_info.get('system', 'Unknown')
                            self.system_counts[system] = self.system_counts.get(system, 0) + 1

# Updates the size statistics
                            size = rom_info.get('size', 0)
                            if size < 1024 * 1024:  # <1MB
                                self.size_distribution['small'] += 1
                            elif size < 50 * 1024 * 1024:  # <50MB
                                self.size_distribution['medium'] += 1
                            elif size < 500 * 1024 * 1024:  # <500MB
                                self.size_distribution['large'] += 1
                            else:  # >500MB
                                self.size_distribution['xl'] += 1

# Call the callback, if available
                            if self.on_rom_found:
                                self.on_rom_found(rom_info)

                    except Exception as e:
                        self.errors += 1
                        # Use the file from the future dictionary
                        file_to_report = futures.get(future, "unknown file")
                        logger.error(f"Fehler bei der Verarbeitung von {file_to_report}: {str(e)}")

# Updates progress
                    self.files_processed += 1
                    if self.on_progress:
                        if not progress_batch or self.files_processed % progress_every == 0 or self.files_processed == total_files:
                            now = time.time()
                            if (now - last_progress_ts) >= 0.05 or self.files_processed == total_files:
                                last_progress_ts = now
                                self.on_progress(self.files_processed, total_files)

# One last progress update
            if self.on_progress:
                self.on_progress(self.files_processed, total_files)

# Scan completed
            self._finish_scan("Scan erfolgreich abgeschlossen")

        except Exception as e:
            logger.exception("Unerwarteter Fehler beim Scannen")
            if self.on_error:
                self.on_error(str(e))
            self._finish_scan(f"Fehler: {str(e)}")

    def _collect_files(self, directory: str, recursive: bool, file_types: Optional[List[str]],
                      max_depth: int = -1, follow_symlinks: bool = False, current_depth: int = 0) -> List[str]:
        """Collect all files to be scanned in the specified directory. Args: Directory: Directory to be searched Recursive: Whether subdirectaries should be searched File_types: List of file extensions or None for all known types Max_depth: Maximum depth of recursion (-1 for unlimited) Follow_symlinks: Whether symbolic links should be followed Current_deth: Current recursion depths (used internally) Return: List of all found file paths"""
        result = []

# Reached maximum depth?
        if max_depth >= 0 and current_depth > max_depth:
            return result

# Determine the file extensions to be searched
        if file_types is None:
            # Pull the complete ROM extension set from the central console database.
            # This avoids hardcoded/partial mappings (e.g. '.bin' -> Sega for everything).
            from ..database.console_db import get_all_rom_extensions
            file_types = sorted(get_all_rom_extensions(include_dot=True))
            # Adds archive files
            file_types.extend(ARCHIVE_EXTENSIONS)

        try:
            # Normalize the file extensions (ensure leading dot)
            normalized: List[str] = []
            for ext in (file_types or []):
                if not ext:
                    continue
                ext = ext.lower()
                if not ext.startswith('.'):
                    ext = f'.{ext}'
                normalized.append(ext)
            file_types = normalized

            file_type_set = set(file_types)

            # Used Pathlib for better platform independence
            dir_path = Path(directory)

            # PS3 extracted game folder: treat as single ROM and skip its contents
            if self._is_ps3_game_dir(dir_path):
                result.append(str(dir_path))
                self.files_found += 1
                return result

# Browse all entries in the directory
            for entry in dir_path.iterdir():
# Check whether the scan should be stopped
                if self.should_stop:
                    break

# Symlink policy: skip symlinked files always; follow symlinked dirs only if enabled
                if entry.is_symlink():
                    if entry.is_dir() and follow_symlinks:
                        pass
                    else:
                        continue

                # Subdir?
                if entry.is_dir():
                    if self._is_ps3_game_dir(entry):
                        result.append(str(entry))
                        self.files_found += 1
                        continue
                    if recursive:
                        # Recursive call for subdirectory
                        subdir_files = self._collect_files(
                            str(entry), recursive, file_types,
                            max_depth, follow_symlinks, current_depth + 1
                        )
                        result.extend(subdir_files)

# File?
                elif entry.is_file():
                    # Check whether the file extension is in the list
                    ext = entry.suffix.lower()
                    if ext in self._ignore_exts:
                        continue
                    if ext in file_type_set:
                        result.append(str(entry))
                        self.files_found += 1

# Updates the expansion statistics
                        self.extension_counts[ext] = self.extension_counts.get(ext, 0) + 1

# Callback, if available
                        if self.on_file_found:
                            self.on_file_found(str(entry))

        except Exception as e:
            logger.error(f"Fehler beim Sammeln der Dateien in {directory}: {str(e)}")
            if self.on_error:
                self.on_error(f"Fehler beim Sammeln der Dateien: {str(e)}")

        return result

    def _process_file(self, file_path: str, use_cache: bool = True) -> Optional[Dict]:
        """Process a single file and return the rom information if found. ARGS: File_Path: Path to the File to Be Processed Use_cache: Whether Cache Data Should be used Return: Dictionary with Rome Information or None If No Rome Has Be."""
        try:
            if self.should_stop:
                return None

            path_obj = Path(file_path)

            file_stat = None
            cache_key = None
            if use_cache and path_obj.is_file():
                try:
                    file_stat = os.stat(file_path)
                    cache_key = self._make_cache_key(file_path, file_stat)
                    with self._cache_lock:
                        cached = self._cache.get(cache_key)
                    if cached:
                        return cached
                except Exception:
                    file_stat = None
                    cache_key = None

            if path_obj.is_dir() and self._is_ps3_game_dir(path_obj):
                file_stat = file_stat or os.stat(file_path)
                rom_info = {
                    'name': path_obj.name,
                    'path': str(path_obj),
                    'system': 'PS3',
                    'detection_confidence': 0.90,
                    'detection_source': 'structure-ps3',
                    'size': 0,
                    'crc32': None,
                    'md5': None,
                    'sha1': None,
                    'last_modified': file_stat.st_mtime,
                    'valid': True,
                    'is_directory': True,
                }
                if use_cache:
                    self._save_to_cache(file_path, rom_info, file_stat=file_stat)
                return rom_info

# Perform cache lookup if activated
            # Cache lookup already handled above for files

            # Check whether it is an archive
            if any(file_path.lower().endswith(ext) for ext in ARCHIVE_EXTENSIONS):
                self.archives_found += 1
                if file_path.lower().endswith('.zip'):
                    return self._process_zip_archive(file_path)
                # .7z/.rar are not supported without external deps, but we can still do DAT
                # game-name matching using the archive stem.
                return self._process_archive_name_only(file_path)

# Collect basic file information
            file_stat = file_stat or os.stat(file_path)
            file_size = file_stat.st_size
            file_name = os.path.basename(file_path)
            ext = Path(file_name).suffix.lower().lstrip(".")

            # Calculates checksums (used for DAT matching too)
            crc32, md5, sha1 = self._calculate_checksums(file_path)

            # DAT/Hash-first: exact match is truth.
            dat_index = self._get_dat_index()
            is_exact = False
            canonical_name: Optional[str] = None
            if dat_index is not None:
                try:
                    match = dat_index.lookup_sha1(sha1)
                    if match:
                        rom_system = match.platform_id or "Unknown"
                        confidence = 1000.0
                        detection_source = "dat:sha1"
                        is_exact = True
                        canonical_name = match.rom_name or match.set_name
                    else:
                        match_crc = dat_index.lookup_crc_size_when_sha1_missing(crc32, file_size)
                        if match_crc:
                            rom_system = match_crc.platform_id or "Unknown"
                            confidence = 1000.0
                            detection_source = "dat:crc-size"
                            is_exact = True
                            canonical_name = match_crc.rom_name or match_crc.set_name
                except Exception:
                    pass

            # Determine console/system type (strict: avoid false positives).
            if not is_exact:
                rom_system, confidence, detection_source = self._detect_system(file_path, file_size=file_size)
                if not rom_system:
                    return None

            candidates_info: Dict[str, Any] = {}
            try:
                from ..core.platform_heuristics import evaluate_platform_candidates
                candidates_info = evaluate_platform_candidates(file_path, container=ext or None)
            except Exception:
                candidates_info = {}

            # Strict mode: only accept exact DAT matches or unique extensions.
            if not is_exact:
                if detection_source != "extension-unique":
                    rom_system = "Unknown"
                    confidence = 0.0
                    detection_source = "unknown"
                else:
                    policy = candidates_info.get("policy") or {}
                    candidate_details = candidates_info.get("candidate_details") or []

                    try:
                        min_score_delta = float(policy.get("min_score_delta", 1.0))
                    except Exception:
                        min_score_delta = 1.0
                    try:
                        min_top_score = float(policy.get("min_top_score", 2.0))
                    except Exception:
                        min_top_score = 2.0
                    try:
                        contradiction_min_score = float(policy.get("contradiction_min_score", min_top_score))
                    except Exception:
                        contradiction_min_score = min_top_score

                    if candidate_details:
                        top = candidate_details[0]
                        runner_up = candidate_details[1] if len(candidate_details) > 1 else None

                        try:
                            top_score = float(top.get("score", 0.0))
                        except Exception:
                            top_score = 0.0
                        try:
                            runner_score = float(runner_up.get("score", 0.0)) if runner_up else 0.0
                        except Exception:
                            runner_score = 0.0

                        delta = top_score - runner_score if runner_up else top_score

                        conflict_groups = set(top.get("conflict_groups") or [])
                        runner_conflict_groups = set(runner_up.get("conflict_groups") or []) if runner_up else set()
                        shared_conflict = conflict_groups.intersection(runner_conflict_groups)

                        if runner_up and shared_conflict and top_score >= min_top_score and runner_score >= min_top_score:
                            rom_system = "Unknown"
                            confidence = 0.0
                            detection_source = "conflict-group"
                        elif runner_up and top_score >= min_top_score and delta < min_score_delta:
                            rom_system = "Unknown"
                            confidence = 0.0
                            detection_source = "ambiguous-candidates"
                        else:
                            norm_system = re.sub(r"[^a-z0-9]+", "", str(rom_system or "").lower())
                            norm_top = re.sub(r"[^a-z0-9]+", "", str(top.get("platform_id") or "").lower())
                            if top_score >= contradiction_min_score and norm_system and norm_top and norm_system != norm_top:
                                rom_system = "Unknown"
                                confidence = 0.0
                                detection_source = "contradiction-candidates"

# Creates the ROM information object
            rom_info = {
                'name': file_name,
                'path': file_path,
                'system': rom_system,
                'detection_confidence': confidence,
                'detection_source': detection_source,
                'is_exact': bool(is_exact),
                'canonical_name': canonical_name,
                'signals': candidates_info.get('signals') or [],
                'candidates': candidates_info.get('candidates') or [],
                'candidate_systems': candidates_info.get('candidate_systems') or [],
                'size': file_size,
                'crc32': crc32,
                'md5': md5,
                'sha1': sha1,
                'last_modified': file_stat.st_mtime,
                'valid': True  # Could be changed later by validation
            }

# Saves the information in the cache
            if use_cache:
                self._save_to_cache(file_path, rom_info, file_stat=file_stat)

            return rom_info

        except Exception as e:
            logger.error(f"Fehler bei der Verarbeitung von {file_path}: {str(e)}")
            return None

    def _is_ps3_game_dir(self, path: Path) -> bool:
        """Return True if the directory looks like an extracted PS3 game."""
        try:
            if not path.is_dir():
                return False
            ps3_game = path / "PS3_GAME"
            if not ps3_game.is_dir():
                return False
            if (path / "PS3_DISC.SFB").is_file():
                return True
            if (ps3_game / "USRDIR" / "EBOOT.BIN").is_file():
                return True
            if (ps3_game / "PARAM.SFO").is_file():
                return True
        except Exception:
            return False
        return False

    def _process_zip_archive(self, file_path: str) -> Optional[Dict]:
        """Process a ZIP archive as a single sortable unit (strict).

        We do NOT extract. We only accept exact DAT evidence:
        - DAT game-name match (zip stem)
        - DAT hash matches against contained entries (ZipInfo.CRC)
        Otherwise return Unknown to avoid false positives.
        """
        try:
            path_obj = Path(file_path)
            zip_stem = path_obj.stem
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size

            dat_index = self._get_dat_index()
            if dat_index is not None:
                try:
                    game_match = dat_index.lookup_game(zip_stem)
                    if game_match and game_match[0]:
                        system_name = game_match[0]
                        if not self._system_tokens_in_path(system_name, str(path_obj)):
                            candidates_info: Dict[str, Any] = {}
                            try:
                                from ..core.platform_heuristics import evaluate_platform_candidates
                                candidates_info = evaluate_platform_candidates(file_path, container="zip")
                            except Exception:
                                candidates_info = {}
                            return {
                                'name': path_obj.name,
                                'path': str(path_obj),
                                'system': 'Unknown',
                                'detection_confidence': 0.0,
                                'detection_source': 'dat-name-mismatch',
                                'is_exact': False,
                                'signals': candidates_info.get('signals') or [],
                                'candidates': candidates_info.get('candidates') or [],
                                'candidate_systems': candidates_info.get('candidate_systems') or [],
                                'size': file_size,
                                'crc32': None,
                                'md5': None,
                                'last_modified': file_stat.st_mtime,
                                'valid': True,
                                'is_archive': True,
                                'archive_type': 'zip',
                                'archive_entry_count': None,
                            }
                        candidates_info: Dict[str, Any] = {}
                        try:
                            from ..core.platform_heuristics import evaluate_platform_candidates
                            candidates_info = evaluate_platform_candidates(file_path, container="zip")
                        except Exception:
                            candidates_info = {}
                        return {
                            'name': path_obj.name,
                            'path': str(path_obj),
                            'system': system_name,
                            'detection_confidence': 1000.0,
                            'detection_source': "dat:name",
                            'is_exact': True,
                            'signals': candidates_info.get('signals') or [],
                            'candidates': candidates_info.get('candidates') or [],
                            'candidate_systems': candidates_info.get('candidate_systems') or [],
                            'size': file_size,
                            'crc32': None,
                            'md5': None,
                            'last_modified': file_stat.st_mtime,
                            'valid': True,
                            'is_archive': True,
                            'archive_type': 'zip',
                            'archive_entry_count': None,
                        }
                except Exception:
                    pass

            from ..security.security_utils import is_safe_archive_member

            with zipfile.ZipFile(str(path_obj), 'r') as zf:
                infos = [zi for zi in zf.infolist() if not zi.is_dir()]

            # Fast exit if empty
            if not infos:
                return None

            # Count DAT evidence by entry CRCs
            system_scores: Dict[str, float] = {}
            system_sources: Dict[str, str] = {}

            if dat_index is not None:
                try:
                    for zi in infos:
                        if not is_safe_archive_member(zi.filename):
                            continue
                        with zf.open(zi, 'r') as entry_f:
                            crc32_val = 0
                            sha1_hash = hashlib.sha1()
                            while chunk := entry_f.read(self.chunk_size):
                                if self.should_stop:
                                    raise InterruptedError("Scan wurde abgebrochen")
                                crc32_val = zipfile.crc32(chunk, crc32_val)
                                sha1_hash.update(chunk)
                            entry_sha1 = sha1_hash.hexdigest()
                            match = dat_index.lookup_sha1(entry_sha1)
                            if not match:
                                entry_crc = f"{crc32_val & 0xFFFFFFFF:08x}"
                                match = dat_index.lookup_crc_size_when_sha1_missing(entry_crc, zi.file_size)
                            if match and match.platform_id:
                                system_scores[match.platform_id] = system_scores.get(match.platform_id, 0.0) + 1.0
                                system_sources[match.platform_id] = "dat:entry"
                except Exception:
                    pass

            if not system_scores:
                system = 'Unknown'
                confidence = 0.0
                source = 'zip-unknown'
            else:
                # Strict: accept only if all DAT evidence points to a single system.
                if len(system_scores) != 1:
                    system = 'Unknown'
                    confidence = 0.0
                    source = 'zip-conflict'
                else:
                    system = next(iter(system_scores.keys()))
                    confidence = 1000.0
                    source = str(system_sources.get(system, 'dat'))

            candidates_info = {}
            try:
                from ..core.platform_heuristics import evaluate_platform_candidates
                candidates_info = evaluate_platform_candidates(file_path, container="zip")
            except Exception:
                candidates_info = {}

            return {
                'name': path_obj.name,
                'path': str(path_obj),
                'system': system,
                'detection_confidence': float(confidence),
                'detection_source': str(source),
                'is_exact': bool(system_scores) and len(system_scores) == 1,
                'signals': candidates_info.get('signals') or [],
                'candidates': candidates_info.get('candidates') or [],
                'candidate_systems': candidates_info.get('candidate_systems') or [],
                'size': file_size,
                'crc32': None,
                'md5': None,
                'last_modified': file_stat.st_mtime,
                'valid': True,
                'is_archive': True,
                'archive_type': 'zip',
                'archive_entry_count': len(infos),
            }

        except Exception as e:
            logger.error(f"Fehler bei der ZIP-Verarbeitung von {file_path}: {str(e)}")
            return None

    def _process_archive_name_only(self, file_path: str) -> Optional[Dict]:
        """Best-effort handling for archives we cannot inspect without optional deps.

        If DATs are configured and the archive stem matches a DAT game name, we can still
        classify and sort accurately (common for curated set naming).
        """
        try:
            path_obj = Path(file_path)
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            dat_index = self._get_dat_index()
            if dat_index is not None:
                match = dat_index.lookup_game(path_obj.stem)
                if match and match.system:
                    if not self._system_tokens_in_path(match.system, str(path_obj)):
                        return {
                            'name': path_obj.name,
                            'path': str(path_obj),
                            'system': 'Unknown',
                            'detection_confidence': 0.0,
                            'detection_source': 'dat-name-mismatch',
                            'is_exact': False,
                            'signals': [],
                            'candidates': [],
                            'candidate_systems': [],
                            'size': file_size,
                            'crc32': None,
                            'md5': None,
                            'sha1': None,
                            'last_modified': file_stat.st_mtime,
                            'valid': True,
                            'is_archive': True,
                            'archive_type': path_obj.suffix.lower().lstrip('.'),
                            'archive_entry_count': None,
                        }
                    candidates_info: Dict[str, Any] = {}
                    try:
                        from ..core.platform_heuristics import evaluate_platform_candidates
                        candidates_info = evaluate_platform_candidates(file_path, container=path_obj.suffix.lower().lstrip('.'))
                    except Exception:
                        candidates_info = {}
                    return {
                        'name': path_obj.name,
                        'path': str(path_obj),
                        'system': match.system,
                        'detection_confidence': 1000.0,
                        'detection_source': f"dat:{match.source}",
                        'is_exact': True,
                        'signals': candidates_info.get('signals') or [],
                        'candidates': candidates_info.get('candidates') or [],
                        'candidate_systems': candidates_info.get('candidate_systems') or [],
                        'size': file_size,
                        'crc32': None,
                        'md5': None,
                        'sha1': None,
                        'last_modified': file_stat.st_mtime,
                        'valid': True,
                        'is_archive': True,
                        'archive_type': path_obj.suffix.lower().lstrip('.'),
                        'archive_entry_count': None,
                    }
            return None
        except Exception:
            return None

    @staticmethod
    def _system_tokens_in_path(system_name: str, path: str) -> bool:
        try:
            tokens = re.findall(r"[a-z0-9]+", str(system_name).lower())
            tokens = [t for t in tokens if len(t) >= 3]
            if not tokens:
                return False
            haystack = re.sub(r"[\\/_\-]+", " ", str(path).lower())
            return all(token in haystack for token in tokens)
        except Exception:
            return False

    def _detect_system(self, file_path: str, file_size: int = 0) -> Tuple[Optional[str], float, str]:
        """Detect console/system for a ROM file (strict, false-positive safe).

        Strategy:
        1) Unique extension match from the enhanced console DB.
        2) Centralized detector only if it yields near-certain confidence.
        Otherwise return Unknown.
        """
        try:
            from ..database.console_db import ENHANCED_CONSOLE_DATABASE
        except Exception:
            ENHANCED_CONSOLE_DATABASE = {}

        path_obj = Path(file_path)
        ext = path_obj.suffix.lower()

        # 1) Unique extension match
        candidates = [
            console_name
            for console_name, meta in ENHANCED_CONSOLE_DATABASE.items()
            if ext in getattr(meta, 'extensions', set())
        ]
        if len(candidates) == 1:
            return candidates[0], 0.90, 'extension-unique'

        # 2) Centralized detector (handler + console detector) with strict threshold
        try:
            from ..detectors.detection_handler import detect_console
            detected, conf = detect_console(path_obj.name, str(path_obj))
            detected = detected or "Unknown"
            if detected != "Unknown" and float(conf or 0.0) >= 0.95:
                return detected, float(conf or 0.0), 'detector-handler'
        except Exception:
            pass

        if candidates:
            # Ambiguous extension: avoid guessing.
            return 'Unknown', 0.0, 'ambiguous-extension'

        return None, 0.0, 'unknown'

    def _calculate_checksums(self, file_path: str) -> Tuple[str, str, str]:
        """Calculate CRC32, MD5 and SHA1 of a file in a single pass."""
        crc32_value = 0
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()

        with open(file_path, 'rb') as f:
            while chunk := f.read(self.chunk_size):
                # Check whether the scan should be paused or stopped
                if self.is_paused:
                    while self.is_paused and not self.should_stop:
                        time.sleep(0.1)

                if self.should_stop:
                    raise InterruptedError("Scan wurde abgebrochen")

                # Updates all checksums at the same time for efficiency
                crc32_value = zipfile.crc32(chunk, crc32_value)
                md5_hash.update(chunk)
                sha1_hash.update(chunk)

        return f"{crc32_value & 0xFFFFFFFF:08x}", md5_hash.hexdigest(), sha1_hash.hexdigest()

    def _make_cache_key(self, file_path: str, file_stat: os.stat_result) -> Tuple[str, int, int]:
        return (file_path, int(file_stat.st_mtime), int(file_stat.st_size))

    def _get_from_cache(self, file_path: str, file_stat: os.stat_result) -> Optional[Dict]:
        """Try to load ROM information from the cache.

        Args: File_Path: path to the file
        Return: ROM information or none, if not in the cache or outdated
        """
        key = self._make_cache_key(file_path, file_stat)
        with self._cache_lock:
            return self._cache.get(key)

    def _save_to_cache(self, file_path: str, rom_info: Dict, file_stat: Optional[os.stat_result] = None) -> None:
        """Store ROM information in the in-memory cache."""
        try:
            if file_stat is None:
                file_stat = os.stat(file_path)
            key = self._make_cache_key(file_path, file_stat)
            with self._cache_lock:
                self._cache[key] = dict(rom_info)
        except Exception:
            return

    def _finish_scan(self, message: str):
        """Complete the scan and call up the Completion Callback. Args: Message: final report for the log"""
        self.end_time = time.time()
        duration = self.end_time - self.start_time

        logger.info(f"Scan abgeschlossen: {message}")
        logger.info(f"Gefundene Dateien: {self.files_found}")
        logger.info(f"Gefundene ROMs: {self.roms_found}")
        logger.info(f"Gefundene Archive: {self.archives_found}")
        logger.info(f"Fehler: {self.errors}")
        logger.info(f"Dauer: {duration:.2f} Sekunden")

# Creates the statistics
        stats = {
            "files_processed": self.files_processed,
            "files_found": self.files_found,
            "roms_found": self.roms_found,
            "archives_found": self.archives_found,
            "errors": self.errors,
            "duration_seconds": duration,
            "message": message,
            "system_counts": self.system_counts,
            "extension_counts": self.extension_counts,
            "size_distribution": self.size_distribution
        }

# Call the callback, if available
        if self.on_complete:
            self.on_complete(stats)

# Set the status back
        self.is_running = False
        self.is_paused = False
        self.should_stop = False

# Exports This Class as a Standard Scanner
default_scanner = HighPerformanceScanner
