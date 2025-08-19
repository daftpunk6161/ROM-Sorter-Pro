#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - Qt-Integration Bridge
Phase 1 Implementation: Desktop-Optimierung und Integration

Dieses Modul stellt eine Brücke zwischen der neuen Qt-Benutzeroberfläche und den
optimierten Backend-Komponenten her. Es ermöglicht die nahtlose Integration der
bestehenden Logik in die neue UI-Struktur und bietet saubere Adapter-Schnittstellen.
"""

import os
import sys
import logging
import threading
import time
from typing import Dict, List, Optional, Any, Callable, Union

try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
    PyQt_VERSION = 6
except ImportError:
    logging.critical("PyQt6 konnte nicht importiert werden!")
    PyQt_VERSION = None

# Lokale Importe
try:
    # Relative import for normal import path
    from ...scanning.scanner_integration import ScannerIntegration
    from ...database.rom_database import ROMDatabase
    from ...config.enhanced_config import get_enhanced_config
    from ...utils.thread_pool import AdaptiveThreadPool
except ImportError:
    # Absolute import for direct calls or unusual import paths
    import sys
    from pathlib import Path

    # Add the main directory to the path, if necessary
    src_dir = Path(__file__).resolve().parent.parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from scanning.scanner_integration import ScannerIntegration
    from database.rom_database import ROMDatabase
    from config.enhanced_config import get_enhanced_config
    from utils.thread_pool import AdaptiveThreadPool

# Logging einrichten
logger = logging.getLogger(__name__)

class QtScannerSignals(QObject):
    """Signale für die Kommunikation zwischen Scanner und Qt-UI."""

    file_found = pyqtSignal(str)  # Pfad zur gefundenen Datei
    rom_found = pyqtSignal(dict)  # ROM-Informationen als Dict
    progress_updated = pyqtSignal(int, int)  # Aktuell, Gesamt
    scan_completed = pyqtSignal(dict)  # Zusammenfassung als Dict
    error_occurred = pyqtSignal(str)  # Fehlermeldung

class QtDatabaseSignals(QObject):
    """Signale für die Kommunikation zwischen Datenbank und Qt-UI."""

    query_completed = pyqtSignal(list)  # Ergebnis als Liste
    update_completed = pyqtSignal(bool, str)  # Erfolg, Nachricht
    error_occurred = pyqtSignal(str)  # Fehlermeldung
    import_progress = pyqtSignal(int, int)  # Aktuell, Gesamt
    export_progress = pyqtSignal(int, int)  # Aktuell, Gesamt

class ScannerWorker(QThread):
    """Worker-Thread für Scanner-Operationen."""

    def __init__(self, scanner_integration: ScannerIntegration, directory: str,
                 signals: QtScannerSignals, options: Dict = None):
        """
        Initialisiert den Scanner-Worker.

        Args:
            scanner_integration: Die Scanner-Integration-Instanz
            directory: Das zu scannende Verzeichnis
            signals: Die Qt-Signale für die UI-Kommunikation
            options: Optionale Scanner-Konfiguration
        """
        super().__init__()
        self.scanner = scanner_integration
        self.directory = directory
        self.signals = signals
        self.options = options or {}
        self._setup_callbacks()

    def _setup_callbacks(self):
        """Registriert die Callbacks für den Scanner."""
        self.scanner.register_callback('file_found',
                                     lambda path: self.signals.file_found.emit(path))
        self.scanner.register_callback('rom_found',
                                     lambda info: self.signals.rom_found.emit(info))
        self.scanner.register_callback('progress',
                                     lambda current, total: self.signals.progress_updated.emit(current, total))
        self.scanner.register_callback('complete',
                                     lambda stats: self.signals.scan_completed.emit(stats))
        self.scanner.register_callback('error',
                                     lambda error: self.signals.error_occurred.emit(error))

    def run(self):
        """Führt den Scan-Vorgang aus."""
        try:
            recursive = self.options.get('recursive', True)
            file_types = self.options.get('file_types', None)
            max_depth = self.options.get('max_depth', -1)
            follow_symlinks = self.options.get('follow_symlinks', False)
            use_cache = self.options.get('use_cache', True)

            # Starte den Scan
            scan_id = self.scanner.scan_directory(
                self.directory,
                recursive=recursive,
                file_types=file_types,
                max_depth=max_depth,
                follow_symlinks=follow_symlinks,
                use_cache=use_cache
            )

            # Wait for a Conclusion (this is signaled internaly by the callbacks)
            while self.scanner.is_scan_active(scan_id):
                self.msleep(100)

        except Exception as e:
            logger.error(f"Fehler im Scanner-Worker: {str(e)}")
            self.signals.error_occurred.emit(f"Scanner-Fehler: {str(e)}")

class DatabaseWorker(QThread):
    """Worker-Thread für Datenbank-Operationen."""

    def __init__(self, database: ROMDatabase, operation: str,
                 signals: QtDatabaseSignals, params: Dict = None):
        """
        Initialisiert den Datenbank-Worker.

        Args:
            database: Die Datenbank-Instanz
            operation: Die auszuführende Operation ('query', 'update', 'import', 'export')
            signals: Die Qt-Signale für die UI-Kommunikation
            params: Parameter für die Operation
        """
        super().__init__()
        self.db = database
        self.operation = operation
        self.signals = signals
        self.params = params or {}

    def run(self):
        """Führt die Datenbankoperation aus."""
        try:
            if self.operation == 'query':
                self._handle_query()
            elif self.operation == 'update':
                self._handle_update()
            elif self.operation == 'import':
                self._handle_import()
            elif self.operation == 'export':
                self._handle_export()
            else:
                raise ValueError(f"Ungültige Operation: {self.operation}")

        except Exception as e:
            logger.error(f"Fehler im Datenbank-Worker: {str(e)}")
            self.signals.error_occurred.emit(f"Datenbankfehler: {str(e)}")

    def _handle_query(self):
        """Führt eine Datenbankabfrage aus."""
        query_type = self.params.get('type', 'roms')
        filters = self.params.get('filters', {})

        if query_type == 'roms':
            result = self.db.get_roms(**filters)
        elif query_type == 'systems':
            result = self.db.get_systems(**filters)
        elif query_type == 'collections':
            result = self.db.get_collections(**filters)
        else:
            result = []

        self.signals.query_completed.emit(result)

    def _handle_update(self):
        """Führt ein Datenbankupdate aus."""
        update_type = self.params.get('type', 'rom')
        item_data = self.params.get('data', {})
        item_id = self.params.get('id')

        success = False
        message = ""

        if update_type == 'rom' and item_id:
            success = self.db.update_rom(item_id, item_data)
            message = f"ROM {item_id} aktualisiert" if success else f"Fehler beim Aktualisieren von ROM {item_id}"
        elif update_type == 'system' and item_id:
            success = self.db.update_system(item_id, item_data)
            message = f"System {item_id} aktualisiert" if success else f"Fehler beim Aktualisieren von System {item_id}"
        elif update_type == 'collection' and item_id:
            success = self.db.update_collection(item_id, item_data)
            message = f"Sammlung {item_id} aktualisiert" if success else f"Fehler beim Aktualisieren von Sammlung {item_id}"
        else:
            message = "Ungültige Update-Parameter"

        self.signals.update_completed.emit(success, message)

    def _handle_import(self):
        """Führt einen Datenbankimport aus."""
        import_file = self.params.get('file')
        import_type = self.params.get('type', 'dat')

        # This would actually carry out an incremental import with feedback feedback
        # Hier nur als Beispiel implementiert
        total_items = 100  # Determined in reality from the import file

        for i in range(total_items):
            # Simuliere Import-Fortschritt
            self.signals.import_progress.emit(i + 1, total_items)
            self.msleep(50)  # Simuliere Verarbeitung

        self.signals.update_completed.emit(True, f"Import von {import_file} abgeschlossen")

    def _handle_export(self):
        """Führt einen Datenbankexport aus."""
        export_file = self.params.get('file')
        export_type = self.params.get('type', 'csv')

        # This would actually carry out incremental export with feedback feedback
        # Hier nur als Beispiel implementiert
        total_items = self.params.get('count', 50)

        for i in range(total_items):
            # Simuliere Export-Fortschritt
            self.signals.export_progress.emit(i + 1, total_items)
            self.msleep(30)  # Simuliere Verarbeitung

        self.signals.update_completed.emit(True, f"Export nach {export_file} abgeschlossen")

class QtIntegrationBridge:
    """
    Haupt-Bridge-Klasse zur Integration der Backend-Komponenten mit der Qt-UI.
    Diese Klasse bietet eine einheitliche Schnittstelle für die UI-Komponenten,
    um mit dem Backend zu interagieren.
    """

    def __init__(self):
        """Initialisiert die Integration-Bridge."""
        self.config = get_enhanced_config()
        self.scanner = ScannerIntegration(self.config)
        self.database = ROMDatabase()
        self.thread_pool = AdaptiveThreadPool(min_workers=2)

        # Signale
        self.scanner_signals = QtScannerSignals()
        self.database_signals = QtDatabaseSignals()

        # Aktive Worker
        self.active_workers = {}

    def start_scan(self, directory: str, options: Dict = None) -> str:
        """
        Startet einen asynchronen Scan-Vorgang.

        Args:
            directory: Das zu scannende Verzeichnis
            options: Optionale Scanner-Konfiguration

        Returns:
            ID des Scan-Vorgangs für spätere Referenz
        """
        worker_id = f"scan_{threading.get_ident()}_{int(time.time())}"
        worker = ScannerWorker(self.scanner, directory, self.scanner_signals, options)
        self.active_workers[worker_id] = worker
        worker.start()
        return worker_id

    def stop_scan(self, worker_id: str) -> bool:
        """
        Stoppt einen laufenden Scan-Vorgang.

        Args:
            worker_id: ID des zu stoppenden Vorgangs

        Returns:
            True, wenn erfolgreich gestoppt, sonst False
        """
        if worker_id in self.active_workers:
            # Search for the associated scan-ID and stop the scan
            scan_ids = self.scanner.get_active_scans()
            for scan_id in scan_ids:
                self.scanner.stop_scan(scan_id)

            worker = self.active_workers[worker_id]
            worker.terminate()
            worker.wait()
            del self.active_workers[worker_id]
            return True
        return False

    def execute_database_operation(self, operation: str, params: Dict = None) -> str:
        """
        Führt eine asynchrone Datenbankoperation aus.

        Args:
            operation: Die auszuführende Operation ('query', 'update', 'import', 'export')
            params: Parameter für die Operation

        Returns:
            ID des Datenbank-Vorgangs für spätere Referenz
        """
        worker_id = f"db_{operation}_{threading.get_ident()}_{int(time.time())}"
        worker = DatabaseWorker(self.database, operation, self.database_signals, params)
        self.active_workers[worker_id] = worker
        worker.start()
        return worker_id

    def cancel_operation(self, worker_id: str) -> bool:
        """
        Bricht eine laufende Operation ab.

        Args:
            worker_id: ID des zu stoppenden Vorgangs

        Returns:
            True, wenn erfolgreich gestoppt, sonst False
        """
        if worker_id in self.active_workers:
            worker = self.active_workers[worker_id]
            worker.terminate()
            worker.wait()
            del self.active_workers[worker_id]
            return True
        return False

    def get_database(self) -> ROMDatabase:
        """Gibt die Datenbank-Instanz zurück."""
        return self.database

    def get_scanner(self) -> ScannerIntegration:
        """Gibt die Scanner-Integration-Instanz zurück."""
        return self.scanner

    def get_config(self):
        """Gibt die Konfigurationsinstanz zurück."""
        return self.config

    def cleanup(self):
        """Bereinigt Ressourcen beim Beenden der Anwendung."""
        # Stoppe alle aktiven Worker
        for worker_id, worker in list(self.active_workers.items()):
            self.cancel_operation(worker_id)

        # Close database
        if hasattr(self.database, 'close'):
            self.database.close()

# Globale Bridge-Instanz
_bridge_instance = None

def get_bridge() -> QtIntegrationBridge:
    """
    Gibt die globale Bridge-Instanz zurück oder erstellt eine neue,
    wenn noch keine existiert.

    Returns:
        QtIntegrationBridge-Instanz
    """
    global _bridge_instance

    if _bridge_instance is None:
        _bridge_instance = QtIntegrationBridge()

    return _bridge_instance
