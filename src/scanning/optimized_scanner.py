# -*-coding: utf-8-*-
"""
ROM Sorter Pro - VERALTET: Optimierter Datei-Scanner v1.0.0

ACHTUNG: Dieses Modul ist veraltet und wird in zukünftigen Versionen entfernt.
Bitte verwenden Sie stattdessen die neuen Scanner-Module in src.scanning.

PERFORMANCE OPTIMIERUNGEN v1.0.0:
- Hochleistungs-Threading für große Verzeichnisstrukturen
- Intelligentes Caching mit adaptiver Anpassung
- Adaptive Batch-Verarbeitung für optimalen Durchsatz
- Tiefenbeschränkte Rekursion für schnellere Suche
- Adaptive Einstellungen basierend auf Filesystem-Performance
- Optimierte Speichernutzung für große Verzeichnisse

Project:        ROM Sorter Pro
File:           src/optimized_scanner.py
Version:        1.0.0
Author:         cemal / daftpunk6161
Created:        12.08.2025
License:        MIT License
Python:         3.8+
"""

import os
import re
import time
import threading
import logging
import warnings
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from functools import lru_cache

# Provide warning - with improved performance through delayed import strategy
warnings.warn(
    "Das Modul optimized_scanner.py ist veraltet und wird in zukünftigen Versionen entfernt. "
    "Bitte verwenden Sie stattdessen die Module in src.scanning.",
    DeprecationWarning, stacklevel=2
)

# Logger Setup With Efficient Zero Handler AS A Default
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Optimized import strategy - imports only if necessary
# Use Lazy Loading and Caching for Imports
_imports = {
    'scanner': None,
    'compat': None
}

def _get_module(name):
    """Lädt ein Modul nur bei Bedarf"""
    global _imports
    if _imports[name] is None:
        try:
            if name == 'scanner':
# Relative import within the scanning package
                from . import adaptive_scanner
                _imports[name] = adaptive_scanner
            elif name == 'compat':
# Import of the compatibility module
                from ..utils import scanner_compat
                _imports[name] = scanner_compat
        except ImportError as e:
            logger.error(f"Fehler beim Importieren von {name}: {e}")
            raise
    return _imports[name]

# Simple wrapper functions for API compatibility
def scan_directory(directory: str, progress_callback=None, stop_event=None, use_cache=True) -> List[Path]:
    """
    Scannt ein Verzeichnis nach ROM-Dateien.
    
    Diese Funktion ist veraltet und delegiert an den neuen AdaptiveScanner.
    
    Args:
        directory: Zu durchsuchendes Verzeichnis
        progress_callback: Callback-Funktion für Fortschritt
        stop_event: Event zum Stoppen des Scans
        use_cache: Ob der Cache verwendet werden soll
        
    Returns:
        Liste von ROM-Dateipfaden
    """
    compat = _get_module('compat')
    return compat.scan_directory(directory, progress_callback, stop_event, use_cache)

def clear_cache():
    """Löscht den Scan-Cache (delegiert an AdaptiveScanner)."""
    compat = _get_module('compat')
    compat.clear_cache()

def get_cache_stats():
    """
    Gibt Statistiken zum Cache zurück.
    
    Returns:
        Dict mit Cache-Statistiken
    """
    compat = _get_module('compat')
    return compat.get_cache_stats()

class OptimizedFileScanner:
    """
    Veraltete OptimizedFileScanner-Klasse.
    Diese Klasse ist nur noch ein Wrapper für die neue AdaptiveScanner-Klasse in src.scanning.
    Sie wird in zukünftigen Versionen entfernt werden.
    """

