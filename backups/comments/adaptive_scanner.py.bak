#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Adaptive Scanner

Dieses Modul enthält adaptive Scanning-Klassen und -Funktionen für hochoptimierte ROM-Dateierkennung.
"""

import os
import time
import logging
import threading
import re
import gc
from pathlib import Path
from typing import List, Dict, Set, Any, Optional, Callable, Union, Tuple
from collections import deque, defaultdict
from functools import lru_cache

# Import core modules
from src.core.rom_utils import get_all_rom_extensions, is_valid_rom_file
from src.core.file_utils import create_directory_if_not_exists
from src.core.rom_models import ROMMetadata
from src.utils.performance_enhanced import measure_time

# Import detector modules
from src.detectors import detect_console_fast, is_archive_file, is_chd_file

# Import scanning module
from src.scanning.scanner import ROMScanner, OptimizedScanner

logger = logging.getLogger(__name__)


class AdaptiveScanner(OptimizedScanner):
    """
    Erweiterte ROM-Scanner-Klasse mit adaptiver Anpassung an Dateisystemleistung und intelligenten
    Caching-Mechanismen.
    """

# Class level cache for improved memory efficiency
    _scan_cache = {}
    _cache_lock = threading.RLock()
    _cache_hit_count = 0
    _cache_miss_count = 0

# Class settings for adaptive performance
    _settings = {
        'use_threading': os.cpu_count() and os.cpu_count() > 2,
        'max_threads': max(1, min(8, (os.cpu_count() or 4) // 2)),
        'min_files_for_threading': 1000,
        'batch_size_base': 100,
        'cache_ttl': 300,  # Seconds, how long cache is valid
        'max_cache_entries': 10,
        'skip_hidden_dirs': True,
        'skip_system_dirs': True,
        'max_scan_depth': 20,  # Prevents excessively deep recursion
    }

# Ignore certain system and hidden directories
    _ignored_dirs = {
        '.git', '.svn', '.hg', '__pycache__', 'node_modules', '.vscode',
        '.idea', 'System Volume Information', '$RECYCLE.BIN', 'Recovery',
        '$Windows.~BT', '$Windows.~WS', 'Windows', 'Program Files', 'Program Files (x86)'
    }

# Performance metrics for adaptive adaptation
    _performance_metrics = {
        'last_scan_time': 0,
        'last_files_per_second': 0,
        'filesystem_latency': 0.001,  # Standardwert in Sekunden
    }

    def __init__(self, filter_extensions: Optional[List[str]] = None, max_workers: int = None):
        """
        Initialisiert einen neuen adaptiven ROM-Scanner.

        Args:
            filter_extensions: Optionale Liste von Dateierweiterungen zum Filtern (ohne Punkt)
            max_workers: Maximale Anzahl an Worker-Threads (None für automatische Bestimmung)
        """
        super().__init__(filter_extensions, max_workers)

# Extended statistics
        self.stats.update({
            'hidden_dirs_skipped': 0,
            'hidden_files_skipped': 0,
            'unsupported_files_skipped': 0,
            'dirs_processed': 0,
            'cached_results_used': 0
        })

# Adaptive parameters based on system performance
        self._adaptive_params = {
            'threading_enabled': self.__class__._settings['use_threading'],
            'batch_size_adjusted': self.__class__._settings['batch_size_base'],
            'is_slow_filesystem': False,
        }

# Compiled regex pattern for Rome recognition
        self._regex_cache = {
            'rom_number': re.compile(r'[\(\[]?\s*[rR]om\s*\d+\s*[\)\]]?'),
            'disk_number': re.compile(r'[\(\[]?\s*[dD]is[ck]\s*\d+\s*[\)\]]?'),
            'version_pattern': re.compile(r'[\(\[]?\s*[vV](\d+(\.\d+)*)\s*[\)\]]?'),
            'region_pattern': re.compile(r'[\(\[]?\s*(US|USA|EUR|Europe|JP|Japan|PAL|NTSC)\s*[\)\]]?')
        }

    def scan_directory_adaptive(self, directory_path: Union[str, Path],
                               recursive: bool = False,
                               use_cache: bool = True) -> List[ROMMetadata]:
        """
        Durchsucht ein Verzeichnis mit adaptiver Leistungsanpassung nach ROM-Dateien.

        Args:
            directory_path: Zu durchsuchendes Verzeichnis
            recursive: Ob Unterverzeichnisse rekursiv durchsucht werden sollen
            use_cache: Ob der Cache verwendet werden soll

        Returns:
            Liste von ROMMetadata-Objekten
        """
        path_obj = Path(directory_path)
        if not path_obj.exists() or not path_obj.is_dir():
            logger.error(f"Verzeichnis existiert nicht oder ist kein Verzeichnis: {directory_path}")
            return []

# Cache check for quick results
        if use_cache:
            with self.__class__._cache_lock:
                cache_key = str(directory_path)
                current_time = time.time()

                if cache_key in self.__class__._scan_cache:
                    cache_entry = self.__class__._scan_cache[cache_key]
                    cache_age = current_time - cache_entry['timestamp']

                    if cache_age < self.__class__._settings['cache_ttl']:
                        self.__class__._cache_hit_count += 1
                        self.stats['cached_results_used'] += 1
                        logger.debug(f"Cache-Treffer für {directory_path} (Alter: {cache_age:.1f}s)")
                        return cache_entry['results']
                    else:
# Cache entry expired
                        self.__class__._cache_miss_count += 1
                else:
                    self.__class__._cache_miss_count += 1

# Measure the file system performance for adaptive optimization
        self._measure_filesystem_performance(path_obj)

# Decide which scan method is used based on the file system performance
        start_time = time.time()

        if self._should_use_threading(path_obj):
# Use parallel scanning for large directories or fast file system
            results = self.scan_directory_parallel(directory_path, recursive)
        else:
# Use sequential scanning for small directories or slow file systems
            results = super().scan_directory(directory_path, recursive)

# Optimize parameters for future scans
        scan_duration = time.time() - start_time
        files_per_second = len(results) / max(0.001, scan_duration)

        self._adjust_adaptive_parameters(files_per_second, self.stats['dirs_processed'], scan_duration)

# Save results in the cache for future inquiries
        if use_cache and results:
            with self.__class__._cache_lock:
                self.__class__._scan_cache[str(directory_path)] = {
                    'results': results,
                    'timestamp': time.time(),
                    'file_count': len(results)
                }

# Limit cache size
                if len(self.__class__._scan_cache) > self.__class__._settings['max_cache_entries']:
# Remove the oldest cache entry
                    oldest_key = min(self.__class__._scan_cache.keys(),
                                    key=lambda k: self.__class__._scan_cache[k]['timestamp'])
                    del self.__class__._scan_cache[oldest_key]

        return results

    def _measure_filesystem_performance(self, directory_path: Path) -> None:
        """
        Misst die Dateisystemleistung für optimale Anpassung.

        Args:
            directory_path: Zu testendes Verzeichnis
        """
        try:
# Small sample of file access for latency estimate
            sample_size = min(20, sum(1 for _ in directory_path.iterdir()))
            if sample_size == 0:
                return

            start_time = time.time()
            file_count = 0

# Go through a small sample of files
            for entry in directory_path.iterdir():
                if file_count >= sample_size:
                    break

                try:
                    if entry.is_file():
# Mass time for basic file operations
                        _ = entry.stat()
                        file_count += 1
                except (PermissionError, OSError):
                    continue

# Calculate average latency per file
            if file_count > 0:
                latency = (time.time() - start_time) / file_count
                self.__class__._performance_metrics['filesystem_latency'] = latency

# Set flag for slow file system
                self._adaptive_params['is_slow_filesystem'] = latency > 0.005  # 5ms als Schwelle

                logger.debug(f"Dateisystem-Latenz: {latency*1000:.2f}ms, Langsames FS: {self._adaptive_params['is_slow_filesystem']}")

        except Exception as e:
            logger.warning(f"Fehler bei der Dateisystem-Leistungsmessung: {e}")

    def _should_use_threading(self, directory_path: Path) -> bool:
        """
        Entscheidet, ob Threading basierend auf Verzeichnisgröße und Dateisystemleistung verwendet werden soll.

        Args:
            directory_path: Zu analysierendes Verzeichnis

        Returns:
            True, wenn Threading verwendet werden soll, sonst False
        """
# Better use sequential scanning in slow file systems
        if self._adaptive_params['is_slow_filesystem']:
            return False

        try:
# Treasures directory size by sampling
            dir_count = 0
            file_count = 0

            with os.scandir(str(directory_path)) as it:
                for entry in it:
                    try:
                        if entry.is_dir():
                            dir_count += 1
                        elif entry.is_file() and self._is_valid_extension(Path(entry.path)):
                            file_count += 1

# Cancel early if we have enough information
                        if dir_count >= 10 and file_count >= 100:
                            break
                    except (PermissionError, OSError):
                        continue

# Use threading if:
# 1. Sufficient subdirectaries for parallelization (min. 3)
# 2. Sufficient files for better performance than sequential
            min_dirs_for_threading = 3
            return (dir_count >= min_dirs_for_threading or
                    file_count >= self.__class__._settings['min_files_for_threading'])

        except Exception:
# Do not use threading in the event of error
            return False

    def _is_valid_extension(self, file_path: Path) -> bool:
        """
        Prüft, ob die Datei eine gültige ROM-Erweiterung hat.

        Args:
            file_path: Zu prüfender Dateipfad

        Returns:
            True, wenn die Datei eine gültige ROM-Erweiterung hat
        """
        extension = file_path.suffix.lstrip('.').lower()
        return extension in self.filter_extensions

    def _adjust_adaptive_parameters(self, files_per_second: float, dirs_scanned: int, total_time: float) -> None:
        """
        Passt adaptive Parameter für künftige Scans basierend auf Leistungsmetriken an.

        Args:
            files_per_second: Durchsatz (Dateien pro Sekunde)
            dirs_scanned: Anzahl der durchsuchten Verzeichnisse
            total_time: Gesamtzeit des Scans in Sekunden
        """
        try:
# Adjust the batch size
            if files_per_second > 1000:
# Very fast file system
                self._adaptive_params['batch_size_adjusted'] = min(500, int(self._adaptive_params['batch_size_adjusted'] * 1.5))
            elif files_per_second < 100:
# Slow file system
                self._adaptive_params['batch_size_adjusted'] = max(20, int(self._adaptive_params['batch_size_adjusted'] * 0.8))

# Adjust threading decision
            if dirs_scanned < 10 or total_time < 1.0:
# Small directory structure - disable threading
                self._adaptive_params['threading_enabled'] = False
            elif dirs_scanned > 100 and total_time > 5.0 and files_per_second > 200:
# Large directory structure with good performance - activate threading
                self._adaptive_params['threading_enabled'] = True

# Update performance metrics
            self.__class__._performance_metrics['last_scan_time'] = total_time
            self.__class__._performance_metrics['last_files_per_second'] = files_per_second

            logger.debug(f"Adaptive Parameter angepasst: Batch-Größe={self._adaptive_params['batch_size_adjusted']}, "
                        f"Threading={self._adaptive_params['threading_enabled']}")

        except Exception as e:
# Do not change parameters in the event of errors
            logger.warning(f"Fehler bei Anpassung der adaptiven Parameter: {e}")

    @classmethod
    def clear_cache(cls) -> None:
        """Löscht den Scanner-Cache."""
        with cls._cache_lock:
            cls._scan_cache.clear()
            cls._cache_hit_count = 0
            cls._cache_miss_count = 0
            logger.debug("Scanner-Cache wurde gelöscht")

    @property
    def cache_stats(self) -> Dict[str, Any]:
        """
        Gibt Cache-Statistiken zurück.

        Returns:
            Dict mit Cache-Statistiken
        """
        with self.__class__._cache_lock:
            hits = self.__class__._cache_hit_count
            misses = self.__class__._cache_miss_count
            total = hits + misses
            hit_rate = (hits / total) * 100 if total > 0 else 0
            return {
                'hits': hits,
                'misses': misses,
                'hit_rate': hit_rate,
                'cache_size': len(self.__class__._scan_cache),
                'max_cache_size': self.__class__._settings['max_cache_entries']
            }

    def get_performance_profile(self) -> Dict[str, Any]:
        """
        Gibt das aktuelle Leistungsprofil des Scanners zurück.

        Returns:
            Dict mit Leistungsmetriken
        """
        return {
            'filesystem_latency_ms': self.__class__._performance_metrics['filesystem_latency'] * 1000,
            'last_scan_time': self.__class__._performance_metrics['last_scan_time'],
            'files_per_second': self.__class__._performance_metrics['last_files_per_second'],
            'is_slow_filesystem': self._adaptive_params['is_slow_filesystem'],
            'threading_enabled': self._adaptive_params['threading_enabled'],
            'batch_size': self._adaptive_params['batch_size_adjusted']
        }


def scan_directory_adaptive(directory_path: Union[str, Path],
                           recursive: bool = False,
                           filter_extensions: Optional[List[str]] = None,
                           use_cache: bool = True) -> List[ROMMetadata]:
    """
    Durchsucht ein Verzeichnis adaptiv nach ROM-Dateien (Komfortfunktion).

    Args:
        directory_path: Zu durchsuchendes Verzeichnis
        recursive: Ob Unterverzeichnisse rekursiv durchsucht werden sollen
        filter_extensions: Optionale Liste von Dateierweiterungen zum Filtern
        use_cache: Ob der Cache verwendet werden soll

    Returns:
        Liste von ROMMetadata-Objekten
    """
    scanner = AdaptiveScanner(filter_extensions)
    return scanner.scan_directory_adaptive(directory_path, recursive, use_cache)


def get_scanner_performance_stats() -> Dict[str, Any]:
    """
    Gibt die aktuellen Scanner-Leistungsstatistiken zurück.

    Returns:
        Dict mit kombinierten Cache- und Leistungsmetriken
    """
    scanner = AdaptiveScanner()
    cache_stats = scanner.cache_stats
    perf_stats = scanner.get_performance_profile()

# Combine statistics
    combined_stats = {**cache_stats, **perf_stats}
    return combined_stats
