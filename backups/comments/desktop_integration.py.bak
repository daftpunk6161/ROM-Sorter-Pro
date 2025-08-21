#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Integrationsmodul für Desktop-Anwendung
Phase 1 Implementation: Desktop-Optimierung

Dieses Modul verbindet die Desktop-Benutzeroberfläche mit den verbesserten
Scannerfunktionen und stellt sicher, dass alle Komponenten korrekt zusammenarbeiten.
"""

import os
import sys
import logging
import threading
import time
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from pathlib import Path

# QT imports are loaded delayed to ensure that
# The configuration is first loaded
QApplication = None
QMessageBox = None

# Local imports
from ..config.enhanced_config import get_enhanced_config
from ..scanning.scanner_integration import ScannerIntegration
from ..utils.thread_pool import AdaptiveThreadPool
from ..database.rom_database import ROMDatabase

# Configure logging
logger = logging.getLogger(__name__)

class DesktopIntegration:
    """
    Integrationsklasse für die Desktop-Anwendung.
    Verbindet UI, Scanner und Datenbank und stellt
    einen einheitlichen Zugriffspunkt für die Anwendung bereit.
    """

    def __init__(self):
        """Initialisiert die Desktop-Integration."""
        self.config = get_enhanced_config()
        self.scanner = None
        self.thread_pool = None
        self.database = None
        self._initialized = False

# Event callbacks
        self.on_rom_found = None
        self.on_scan_progress = None
        self.on_scan_complete = None
        self.on_error = None

# Thread security
        self._lock = threading.RLock()

    def initialize(self):
        """
        Initialisiert alle benötigten Komponenten.
        Diese Methode sollte nach der Konfiguration aufgerufen werden.
        """
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            try:
                logger.info("Initialisiere Desktop-Integration...")

# Initialize the thread pool
                scanner_config = self.config.get_scanner_config()
                max_threads = self.config.get_max_threads()

                logger.info(f"Erstelle Thread-Pool mit max. {max_threads} Threads")
                self.thread_pool = AdaptiveThreadPool(
                    min_workers=2,
                    max_workers=max_threads,
                    name_prefix="rom_sorter",
                    daemon=True
                )
                self.thread_pool.start()

# Initialize database
                db_config = self.config.get_database_config()
                cache_enabled = db_config.get("use_memory_cache", True)

                logger.info(f"Initialisiere Datenbank mit Cache: {cache_enabled}")
                self.database = ROMDatabase(
                    auto_commit=True,
                    cache_enabled=cache_enabled
                )

# Initialize scanner
                logger.info("Initialisiere Scanner")
                self.scanner = ScannerIntegration(self.config)

# Register scanner callbacks
                self.register_scanner_callbacks()

                self._initialized = True
                logger.info("Desktop-Integration erfolgreich initialisiert")

            except Exception as e:
                logger.error(f"Fehler bei der Initialisierung der Desktop-Integration: {e}")
                self.show_error_dialog("Initialisierungsfehler",
                                     f"Die Anwendung konnte nicht initialisiert werden: {e}")
                raise

    def register_scanner_callbacks(self):
        """Registriert Callbacks für den Scanner."""
        if not self.scanner:
            return

# File found
        def on_file_found(path):
            logger.debug(f"Datei gefunden: {path}")

# Rome found
        def on_rom_found(info):
            logger.debug(f"ROM gefunden: {info.get('name', 'Unbekannt')}")

# Add Rome to the database
            try:
                if self.database and 'crc32' in info:
                    system_name = info.get('system', 'Unbekannt')
                    system = self.database.get_system_by_name(system_name)

                    if system:
                        self.database.add_rom(
                            name=info.get('name', 'Unbekannt'),
                            system_id=system['id'],
                            file_path=info.get('path'),
                            size=info.get('size'),
                            crc32=info.get('crc32'),
                            md5=info.get('md5'),
                            sha1=info.get('sha1'),
                            metadata=info.get('metadata')
                        )
            except Exception as e:
                logger.error(f"Fehler beim Hinzufügen von ROM zur Datenbank: {e}")

# Call Ui-Callback, if available
            if self.on_rom_found:
                try:
                    self.on_rom_found(info)
                except Exception as e:
                    logger.error(f"Fehler im on_rom_found-Callback: {e}")

# Progress
        def on_progress(current, total):
            logger.debug(f"Fortschritt: {current}/{total}")

            if self.on_scan_progress:
                try:
                    self.on_scan_progress(current, total)
                except Exception as e:
                    logger.error(f"Fehler im on_scan_progress-Callback: {e}")

# Scan completed
        def on_complete(stats):
            logger.info(f"Scan abgeschlossen: {stats}")

            if self.on_scan_complete:
                try:
                    self.on_scan_complete(stats)
                except Exception as e:
                    logger.error(f"Fehler im on_scan_complete-Callback: {e}")

# Mistake
        def on_error(error):
            logger.error(f"Scanner-Fehler: {error}")

            if self.on_error:
                try:
                    self.on_error(error)
                except Exception as e:
                    logger.error(f"Fehler im on_error-Callback: {e}")
            else:
                self.show_error_dialog("Scanner-Fehler", str(error))

# Register callbacks
        self.scanner.register_callback('file_found', on_file_found)
        self.scanner.register_callback('rom_found', on_rom_found)
        self.scanner.register_callback('progress', on_progress)
        self.scanner.register_callback('complete', on_complete)
        self.scanner.register_callback('error', on_error)

    def scan_directory(self, directory: str, recursive: bool = True) -> Optional[str]:
        """
        Startet einen Scan des angegebenen Verzeichnisses.

        Args:
            directory: Das zu scannende Verzeichnis
            recursive: Ob Unterordner durchsucht werden sollen

        Returns:
            Scan-ID oder None bei Fehler
        """
        if not self._initialized:
            self.initialize()

        try:
            logger.info(f"Starte Scan von {directory} (rekursiv: {recursive})")

            scanner_config = self.config.get_scanner_config()

            return self.scanner.scan_directory(
                directory,
                recursive=recursive,
                max_depth=scanner_config.get("max_depth", -1),
                follow_symlinks=scanner_config.get("follow_symlinks", False),
                use_cache=scanner_config.get("use_cache", True)
            )

        except Exception as e:
            logger.error(f"Fehler beim Starten des Scans: {e}")
            self.show_error_dialog("Scan-Fehler",
                                 f"Der Scan konnte nicht gestartet werden: {e}")
            return None

    def pause_scan(self, scan_id: Optional[str] = None) -> bool:
        """
        Pausiert einen laufenden Scan.

        Args:
            scan_id: ID des zu pausierenden Scans oder None für alle Scans

        Returns:
            True wenn erfolgreich, False bei Fehler
        """
        if not self._initialized or not self.scanner:
            return False

        try:
            return self.scanner.pause_scan(scan_id)
        except Exception as e:
            logger.error(f"Fehler beim Pausieren des Scans: {e}")
            return False

    def resume_scan(self, scan_id: Optional[str] = None) -> bool:
        """
        Setzt einen pausierten Scan fort.

        Args:
            scan_id: ID des fortzusetzenden Scans oder None für alle Scans

        Returns:
            True wenn erfolgreich, False bei Fehler
        """
        if not self._initialized or not self.scanner:
            return False

        try:
            return self.scanner.resume_scan(scan_id)
        except Exception as e:
            logger.error(f"Fehler beim Fortsetzen des Scans: {e}")
            return False

    def stop_scan(self, scan_id: Optional[str] = None) -> bool:
        """
        Stoppt einen laufenden Scan.

        Args:
            scan_id: ID des zu stoppenden Scans oder None für alle Scans

        Returns:
            True wenn erfolgreich, False bei Fehler
        """
        if not self._initialized or not self.scanner:
            return False

        try:
            return self.scanner.stop_scan(scan_id)
        except Exception as e:
            logger.error(f"Fehler beim Stoppen des Scans: {e}")
            return False

    def execute_task(self, func: Callable, *args, **kwargs) -> str:
        """
        Führt eine Aufgabe im Thread-Pool aus.

        Args:
            func: Die auszuführende Funktion
            *args, **kwargs: Parameter für die Funktion

        Returns:
            Task-ID
        """
        if not self._initialized:
            self.initialize()

        return self.thread_pool.submit(func, *args, **kwargs)

    def shutdown(self):
        """Fährt alle Komponenten herunter."""
        logger.info("Fahre Desktop-Integration herunter...")

        try:
# Shut down scanner
            if self.scanner:
                for scan_id in self.scanner.active_scans:
                    self.scanner.stop_scan(scan_id)

# Dill down thread pool
            if self.thread_pool:
                self.thread_pool.shutdown(wait=True)

# Close the database
            if self.database:
                db_config = self.config.get_database_config()
                if db_config.get("vacuum_on_exit", True):
                    logger.info("Führe Datenbank-Vacuum durch...")
                    try:
# Perform vacuum to optimize the database
                        self.database.conn.execute("VACUUM")
                    except Exception as e:
                        logger.error(f"Fehler beim Vacuum der Datenbank: {e}")

                self.database.close()

            logger.info("Desktop-Integration erfolgreich heruntergefahren")

        except Exception as e:
            logger.error(f"Fehler beim Herunterfahren der Desktop-Integration: {e}")

    def show_error_dialog(self, title: str, message: str):
        """
        Zeigt einen Fehlerdialog an, wenn Qt verfügbar ist.
        Falls nicht, wird der Fehler nur protokolliert.

        Args:
            title: Titel des Dialogs
            message: Fehlermeldung
        """
        logger.error(f"{title}: {message}")

        global QApplication, QMessageBox

# Try to import QT if not yet done
        if QMessageBox is None:
# First check whether the QT module is available
            qt_available = False

# Try to import QT modules
            try:
# Try to import the QT module
                from src.ui.qt import can_use_qt, get_qt_version

                if can_use_qt():
                    qt_version = get_qt_version()
                    if qt_version == 6:
                        from PyQt6.QtWidgets import QApplication, QMessageBox
                        qt_available = True
                    elif qt_version == 5:
# Import only if available - the import is already intercepted by modules checks
                        try:
                            from PyQt5.QtWidgets import QApplication, QMessageBox
                            qt_available = True
                        except ImportError:
                            pass
            except ImportError as e:
                logger.debug(f"Qt-Module nicht verfügbar: {e}")
# QT is not available, only logging
                return

# Make sura that there is a Qapplication
        if QApplication.instance() is None:
            return

# Show on error dialogue
        QMessageBox.critical(None, title, message)

# Global instance of the desktop integration
desktop_integration_instance = None

def get_desktop_integration() -> DesktopIntegration:
    """
    Gibt die globale Instanz der Desktop-Integration zurück.
    Erstellt eine neue Instanz, falls noch keine existiert.

    Returns:
        DesktopIntegration-Instanz
    """
    global desktop_integration_instance

    if desktop_integration_instance is None:
        desktop_integration_instance = DesktopIntegration()

    return desktop_integration_instance