# Lightweight class attributes with delegate patterns
    _cache_lock = threading.RLock()
    _settings = {
        'use_threading': os.cpu_count() and os.cpu_count() > 2,
        'max_threads': max(1, min(8, (os.cpu_count() or 4) // 2)),
        'min_files_for_threading': 1000,
        'batch_size_base': 100,
        'cache_ttl': 300,
        'max_cache_entries': 10,
        'skip_hidden_dirs': True,
        'skip_system_dirs': True,
        'max_scan_depth': 20,
    }

# Lightweight performance metrics (are not really used)
    _performance_metrics = {
        'last_scan_time': 0,
        'last_files_per_second': 0,
        'filesystem_latency': 0.001,
    }

    def __init__(self, extensions=None):
        """Scanner mit optionalem Erweiterungsfilter initialisieren."""
        compat = _get_module('compat')
        
# Direct delegation to optimized files from compat
        self._delegate = compat.OptimizedFileScanner(extensions)
        
# Lightweight statistics for API compatibility
        self.stats = {
            'hidden_dirs_skipped': 0,
            'hidden_files_skipped': 0,
            'unsupported_files_skipped': 0,
            'dirs_processed': 0,
            'cached_results_used': 0
        }
        
# Optimized extension test with LRU_Cache
        self.ROM_EXTENSIONS = set(ext.lower() for ext in extensions) if extensions else set()
        self._is_rom_file = lru_cache(maxsize=2048)(self._optimized_extension_check)

    def _optimized_extension_check(self, path):
        """Optimierter Check für ROM-Dateierweiterungen mit Delegation."""
        try:
            return self._delegate._real_scanner._is_valid_extension(path)
        except (AttributeError, TypeError):
# Fallback in the event that the delegation fails
            ext = path.suffix.lower()
            return ext.lstrip('.') in self.ROM_EXTENSIONS if self.ROM_EXTENSIONS else True

    def scan_directory(self, directory: str, progress_callback=None, stop_event=None, use_cache=True) -> List[Path]:
        """
        Scannt Verzeichnis nach ROM-Dateien mit optimaler Leistung und adaptiver Anpassung.
        
        Args:
            directory: Zu durchsuchendes Verzeichnis
            progress_callback: Callback-Funktion für Fortschritt
            stop_event: Event zum Stoppen des Scans
            use_cache: Ob der Cache verwendet werden soll
            
        Returns:
            Liste von ROM-Dateipfaden
        """
        try:
# Efficient delegation to the real scanner
            return self._delegate.scan_directory(directory, progress_callback, stop_event, use_cache)
        except Exception as e:
            logger.error(f"Fehler beim Scannen von {directory}: {e}")
            return []

# Methods for maintaining API compatibility (empty implementations)
    def _measure_filesystem_performance(self, directory):
        """Delegiert an AdaptiveScanner (leere Implementierung)."""
        pass
        
    def _should_use_threading(self, directory):
        """Delegiert an AdaptiveScanner (leere Implementierung)."""
        return False
        
    def _scan_sequential(self, directory, progress_callback=None):
        """Delegiert an AdaptiveScanner (leere Implementierung)."""
        return self.scan_directory(directory, progress_callback)
        
    def _scan_with_threading(self, directory, progress_callback=None):
        """Delegiert an AdaptiveScanner (leere Implementierung)."""
        return self.scan_directory(directory, progress_callback)
        
    def _thread_scan_worker(self, dirs, thread_id, progress_callback):
        """Delegiert an AdaptiveScanner (leere Implementierung)."""
        pass
        
    def _create_balanced_dir_chunks(self, dirs, num_chunks):
        """Delegiert an AdaptiveScanner (leere Implementierung)."""
        return [dirs]
        
    def _adjust_adaptive_parameters(self, files_per_second, dirs_scanned, total_time):
        """Delegiert an AdaptiveScanner (leere Implementierung)."""
        pass

    @classmethod
    def clear_cache(cls):
        """Löscht den Scanner-Cache."""
        compat = _get_module('compat')
        compat.clear_cache()

    @property
    def cache_stats(self):
        """
        Gibt Cache-Statistiken zurück.
        
        Returns:
            Dict mit Cache-Statistiken
        """
        compat = _get_module('compat')
        return compat.get_cache_stats()
