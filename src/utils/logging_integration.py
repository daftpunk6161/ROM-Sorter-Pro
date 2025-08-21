#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rom Sarter Pro - Logging Integration This Module Integrates The Various Logging Mechanisms of the Project and Provides A Uniform Interface for All Subsystems. It uses the existing module: - SRC.UTILS.LOGGER: Simple Logging - SRC.Utils.logging_enhanced: Extended Logging Functions - Src.Logging_config: Performance -Optimized Logging and Offers A Central Configuration for All Subsystems."""

import os
import sys
import logging
import logging.handlers
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Union
from datetime import datetime
from functools import wraps
from contextlib import contextmanager

# Import existierender Logging-Module
try:
    # Attempts to import the different logging modules
    from src.utils.logger import setup_logger
    from src.utils.logging_enhanced import ColoredFormatter, JsonFormatter
    from src.logging_config import FastFormatter

    # Set flags for available modules
    BASIC_LOGGING_AVAILABLE = True
    ENHANCED_LOGGING_AVAILABLE = True
    FAST_LOGGING_AVAILABLE = True
except ImportError as e:
    # In the case of import defects, corresponding flags set
    if 'logger' in str(e):
        BASIC_LOGGING_AVAILABLE = False
    else:
        BASIC_LOGGING_AVAILABLE = True

    if 'logging_enhanced' in str(e):
        ENHANCED_LOGGING_AVAILABLE = False
    else:
        ENHANCED_LOGGING_AVAILABLE = True

    if 'logging_config' in str(e):
        FAST_LOGGING_AVAILABLE = False
    else:
        FAST_LOGGING_AVAILABLE = True

# Konfigurationskonstanten
DEFAULT_LOG_LEVEL = logging.INFO
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_ENCODING = 'utf-8'

# Globaler Zustand
_initialized = False
_loggers: Dict[str, logging.Logger] = {}
_log_dir: Optional[Path] = None
_subsystem_levels: Dict[str, int] = {}
_performance_stats: Dict[str, Dict[str, Any]] = {}
_stats_lock = threading.RLock()

# Context for structured logging
_context_local = threading.local()


# Initialisierung des Logging-Systems
def initialize_logging(log_dir: Optional[str] = None,
                       level: int = DEFAULT_LOG_LEVEL,
                       use_colors: bool = True,
                       use_json: bool = False,
                       subsystem_levels: Optional[Dict[str, int]] = None) -> bool:
    """Initialized the integrated logging system. Args: Log_dir: List for log files (standard: 'logs') Level: General Log level (Standard: Info) use_colors: Activate colored console output use_json: Activate JSON logging for file output Subsystem_Levels: specific log levels for subsystems Return: True with successful initialization, otherwise false"""
    global _initialized, _log_dir, _subsystem_levels

    if _initialized:
        # Already Initialized, Log A Warning
        logger = logging.getLogger("logging_integration")
        logger.warning("Logging system was already initialized.")
        return False

    try:
        # Log-Verzeichnis konfigurieren
        if log_dir is None:
            _log_dir = Path('logs')
        else:
            _log_dir = Path(log_dir)

        # Make sure the log directory exists
        _log_dir.mkdir(parents=True, exist_ok=True)

        # Root-Logger konfigurieren
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # Alle bestehenden Handler entfernen
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Konsolenausgabe konfigurieren
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        if use_colors and ENHANCED_LOGGING_AVAILABLE:
            # Use colored formatting if available
            formatter = ColoredFormatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)
        elif FAST_LOGGING_AVAILABLE:
            # Use fast formatting if available
            formatter = FastFormatter(enable_colors=use_colors)
        else:
            # Standard-Formatierung als Fallback
            formatter = logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)

        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Haupt-Logdatei konfigurieren
        log_file = _log_dir / 'rom_sorter.log'
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT, encoding=LOG_ENCODING
        )
        file_handler.setLevel(level)

        if use_json and ENHANCED_LOGGING_AVAILABLE:
            # JSON formatting for structured logs
            formatter = JsonFormatter()
        else:
            # Standard formatting for text logs
            formatter = logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)

        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Separate Fehlerlog-Datei
        error_log = _log_dir / 'errors.log'
        error_handler = logging.handlers.RotatingFileHandler(
            error_log, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT, encoding=LOG_ENCODING
        )
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT))
        root_logger.addHandler(error_handler)

        # Subsystem-spezifische Log-Level
        if subsystem_levels:
            _subsystem_levels = subsystem_levels

        # Initialisierung abgeschlossen
        _initialized = True

        # Systeminformationen loggen
        logger = get_logger("logging_integration")
        logger.info(f"Logging-System initialisiert: Verzeichnis={_log_dir.absolute()}")
        logger.info(f"Python Version: {sys.version}")
        logger.info(f"Plattform: {sys.platform}")

        return True

    except Exception as e:
        # Fallback for basic configuration in the event of errors - without Stdout handler
        # Zuerst alle bestehenden Handler entfernen
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                root_logger.removeHandler(handler)

        # Just add one file handler, no stream handler
        log_dir = Path('logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        error_log = log_dir / 'error_init.log'

        file_handler = logging.FileHandler(error_log)
        file_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)

        logger = logging.getLogger("logging_integration")
        logger.error(f"Fehler bei der Initialisierung des Logging-Systems: {e}")
        logger.error(traceback.format_exc())
        return False


