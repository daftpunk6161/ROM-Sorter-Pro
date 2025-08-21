#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - High-Performance Scanner v2.1.8
Phase 1 Implementation: Desktop Optimization

This module implements a high-performance scanner for ROM files with advanced
thread management, optimized memory usage, and enhanced error handling.

FEATURES:
- Multi-threading for maximum CPU utilization
- Advanced parallel processing for optimal performance
- Intelligent chunking of large files for reduced memory usage
- Robust error handling with recovery capabilities
- Adaptive scanning for different systems
- Support for delayed and incremental processing
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
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Callable, Union, Any, Generator, TypeVar

# Define the type alias for the config class
ConfigType = TypeVar('ConfigType')

# Local imports
from ..exceptions import ScannerError
from ..config import Config

# Set up logging
logger = logging.getLogger(__name__)

# Constant
MAX_WORKERS = os.cpu_count() or 4  # Fallback auf 4 Threads
CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB for file chunking
FILE_EXTENSIONS = {
    'Nintendo': ['.nes', '.fds'],
    'Super Nintendo': ['.sfc', '.smc'],
    'Nintendo 64': ['.n64', '.z64', '.v64'],
    'GameBoy': ['.gb', '.gbc', '.gba'],
    'Sega Genesis/Mega Drive': ['.gen', '.bin', '.md', '.smd'],
    'PlayStation': ['.iso', '.bin', '.img', '.chd', '.pbp'],
    'Dreamcast': ['.gdi', '.cdi', '.chd'],
    'Arcade': ['.zip']
}
ARCHIVE_EXTENSIONS = ['.zip', '.7z', '.rar']

class HighPerformanceScanner:
    """Ein hochoptimierter Scanner für ROM-Dateien mit fortschrittlicher Parallelverarbeitung."""

    def __init__(self, config: Optional[ConfigType] = None):
        """
        Initialisiert den Scanner.

        Args:
            config: Optionale Konfigurationsinstanz. Falls None, wird die Standardkonfiguration verwendet.
        """
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

# Definitely determines the optimal thread number based on the CPU number
        cpu_count = os.cpu_count() or 4
        self.max_workers = min(32, max(4, cpu_count * 2))  # Between 4 and 32 threads
        logger.info(f"Scanner konfiguriert mit {self.max_workers} Threads")

# Callbacks for event handler
        self.on_file_found = None  # Callback: (path: str) -> None
        self.on_rom_found = None   # Callback: (rom_info: Dict) -> None
        self.on_progress = None    # Callback: (current: int, total: int) -> None
        self.on_complete = None    # Callback: (stats: Dict) -> None
        self.on_error = None       # Callback: (error: str) -> None

    def _reset_counters(self):
        """Setzt alle Statistikzähler zurück."""
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
        """Stellt sicher, dass alle benötigten Verzeichnisse existieren."""
        cache_dir = self.config.get("cache_directory", "cache")
        os.makedirs(cache_dir, exist_ok=True)

# Other required directories
        temp_dir = os.path.join(cache_dir, "temp")
        log_dir = os.path.join(cache_dir, "logs")

        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)

    def scan(self, directory: str, recursive: bool = True, file_types: Optional[List[str]] = None,
             max_depth: int = -1, follow_symlinks: bool = False, use_cache: bool = True):
        """
        Startet einen asynchronen Scan des angegebenen Verzeichnisses.

        Args:
            directory: Das zu durchsuchende Verzeichnis
            recursive: Ob Unterverzeichnisse durchsucht werden sollen
            file_types: Liste von Dateierweiterungen, die gesucht werden sollen
                        (None für alle bekannten ROM-Typen)
            max_depth: Maximale Rekursionstiefe (-1 für unbegrenzt)
            follow_symlinks: Ob symbolischen Links gefolgt werden soll
            use_cache: Ob Cache-Daten verwendet werden sollen

        Returns:
            True wenn der Scan erfolgreich gestartet wurde, False sonst
        """
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
        """
        Pausiert den laufenden Scan.

        Returns:
            True wenn der Scan erfolgreich pausiert wurde, False sonst
        """
        if self.is_running and not self.is_paused:
            logger.info("Scan pausiert")
            self.is_paused = True
            return True
        return False

    def resume(self):
        """
        Setzt einen pausierten Scan fort.

        Returns:
            True wenn der Scan erfolgreich fortgesetzt wurde, False sonst
        """
        if self.is_running and self.is_paused:
            logger.info("Scan fortgesetzt")
            self.is_paused = False
            return True
        return False

    def stop(self):
        """
        Stoppt den laufenden Scan.

        Returns:
            True wenn der Scan erfolgreich gestoppt wurde, False sonst
        """
        if self.is_running:
            logger.info("Scan wird gestoppt...")
            self.should_stop = True
            self.is_paused = False
            return True
        return False

    def _scan_thread(self, directory: str, options: Dict[str, Any]):
        """
        Hauptthread für den Scanvorgang.

        Koordiniert die Worker-Threads und sammelt die Ergebnisse.

        Args:
            directory: Das zu durchsuchende Verzeichnis
            options: Dictionary mit Scanoptionen
        """
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
                        rom_info = future.result()

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
                        logger.error(f"Fehler bei der Verarbeitung von {file_path}: {str(e)}")

