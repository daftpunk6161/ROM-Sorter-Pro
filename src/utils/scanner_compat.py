"""Wrapper Functions for Outdated Views from Optimized_Scanner.py This module offer a compatibility layer between the outdated optimized_scanner.py and the new adaptive scanner implementation. Optimizations: - Delayed Imports for Better Start Time - Efficient Storage Use BY Lazy Initialization -Improved Cache Use and Management - Extended Error Treatment and Logging -Performance Monitoring Integration"""

import warnings
import logging
import time
import sys
from pathlib import Path
from typing import List, Union, Optional, Dict, Any, Callable
from functools import wraps
import threading

# Logger Setup with Zero Handler AS A Default
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Lazy loading of modules for improved start time
_lazy_imports = {}
_import_lock = threading.RLock()

def _import_scanner():
    """Imports the scanner modules with error treatment"""
    try:
        with _import_lock:
            if 'scanner' not in _lazy_imports:
                # Versuche relativen Import
                from ..scanning import adaptive_scanner
                _lazy_imports['scanner'] = {
                    'scan_directory_adaptive': adaptive_scanner.scan_directory_adaptive,
                    'AdaptiveScanner': adaptive_scanner.AdaptiveScanner,
                    'get_scanner_performance_stats': adaptive_scanner.get_scanner_performance_stats
                }
    except (ImportError, ValueError) as e:
        logger.warning(f"Relativer Import fehlgeschlagen: {e}, versuche absoluten Import")
        try:
            # Fallback zum absoluten Import
            from src.scanning import adaptive_scanner
            _lazy_imports['scanner'] = {
                'scan_directory_adaptive': adaptive_scanner.scan_directory_adaptive,
                'AdaptiveScanner': adaptive_scanner.AdaptiveScanner,
                'get_scanner_performance_stats': adaptive_scanner.get_scanner_performance_stats
            }
        except ImportError as e:
            logger.error(f"Fehler beim Importieren der Scanner-Module: {e}")
            # Provide minimal functionality
            class FallbackScanner:
                def __init__(self, filter_extensions=None): pass
                def scan_directory_adaptive(self, *args, **kwargs): return []
                @classmethod
                def clear_cache(cls): pass
            
            _lazy_imports['scanner'] = {
                'scan_directory_adaptive': lambda *args, **kwargs: [],
                'AdaptiveScanner': FallbackScanner,
                'get_scanner_performance_stats': lambda: {'error': str(e)}
            }

def _import_performance():
    """Imports the performance modules with error treatment"""
    try:
        with _import_lock:
            if 'performance' not in _lazy_imports:
                try:
                    # Versuche relativen Import
                    from ..utils import performance
                    _lazy_imports['performance'] = {
                        'measure_time': performance.measure_time,
                        'monitor': performance.PerformanceMonitor.get_instance()
                    }
                except (ImportError, ValueError):
                    # Fallback zum absoluten Import
                    from src.utils.performance import measure_time, PerformanceMonitor
                    _lazy_imports['performance'] = {
                        'measure_time': measure_time,
                        'monitor': PerformanceMonitor.get_instance()
                    }
    except ImportError as e:
        logger.warning(f"Performance-Module nicht verfügbar: {e}")
        # Dummy-Funktionen bereitstellen
        _lazy_imports['performance'] = {
            'measure_time': lambda func=None, **kwargs: func if func else lambda f: f,
            'monitor': type('DummyMonitor', (), {
                'record_operation_time': lambda *args, **kwargs: None
            })
        }

