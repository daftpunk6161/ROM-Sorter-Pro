#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - Erweitertes Logging-Modul

Dieses Modul bietet eine verbesserte Logging-Funktionalität mit zusätzlichen Features:
- Automatische Rotation von Logdateien
- Farbiges Logging auf der Konsole
- Strukturiertes JSON-Logging für Maschinenlesbarkeit
- Leistungsmetriken und Prozessüberwachung
- Deduplizierung von Lognachrichten
"""

import os
import sys
import json
import logging
import logging.handlers
import time
import traceback
import platform
import socket
import threading
from typing import Dict, List, Any, Optional, Union, Set, Tuple
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter


# Benutzerdefinierte Log-Ebenen
TRACE = 5  # Detaillierteres Debug-Level
VERBOSE = 15  # Between debug and info


class ColoredFormatter(logging.Formatter):
    """Formatter für farbige Konsolenausgabe."""

    # ANSI-Farbcodes
    COLORS = {
        'BLACK': '\033[0;30m',
        'RED': '\033[0;31m',
        'GREEN': '\033[0;32m',
        'YELLOW': '\033[0;33m',
        'BLUE': '\033[0;34m',
        'MAGENTA': '\033[0;35m',
        'CYAN': '\033[0;36m',
        'WHITE': '\033[0;37m',
        'BOLD_RED': '\033[1;31m',
        'BOLD_GREEN': '\033[1;32m',
        'BOLD_YELLOW': '\033[1;33m',
        'RESET': '\033[0m'
    }

    LEVEL_COLORS = {
        TRACE: COLORS['BLUE'],
        logging.DEBUG: COLORS['CYAN'],
        VERBOSE: COLORS['WHITE'],
        logging.INFO: COLORS['GREEN'],
        logging.WARNING: COLORS['YELLOW'],
        logging.ERROR: COLORS['RED'],
        logging.CRITICAL: COLORS['BOLD_RED']
    }

    def __init__(self, fmt: str = None, datefmt: str = None, use_colors: bool = True):
        """
        Initialisiert den farbigen Formatter.

        Args:
            fmt: Format-String
            datefmt: Datumsformat
            use_colors: Aktiviert/deaktiviert Farbcodes
        """
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """
        Formatiert einen Log-Record mit Farben.

        Args:
            record: Zu formatierender LogRecord

        Returns:
            Formatierte Log-Nachricht
        """
        original_msg = super().format(record)

        if not self.use_colors:
            return original_msg

        color = self.LEVEL_COLORS.get(record.levelno, self.COLORS['RESET'])
        return f"{color}{original_msg}{self.COLORS['RESET']}"


class JsonFormatter(logging.Formatter):
    """Formatter für strukturiertes JSON-Logging."""

    def __init__(self, include_extra: bool = True):
        """
        Initialisiert den JSON-Formatter.

        Args:
            include_extra: Ob zusätzliche Felder eingeschlossen werden sollen
        """
        super().__init__()
        self.include_extra = include_extra
        self.hostname = socket.gethostname()
        self.default_fields = {
            'system': platform.system(),
            'node': self.hostname,
            'app': 'rom-sorter-pro',
            'pid': os.getpid(),
            'thread_name': threading.current_thread().name
        }

    def format(self, record: logging.LogRecord) -> str:
        """
        Formatiert einen Log-Record als JSON.

        Args:
            record: Zu formatierender LogRecord

        Returns:
            JSON-formatierte Log-Nachricht
        """
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage()
        }

        # Add standard fields
        log_data.update(self.default_fields)

        # Add thread ID
        log_data['thread_id'] = record.thread

        # Exception-Informationen, falls vorhanden
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'value': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        # Additional fields from the Record
        if self.include_extra and hasattr(record, 'extra'):
            log_data.update(record.extra)

        # In JSON konvertieren
        return json.dumps(log_data)


class DedupHandler(logging.Handler):
    """Handler, der duplizierte Log-Nachrichten dedupliziert."""

    def __init__(self, target_handler: logging.Handler, interval: float = 5.0, capacity: int = 1000):
        """
        Initialisiert den Deduplizierungs-Handler.

        Args:
            target_handler: Ziel-Handler für deduplizierte Nachrichten
            interval: Intervall in Sekunden für die Ausgabe von Zusammenfassungen
            capacity: Maximale Anzahl von zu speichernden eindeutigen Nachrichten
        """
        super().__init__()
        self.target_handler = target_handler
        self.interval = interval
        self.capacity = capacity

        self.message_counts: Counter = Counter()
        self.last_flush_time = time.time()
        self.lock = threading.RLock()

    def emit(self, record: logging.LogRecord) -> None:
        """
        Verarbeitet einen LogRecord.

        Args:
            record: Zu verarbeitender LogRecord
        """
        with self.lock:
            # Count message
            message = record.getMessage()
            self.message_counts[message] += 1

            # Check whether the interval has expired
            current_time = time.time()
            if current_time - self.last_flush_time >= self.interval:
                self._flush_counts()
                self.last_flush_time = current_time

            # Spend immediately with the first message
            if self.message_counts[message] == 1:
                self.target_handler.handle(record)

            # Capacity test
            if len(self.message_counts) > self.capacity:
                self._flush_counts()

    def _flush_counts(self) -> None:
        """Gibt Zusammenfassungen für duplizierte Nachrichten aus."""
        for message, count in self.message_counts.items():
            if count > 1:
                summary_record = logging.LogRecord(
                    name="dedup",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=f"Wiederholte Nachricht ({count}x): {message}",
                    args=(),
                    exc_info=None
                )
                self.target_handler.handle(summary_record)

        # Reset counter
        self.message_counts.clear()


class PerformanceMetricsHandler(logging.Handler):
    """Handler zum Sammeln und Ausgeben von Leistungsmetriken."""

    def __init__(self, interval: float = 60.0):
        """
        Initialisiert den Leistungsmetriken-Handler.

        Args:
            interval: Intervall für die Ausgabe von Metriken in Sekunden
        """
        super().__init__()
        self.interval = interval
        self.last_metrics_time = time.time()

        self.levels_count: Dict[int, int] = defaultdict(int)
        self.modules_count: Dict[str, int] = defaultdict(int)
        self.message_count = 0
        self.start_time = time.time()

        self.lock = threading.RLock()

    def emit(self, record: logging.LogRecord) -> None:
        """
        Verarbeitet einen LogRecord und sammelt Metriken.

        Args:
            record: Zu verarbeitender LogRecord
        """
        with self.lock:
            # Metriken aktualisieren
            self.levels_count[record.levelno] += 1
            self.modules_count[record.module] += 1
            self.message_count += 1

            # Metriken ausgeben, wenn Intervall abgelaufen ist
            current_time = time.time()
            if current_time - self.last_metrics_time >= self.interval:
                self._report_metrics()
                self.last_metrics_time = current_time

    def _report_metrics(self) -> None:
        """Gibt gesammelte Metriken aus."""
        if self.message_count == 0:
            return

        elapsed = time.time() - self.start_time
        if elapsed == 0:
            elapsed = 0.001  # Vermeide Division durch Null

        # Metriken berechnen
        msgs_per_sec = self.message_count / elapsed
        level_percentages = {
            logging.getLevelName(level): (count / self.message_count) * 100
            for level, count in self.levels_count.items()
        }
        top_modules = sorted(
            self.modules_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]  # Top 5 Module

        # Metriken-Nachricht erstellen
        metrics_record = logging.LogRecord(
            name="metrics",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=f"Logging-Metriken: {self.message_count} Nachrichten "
                f"({msgs_per_sec:.2f}/s), Verteilung: {level_percentages}, "
                f"Top-Module: {top_modules}",
            args=(),
            exc_info=None
        )

        # Send to the root logger
        logging.getLogger().handle(metrics_record)


def setup_logging(
    log_dir: str = 'logs',
    log_level: int = logging.INFO,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    max_file_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    log_json: bool = False,
    use_colors: bool = True,
    dedup_messages: bool = True,
    collect_metrics: bool = True,
    metrics_interval: float = 600.0,  # 10 Minuten
    app_name: str = 'rom_sorter'
) -> None:
    """
    Richtet das erweiterte Logging-System ein.

    Args:
        log_dir: Verzeichnis für Logdateien
        log_level: Allgemeines Log-Level
        console_level: Log-Level für Konsolenausgabe
        file_level: Log-Level für Dateiausgabe
        max_file_size: Maximale Größe pro Logdatei
        backup_count: Anzahl beizubehaltender Logdateien
        log_json: Ob JSON-Logs geschrieben werden sollen
        use_colors: Ob farbige Konsolenausgabe verwendet werden soll
        dedup_messages: Ob Nachrichten dedupliziert werden sollen
        collect_metrics: Ob Leistungsmetriken gesammelt werden sollen
        metrics_interval: Intervall für die Ausgabe von Metriken
        app_name: Name der Anwendung für Logdateien
    """
    # Benutzerdefinierte Log-Ebenen registrieren
    logging.addLevelName(TRACE, "TRACE")
    logging.addLevelName(VERBOSE, "VERBOSE")

    # Make sure the log directory exists
    os.makedirs(log_dir, exist_ok=True)

    # Root-Logger konfigurieren
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Bestehende Handler entfernen
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Format-Strings
    console_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_format = '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'

    # Konsolenausgabe einrichten
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)

    if use_colors:
        console_formatter = ColoredFormatter(console_format)
    else:
        console_formatter = logging.Formatter(console_format)

    console_handler.setFormatter(console_formatter)

    # Files for the different output formats
    today = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(log_dir, f'{app_name}_{today}.log')

    # Dateiausgabe einrichten
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter(file_format))

    # Add the handler to the root logger
    if dedup_messages:
        console_handler = DedupHandler(console_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Set up JSON logging, if desired
    if log_json:
        json_file = os.path.join(log_dir, f'{app_name}_{today}.json')
        json_handler = logging.handlers.RotatingFileHandler(
            filename=json_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        json_handler.setLevel(file_level)
        json_handler.setFormatter(JsonFormatter())
        root_logger.addHandler(json_handler)

    # Set up metrics collection if desired
    if collect_metrics:
        metrics_handler = PerformanceMetricsHandler(interval=metrics_interval)
        metrics_handler.setLevel(logging.NOTSET)
        root_logger.addHandler(metrics_handler)

    # Start-Nachricht loggen
    logging.info(f"Logging-System initialisiert mit Log-Level {logging.getLevelName(log_level)}")
    logging.debug(f"Log-Datei: {log_file}")


class LoggerAdapter(logging.LoggerAdapter):
    """
    Adapter für kontextbezogenes Logging.
    Ermöglicht das Hinzufügen von Kontextinformationen zu allen Log-Nachrichten.
    """

    def __init__(self, logger: logging.Logger, extra: Dict[str, Any] = None):
        """
        Initialisiert den Logger-Adapter mit zusätzlichen Kontextinformationen.

        Args:
            logger: Basis-Logger
            extra: Zusätzliche Kontextinformationen
        """
        super().__init__(logger, extra or {})

    def process(self, msg: str, kwargs: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Verarbeitet die Log-Nachricht und fügt Kontextinformationen hinzu.

        Args:
            msg: Log-Nachricht
            kwargs: Zusätzliche Argumente für den Logger

        Returns:
            Tupel aus formatierter Nachricht und Argumenten
        """
        # Add context information in a compact form to the message
        context_str = ' '.join(f"{k}={v}" for k, v in self.extra.items())
        if context_str:
            msg = f"{msg} [{context_str}]"

        # Insert further context information in the Record
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra'].update(self.extra)

        return msg, kwargs

    def trace(self, msg: str, *args, **kwargs) -> None:
        """
        Loggt eine Nachricht auf TRACE-Level.

        Args:
            msg: Log-Nachricht
            *args: Positionsabhängige Argumente für die Formatierung
            **kwargs: Zusätzliche Argumente für den Logger
        """
        self.log(TRACE, msg, *args, **kwargs)

    def verbose(self, msg: str, *args, **kwargs) -> None:
        """
        Loggt eine Nachricht auf VERBOSE-Level.

        Args:
            msg: Log-Nachricht
            *args: Positionsabhängige Argumente für die Formatierung
            **kwargs: Zusätzliche Argumente für den Logger
        """
        self.log(VERBOSE, msg, *args, **kwargs)