def get_logger(name: str) -> logging.Logger:
    """Returns A Configured Logger for the Specified Subsystem. ARGS: Name: Name of the Subsystem/Logger Return: Configured Logger"""
    # Check if the logger has already been created
    if name in _loggers:
        return _loggers[name]

    # Check Whether there is a specific level for the subsystem
    level = DEFAULT_LOG_LEVEL
    for subsystem, subsystem_level in _subsystem_levels.items():
        if name.startswith(subsystem):
            level = subsystem_level
            break

    # Logger erstellen
    if BASIC_LOGGING_AVAILABLE:
        # Use Setup_logger, if available
        logger = setup_logger(name, level)
    else:
        # Standard-Logger als Fallback
        logger = logging.getLogger(name)
        logger.setLevel(level)

    # Logger im Cache speichern
    _loggers[name] = logger

    return logger


@contextmanager
def log_context(**kwargs) -> None:
    """Context Manager for setting thread local context for logging. Args: ** Kwargs: key value pairs for the context"""
    # Alten Kontext speichern
    if not hasattr(_context_local, 'context'):
        _context_local.context = {}

    old_context = _context_local.context.copy()

    try:
        # Neuen Kontext setzen
        _context_local.context.update(kwargs)
        yield
    finally:
        # Kontext wiederherstellen
        _context_local.context = old_context


def log_performance(logger_name: str = None, operation: str = None, level: int = logging.DEBUG):
    """Decorator for the performance measurement of functions. Args: Logger_Name: Name of the logger to be used Operation: Name of the Operation (Standard: Function Name) Level: Log level for the performance report"""
    def decorator(func):
        nonlocal logger_name, operation

        if not logger_name:
            logger_name = func.__module__

        if not operation:
            operation = func.__qualname__

        # Logger abrufen
        logger = get_logger(logger_name)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Startzeit messen
            start_time = time.time()

            try:
                # Run out
                result = func(*args, **kwargs)
                return result
            finally:
                # Measure and log in the end time
                elapsed = time.time() - start_time
                logger.log(level, f"Performance: {operation} - {elapsed:.6f} Sekunden")

                # Statistik aktualisieren
                with _stats_lock:
                    if operation not in _performance_stats:
                        _performance_stats[operation] = {
                            'count': 0,
                            'total_time': 0.0,
                            'min_time': float('inf'),
                            'max_time': 0.0
                        }

                    stats = _performance_stats[operation]
                    stats['count'] += 1
                    stats['total_time'] += elapsed
                    stats['min_time'] = min(stats['min_time'], elapsed)
                    stats['max_time'] = max(stats['max_time'], elapsed)

        return wrapper

    return decorator


def log_exception(logger_name: str = None, level: int = logging.ERROR, reraise: bool = True):
    """Decorator for logging exceptions. Args: Logger_Name: Name of the logger to be used Level: Log level for the exception Reraise: Whether the exception should be continued"""
    def decorator(func):
        nonlocal logger_name

        if not logger_name:
            logger_name = func.__module__

        # Logger abrufen
        logger = get_logger(logger_name)

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Run out
                return func(*args, **kwargs)
            except Exception as e:
                # Ausnahme loggen
                logger.log(level, f"Ausnahme in {func.__qualname__}: {e}", exc_info=True)

                if reraise:
                    raise

        return wrapper

    return decorator


def get_performance_stats() -> Dict[str, Dict[str, Any]]:
    """Gives back the collected performance statistics. Return: Dict with performance statistics per operation"""
    with _stats_lock:
        stats = {}
        for op, op_stats in _performance_stats.items():
            if op_stats['count'] > 0:
                stats[op] = {
                    'count': op_stats['count'],
                    'total_time': op_stats['total_time'],
                    'avg_time': op_stats['total_time'] / op_stats['count'],
                    'min_time': op_stats['min_time'],
                    'max_time': op_stats['max_time']
                }
        return stats


def log_stats():
    """Logs the collected performance statistics."""
    stats = get_performance_stats()
    if not stats:
        return

    logger = get_logger("performance_stats")
    logger.info("=== Performance-Statistiken ===")

    for op, op_stats in stats.items():
        logger.info(f"{op}: {op_stats['count']} Aufrufe, "
                   f"Durchschnitt: {op_stats['avg_time']:.6f}s, "
                   f"Min: {op_stats['min_time']:.6f}s, "
                   f"Max: {op_stats['max_time']:.6f}s")


# Automatic logging of the performance statistics when ending
import atexit
atexit.register(log_stats)