# Updates progress
                    self.files_processed += 1
                    if self.on_progress and self.files_processed % max(1, total_files // 100) == 0:
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
        """
        Sammelt alle zu scannenden Dateien im angegebenen Verzeichnis.

        Args:
            directory: Zu durchsuchendes Verzeichnis
            recursive: Ob Unterverzeichnisse durchsucht werden sollen
            file_types: Liste von Dateierweiterungen oder None für alle bekannten Typen
            max_depth: Maximale Rekursionstiefe (-1 für unbegrenzt)
            follow_symlinks: Ob symbolischen Links gefolgt werden soll
            current_depth: Aktuelle Rekursionstiefe (intern verwendet)

        Returns:
            Liste aller gefundenen Dateipfade
        """
        result = []

# Reached maximum depth?
        if max_depth >= 0 and current_depth > max_depth:
            return result

# Determines the file extensions to be searched
        if file_types is None:
# Collect all known Rome date extensions
            file_types = []
            for extensions in FILE_EXTENSIONS.values():
                file_types.extend(extensions)

# Adds archive files
            file_types.extend(ARCHIVE_EXTENSIONS)

        try:
# Normalize the file extensions
            file_types = [ext.lower() for ext in file_types]

# Used Patlib for better platform independence
            dir_path = Path(directory)

# Browse all entries in the directory
            for entry in dir_path.iterdir():
# Check whether the scan should be stopped
                if self.should_stop:
                    break

# Symbolical links, if not desired
                if entry.is_symlink() and not follow_symlinks:
                    continue

# Subdler?
                if entry.is_dir():
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
                    if any(entry.name.lower().endswith(ext) for ext in file_types):
                        result.append(str(entry))
                        self.files_found += 1

# Updates the expansion statistics
                        ext = entry.suffix.lower()
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
        """
        Verarbeitet eine einzelne Datei und gibt die ROM-Informationen zurück, falls gefunden.

        Args:
            file_path: Pfad zur zu verarbeitenden Datei
            use_cache: Ob Cache-Daten verwendet werden sollen

        Returns:
            Dictionary mit ROM-Informationen oder None, wenn keine ROM gefunden wurde
        """
        try:
# Perform cache lookup if activated
            if use_cache:
                cached_info = self._get_from_cache(file_path)
                if cached_info:
                    return cached_info

# Check whether it is an archive
            if any(file_path.lower().endswith(ext) for ext in ARCHIVE_EXTENSIONS):
                self.archives_found += 1
# In A Complete Implementation, The Archive Content would be scanned here
                return None

# Collect basic file information
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            file_name = os.path.basename(file_path)

# Determines the system type based on the file extension
            rom_system = self._detect_system_by_extension(file_path)

            if not rom_system:
# Unknown file type
                return None

# Calculates pruef sums (more efficient with chunking for large files)
            crc32, md5 = self._calculate_checksums(file_path)

# Creates the ROM information object
            rom_info = {
                'name': file_name,
                'path': file_path,
                'system': rom_system,
                'size': file_size,
                'crc32': crc32,
                'md5': md5,
                'last_modified': file_stat.st_mtime,
                'valid': True  # Could be changed later by validation
            }

# Saves the information in the cache
            if use_cache:
                self._save_to_cache(file_path, rom_info)

            return rom_info

        except Exception as e:
            logger.error(f"Fehler bei der Verarbeitung von {file_path}: {str(e)}")
            return None

    def _detect_system_by_extension(self, file_path: str) -> Optional[str]:
        """
        Erkennt das System anhand der Dateierweiterung.

        Args:
            file_path: Zu prüfender Dateipfad

        Returns:
            Systemname oder None, wenn keine Übereinstimmung gefunden wurde
        """
        lower_path = file_path.lower()

        for system, extensions in FILE_EXTENSIONS.items():
            if any(lower_path.endswith(ext) for ext in extensions):
                return system

        return None

    def _calculate_checksums(self, file_path: str) -> Tuple[str, str]:
        """
        Berechnet CRC32 und MD5 Prüfsummen einer Datei.

        Verwendet Chunking für bessere Speichernutzung bei großen Dateien.

        Args:
            file_path: Pfad zur Datei

        Returns:
            Tuple mit (CRC32, MD5) Prüfsummen als Hex-Strings
        """
        crc32_value = 0
        md5_hash = hashlib.md5()

        with open(file_path, 'rb') as f:
            while chunk := f.read(CHUNK_SIZE):
# Check whether the scan should be paused or stopped
                if self.is_paused:
                    while self.is_paused and not self.should_stop:
                        time.sleep(0.1)

                if self.should_stop:
                    raise InterruptedError("Scan wurde abgebrochen")

# Updates both test sums at the same time for efficiency
                crc32_value = zipfile.crc32(chunk, crc32_value)
                md5_hash.update(chunk)

        return f"{crc32_value & 0xFFFFFFFF:08x}", md5_hash.hexdigest()

    def _get_from_cache(self, file_path: str) -> Optional[Dict]:
        """
        Versucht, ROM-Informationen aus dem Cache zu laden.

        Args:
            file_path: Pfad zur Datei

        Returns:
            ROM-Informationen oder None, wenn nicht im Cache oder veraltet
        """
# In a complete implementation, Cache Access Wood Take Place here
        return None

    def _save_to_cache(self, file_path: str, rom_info: Dict):
        """
        Speichert ROM-Informationen im Cache.

        Args:
            file_path: Pfad zur Datei
            rom_info: ROM-Informationen
        """
# In A Complete implementation, Cache Storage would take place place here
        pass

    def _finish_scan(self, message: str):
        """
        Schließt den Scan ab und ruft den Completion-Callback auf.

        Args:
            message: Abschlussmeldung für das Log
        """
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