def get_logger(name: str, extra: Dict[str, Any] = None) -> LoggerAdapter:
    """
    Erstellt einen neuen Logger mit Adapter für kontextbezogenes Logging.

    Args:
        name: Name des Loggers
        extra: Zusätzliche Kontextinformationen

    Returns:
        LoggerAdapter mit den angegebenen Kontextinformationen
    """
    return LoggerAdapter(logging.getLogger(name), extra or {})


def with_context(context: Dict[str, Any] = None):
    """
    Dekorator für Funktionen, der Kontext zum Logging hinzufügt.

    Args:
        context: Statischer Kontext für alle aufgerufenen Funktionen

    Returns:
        Dekorator-Funktion
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Logger for this function
            logger_name = f"{func.__module__}.{func.__name__}"

            # Kombinierten Kontext erstellen
            combined_context = {}
            if context:
                combined_context.update(context)

            # Add functional arguments to the context
            func_context = {
                'function': func.__name__,
                'module': func.__module__,
                'start_time': datetime.now().isoformat()
            }
            combined_context.update(func_context)

            # Create logger with context
            logger = get_logger(logger_name, combined_context)
            logger.debug(f"Funktion {func.__name__} aufgerufen")

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.debug(f"Funktion {func.__name__} erfolgreich abgeschlossen in {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"Fehler in Funktion {func.__name__} nach {elapsed:.3f}s: {e}")
                raise

        return wrapper

    return decorator
