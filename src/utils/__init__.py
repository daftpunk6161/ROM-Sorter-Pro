"""
ROM Sorter Pro - Utils Modul

Dieses Paket enthält Utility-Funktionen und -Klassen für die ROM-Sorter-Pro-Anwendung.
"""

from functools import lru_cache
from pathlib import Path
import os
import re
import logging
from typing import Tuple, Optional, List, Dict, Any, Union

# Module exports for easier use
try:
    from .fuzzy_matching import (
        fuzz_ratio, fuzz_partial_ratio, fuzz_token_sort_ratio,
        fuzz_token_set_ratio, ProcessMatch
    )
except ImportError:
    pass  # Module may not yet

try:
    from .logging_enhanced import (
        TRACE, VERBOSE, ColoredFormatter, JSONFormatter, LogMetricsHandler
    )
except ImportError:
    pass  # Module may not yet

try:
    from .performance import (
        measure_time, measure_function, PerformanceMetric, PerformanceMonitor,
        get_performance_report
    )
except ImportError:
    pass  # Module may not yet

# Wrapper for functions that are still imported from utils.py
# This enables a Gentle Migration
logger = logging.getLogger(__name__)

# Perform the charging message for debugging purposes
logger.info("Utils-Modul mit Wrapper-Funktionen geladen")

@lru_cache(maxsize=1000)
def detect_console_by_extension_cached(filename: str) -> str:
    """
    Erkennt die Konsole anhand der Dateiendung mit Caching.

    Diese Funktion ist ein Wrapper, der die Funktionalität von src.utils.detect_console_by_extension_cached
    repliziert und die Migration erleichtert.

    Args:
        filename: Der Dateiname oder Pfad

    Returns:
        Erkannte Konsole oder "Unknown"
    """
    path_obj = Path(filename)
    extension = path_obj.suffix.lower()

    from src.database.console_db import get_console_for_extension
    console = get_console_for_extension(extension)

    return console if console else "Unknown"

def get_all_rom_extensions(include_dot: bool = False) -> List[str]:
    """
    Wrapper zu core.rom_utils.get_all_rom_extensions für Abwärtskompatibilität.

    Args:
        include_dot: Ob der Punkt am Anfang der Erweiterung enthalten sein soll

    Returns:
        Liste aller unterstützten Dateierweiterungen
    """
    from src.core.rom_utils import get_all_rom_extensions as _get_all_rom_extensions
    return _get_all_rom_extensions(include_dot)

@lru_cache(maxsize=1000)
def detect_console_fast(filename: str, file_path: Optional[str] = None) -> Tuple[str, float]:
    """
    Schnelle Konsolenerkennung basierend auf Dateiname und Dateiendung.

    Diese Funktion ist ein Wrapper zur Funktion in console_detector.py und ermöglicht eine
    konsistente Importstruktur über das gesamte Projekt.

    Args:
        filename: ROM-Dateiname
        file_path: Optionaler vollständiger Dateipfad

    Returns:
        Tupel mit (Konsolenname, Konfidenzwert)
    """
    from src.detectors.console_detector import detect_console_fast as _detect_console_fast
    return _detect_console_fast(filename, file_path)

def is_chd_file(file_path: str) -> bool:
    """
    Überprüft, ob eine Datei im CHD-Format vorliegt.

    Diese Funktion ist ein Wrapper zur Funktion in chd_detector.py und ermöglicht eine
    konsistente Importstruktur über das gesamte Projekt.

    Args:
        file_path: Pfad zur zu prüfenden Datei

    Returns:
        True wenn es sich um eine CHD-Datei handelt, sonst False
    """
    from src.detectors.chd_detector import is_chd_file as _is_chd_file
    return _is_chd_file(file_path)

def detect_console_from_chd(file_path: str) -> Tuple[str, float]:
    """
    Erkennt die Konsole aus einer CHD-Datei.

    Diese Funktion ist ein Wrapper zur Funktion in chd_detector.py und ermöglicht eine
    konsistente Importstruktur über das gesamte Projekt.

    Args:
        file_path: Pfad zur CHD-Datei

    Returns:
        Tuple aus (console_name, confidence)
    """
    from src.detectors.chd_detector import detect_console_from_chd as _detect_console_from_chd
    return _detect_console_from_chd(file_path)

def is_archive_file(file_path: str) -> bool:
    """
    Überprüft, ob eine Datei ein Archiv ist.

    Diese Funktion ist ein Wrapper zur Funktion in archive_detector.py und ermöglicht eine
    konsistente Importstruktur über das gesamte Projekt.

    Args:
        file_path: Pfad zur zu prüfenden Datei

    Returns:
        True wenn es sich um ein Archiv handelt, sonst False
    """
    from src.detectors.archive_detector import is_archive_file as _is_archive_file
    return _is_archive_file(file_path)

def detect_console_from_archive(file_path: str) -> Tuple[str, float]:
    """
    Erkennt die Konsole aus einem Archiv.

    Diese Funktion ist ein Wrapper zur Funktion in archive_detector.py und ermöglicht eine
    konsistente Importstruktur über das gesamte Projekt.

    Args:
        file_path: Pfad zum Archiv

    Returns:
        Tuple aus (console_name, confidence)
    """
    from src.detectors.archive_detector import detect_console_from_archive as _detect_console_from_archive
    return _detect_console_from_archive(file_path)


# Import wrapper functions for downward compatibility with optimized_scanner.py
# These imports ensure that existing code, the Optimized_Scanner.py uses, uses
# Furthermore, the new scanner modules are used instead.
try:
    from .scanner_compat import (
        OptimizedFileScanner,
        scan_directory as optimized_scan_directory,
        clear_cache as clear_scanner_cache,
        get_cache_stats as get_scanner_cache_stats
    )
except ImportError:
    # Fallback if scanner_compat is not available
    logging.warning("Die Scanner-Kompatibilitätsmodule konnten nicht importiert werden.")