def with_performance_tracking(func):
    """Decorator for performance tracking"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            duration = time.perf_counter() - start_time
            try:
                # Performance monitoring only if available
                if 'performance' not in _lazy_imports:
                    _import_performance()
                perf = _lazy_imports.get('performance', {})
                if perf and 'monitor' in perf:
                    perf['monitor'].record_operation_time(f"compat_{func.__name__}", duration)
            except Exception:
                pass  # Performance-Monitoring ist optional
    return wrapper

@with_performance_tracking
def scan_directory(directory: str, progress_callback=None, stop_event=None, use_cache=True) -> List[Path]:
    """Wrapper for the outdated scan_directory call from Optimized_Scanner.py. Args: Directory: Directory to be searched Progress_Callback: Callback function for progress notifications Stop_event: Event to stop the scan use_cache: Whether the cache should be used Return: List of ROM file paths"""
    warnings.warn(
        "Die Verwendung von optimized_scanner.py ist veraltet. "
        "Bitte verwenden Sie stattdessen src.scanning.scan_directory_adaptive.",
        DeprecationWarning, stacklevel=2
    )

    try:
        # Stelle sicher, dass Scanner-Module geladen sind
        if 'scanner' not in _lazy_imports:
            _import_scanner()
        
        scanner_module = _lazy_imports['scanner']
        scanner = scanner_module['AdaptiveScanner']()

        # If progress_callback is available, we adjust it for the new API
        if progress_callback:
            def adapted_callback(completed, total, percentage):
                try:
                    progress_callback(percentage, f"{completed}/{total} Dateien")
                except Exception as e:
                    logger.warning(f"Fehler im Progress-Callback: {e}")

            # Use scan_with_pogress_callback if available
            if hasattr(scanner, 'scan_with_progress_callback'):
                results = scanner.scan_with_progress_callback(
                    directory_path=directory,
                    progress_callback=adapted_callback,
                    recursive=True
                )
            else:
                # Fallback for older scanner versions
                results = scanner.scan_directory_adaptive(directory, recursive=True, use_cache=use_cache)
        else:
            # Without callback we use scan_directory_adaptive
            results = scanner.scan_directory_adaptive(directory, recursive=True, use_cache=use_cache)

        # Convert rommetadata to Path for downward compatibility
        if results and hasattr(results[0], 'path'):
            return [item.path for item in results]
        return results  # Already a List of Paths Or Empty
        
    except Exception as e:
        logger.error(f"Fehler beim Scannen von {directory}: {e}")
        return []

@with_performance_tracking
def clear_cache():
    """Wrapper for the outdated Clear_Cache call from Optimized_Scanner.py."""
    warnings.warn(
        "Die Verwendung von optimized_scanner.py ist veraltet. "
        "Bitte verwenden Sie stattdessen src.scanning.AdaptiveScanner.clear_cache.",
        DeprecationWarning, stacklevel=2
    )

    try:
        # Stelle sicher, dass Scanner-Module geladen sind
        if 'scanner' not in _lazy_imports:
            _import_scanner()
            
        scanner_module = _lazy_imports['scanner']
        scanner_module['AdaptiveScanner'].clear_cache()
        logger.debug("Scanner-Cache erfolgreich gelöscht")
    except Exception as e:
        logger.warning(f"Fehler beim Löschen des Scanner-Caches: {e}")

@with_performance_tracking
def get_cache_stats() -> Dict[str, Any]:
    """Wrapper for the outdated Cache_Stats call from Optimized_Scanner.py. Return: Dict with cache statistics"""
    warnings.warn(
        "Die Verwendung von optimized_scanner.py ist veraltet. "
        "Bitte verwenden Sie stattdessen src.scanning.get_scanner_performance_stats.",
        DeprecationWarning, stacklevel=2
    )

    try:
        # Stelle sicher, dass Scanner-Module geladen sind
        if 'scanner' not in _lazy_imports:
            _import_scanner()
            
        scanner_module = _lazy_imports['scanner']
        return scanner_module['get_scanner_performance_stats']()
    except Exception as e:
        logger.warning(f"Fehler beim Abrufen der Cache-Statistiken: {e}")
        return {
            'error': str(e),
            'hits': 0,
            'misses': 0,
            'hit_rate': 0,
            'cache_size': 0,
            'max_cache_size': 0
        }

class OptimizedFileScanner:
    """Outdated Optimized Files Scanner Class from Optimized_Scanner.py. This Class ONLY SERVES AS A Wrapper and Should no Longer Be used. Optimizations: - Lazy Loading of Dependencies - More Efficient Storage Use - Improved Error Treatment - Intelligent Caching for Better Performance"""

    def __init__(self, extensions=None):
        """Initialized a new optimized file scanner (wrapper). ARGS: Extensions: Optional List of File Extensions for Filtering"""
        warnings.warn(
            "Die OptimizedFileScanner-Klasse ist veraltet. "
            "Bitte verwenden Sie stattdessen src.scanning.AdaptiveScanner.",
            DeprecationWarning, stacklevel=2
        )

        # Stelle sicher, dass Scanner-Module geladen sind
        if 'scanner' not in _lazy_imports:
            _import_scanner()
            
        scanner_module = _lazy_imports['scanner']
        # Create real scanner with delayed initialization
        self._real_scanner = scanner_module['AdaptiveScanner'](filter_extensions=extensions)
        logger.debug("OptimizedFileScanner-Wrapper initialisiert")

    @with_performance_tracking
    def scan_directory(self, directory: str, progress_callback=None, stop_event=None, use_cache=True) -> List[Path]:
        """Scan a Directory (wrapper method). ARGS: Directory: Directory to Be Searched Progress_Callback: Callback Function for Progress Notifications Stop_event: Event to stop the scan use_cache: Whather the Cache Should be used: List of Rom File Paths"""
        try:
            # Delegiers to the global wrapper function
            return scan_directory(directory, progress_callback, stop_event, use_cache)
        except Exception as e:
            logger.error(f"Fehler beim Scannen von {directory}: {e}")
            return []

    @classmethod
    @with_performance_tracking
    def clear_cache(cls):
        """Deletes the scanner cache (wrapper method)."""
        clear_cache()

    @property
    @with_performance_tracking
    def cache_stats(self):
        """Gives back cache statistics (wrapper method). Return: Dict with cache statistics"""
        return get_cache_stats()
