#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Integrationsbrücke für High-Performance-Scanner
Phase 1 Implementation: Desktop-Optimierung

Dieses Modul dient als Brücke zwischen dem neuen High-Performance-Scanner und der bestehenden
Anwendung. Es stellt Adapter-Funktionalität bereit, die es ermöglicht, den neuen Scanner
in bestehenden Code zu integrieren ohne umfangreiche Änderungen an anderen Modulen vorzunehmen.
"""

import os
import sys
import logging
import threading
import time
from typing import Dict, List, Optional, Callable, Union, Any, Tuple, TypeVar

# Define the type alias for the config class
ConfigType = TypeVar('ConfigType')

# Local imports
try:
    from .high_performance_scanner import HighPerformanceScanner
    from ..config import Config
except ImportError:
# Fallback for direct call to this module
    from high_performance_scanner import HighPerformanceScanner
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import Config

# Set up logging
logger = logging.getLogger(__name__)

class ScannerIntegration:
    """
    Integration des High-Performance-Scanners mit der bestehenden Anwendung.
    Diese Klasse bietet eine einfache API für andere Module, um den neuen Scanner zu nutzen.
    """

    def __init__(self, config: Optional[ConfigType] = None):
        """
        Initialisiert die Scanner-Integration.

        Args:
            config: Optionale Konfigurationsinstanz. Falls None, wird die Standardkonfiguration verwendet.
        """
        self.config = config or Config()
        self.scanner = HighPerformanceScanner(self.config)
        self.callbacks = {}
        self.active_scans = {}
        self.scan_counter = 0
        self._register_callbacks()

    def _register_callbacks(self):
        """Registriert die Callbacks für den Scanner."""
        self.scanner.on_file_found = lambda path: self._handle_callback('file_found', path)
        self.scanner.on_rom_found = lambda info: self._handle_callback('rom_found', info)
        self.scanner.on_progress = lambda current, total: self._handle_callback('progress', current, total)
        self.scanner.on_complete = lambda stats: self._handle_callback('complete', stats)
        self.scanner.on_error = lambda error: self._handle_callback('error', error)

    def _handle_callback(self, event_type: str, *args):
        """
        Leitet Ereignisse an registrierte Callbacks weiter.

        Args:
            event_type: Art des Ereignisses ('file_found', 'rom_found', etc.)
            *args: Argumente, die an den Callback weitergegeben werden
        """
        if event_type in self.callbacks:
            for callback in self.callbacks.get(event_type, []):
                try:
                    callback(*args)
                except Exception as e:
                    logger.error(f"Fehler im {event_type} Callback: {str(e)}")

    def register_callback(self, event_type: str, callback: Callable):
        """
        Registriert einen Callback für ein bestimmtes Ereignis.

        Args:
            event_type: Art des Ereignisses ('file_found', 'rom_found', 'progress', 'complete', 'error')
            callback: Funktion, die aufgerufen wird, wenn das Ereignis eintritt
        """
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)

    def scan_directory(self, directory: str, recursive: bool = True, file_types: Optional[List[str]] = None,
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
            Scan-ID, die zur Identifizierung des Scans verwendet werden kann
        """
# Check whether the directory exists
        if not os.path.isdir(directory):
            self._handle_callback('error', f"Verzeichnis existiert nicht: {directory}")
            return None

# Create new scan-ID
        self.scan_counter += 1
        scan_id = f"scan_{self.scan_counter}"

# Starts the scan in a separate thread
        scan_thread = threading.Thread(
            target=self._run_scan,
            args=(scan_id, directory, recursive, file_types, max_depth, follow_symlinks, use_cache),
            daemon=True
        )

# Save and start the thread
        self.active_scans[scan_id] = {
            'thread': scan_thread,
            'directory': directory,
            'start_time': time.time(),
            'status': 'starting'
        }

        scan_thread.start()
        return scan_id

    def _run_scan(self, scan_id: str, directory: str, recursive: bool, file_types: Optional[List[str]],
                 max_depth: int, follow_symlinks: bool, use_cache: bool):
        """
        Führt den eigentlichen Scan im Thread aus.

        Args:
            scan_id: ID des Scans
            directory: Das zu durchsuchende Verzeichnis
            recursive: Ob Unterverzeichnisse durchsucht werden sollen
            file_types: Liste von Dateierweiterungen, die gesucht werden sollen
            max_depth: Maximale Rekursionstiefe
            follow_symlinks: Ob symbolischen Links gefolgt werden soll
            use_cache: Ob Cache-Daten verwendet werden sollen
        """
        try:
            self.active_scans[scan_id]['status'] = 'running'

# Starts the scanner
            result = self.scanner.scan(
                directory, recursive, file_types, max_depth, follow_symlinks, use_cache
            )

            if result:
                self.active_scans[scan_id]['status'] = 'running'
                logger.info(f"Scan {scan_id} gestartet für Verzeichnis {directory}")
            else:
                self.active_scans[scan_id]['status'] = 'error'
                logger.error(f"Scan {scan_id} konnte nicht gestartet werden")
                self._handle_callback('error', f"Scan konnte nicht gestartet werden: {directory}")

        except Exception as e:
            self.active_scans[scan_id]['status'] = 'error'
            error_msg = f"Fehler beim Starten des Scans: {str(e)}"
            logger.exception(error_msg)
            self._handle_callback('error', error_msg)

    def pause_scan(self, scan_id: Optional[str] = None):
        """
        Pausiert einen laufenden Scan.

        Args:
            scan_id: ID des zu pausierenden Scans oder None für alle Scans

        Returns:
            True wenn mindestens ein Scan erfolgreich pausiert wurde, False sonst
        """
        if scan_id is not None:
            if scan_id in self.active_scans and self.active_scans[scan_id]['status'] == 'running':
                result = self.scanner.pause()
                if result:
                    self.active_scans[scan_id]['status'] = 'paused'
                return result
            return False
        else:
# Pause all ongoing scans
            paused_any = False
            for scan_id in self.active_scans:
                if self.active_scans[scan_id]['status'] == 'running':
                    if self.scanner.pause():
                        self.active_scans[scan_id]['status'] = 'paused'
                        paused_any = True
            return paused_any

    def resume_scan(self, scan_id: Optional[str] = None):
        """
        Setzt einen pausierten Scan fort.

        Args:
            scan_id: ID des fortzusetzenden Scans oder None für alle Scans

        Returns:
            True wenn mindestens ein Scan erfolgreich fortgesetzt wurde, False sonst
        """
        if scan_id is not None:
            if scan_id in self.active_scans and self.active_scans[scan_id]['status'] == 'paused':
                result = self.scanner.resume()
                if result:
                    self.active_scans[scan_id]['status'] = 'running'
                return result
            return False
        else:
# Continue all paused scans
            resumed_any = False
            for scan_id in self.active_scans:
                if self.active_scans[scan_id]['status'] == 'paused':
                    if self.scanner.resume():
                        self.active_scans[scan_id]['status'] = 'running'
                        resumed_any = True
            return resumed_any

    def stop_scan(self, scan_id: Optional[str] = None):
        """
        Stoppt einen laufenden Scan.

        Args:
            scan_id: ID des zu stoppenden Scans oder None für alle Scans

        Returns:
            True wenn mindestens ein Scan erfolgreich gestoppt wurde, False sonst
        """
        if scan_id is not None:
            if scan_id in self.active_scans and self.active_scans[scan_id]['status'] in ['running', 'paused']:
                result = self.scanner.stop()
                if result:
                    self.active_scans[scan_id]['status'] = 'stopping'
                return result
            return False
        else:
# Stop all running or paused scans
            stopped_any = False
            for scan_id in self.active_scans:
                if self.active_scans[scan_id]['status'] in ['running', 'paused']:
                    if self.scanner.stop():
                        self.active_scans[scan_id]['status'] = 'stopping'
                        stopped_any = True
            return stopped_any

    def get_scan_status(self, scan_id: Optional[str] = None) -> Union[Dict, List[Dict]]:
        """
        Gibt den Status eines oder aller Scans zurück.

        Args:
            scan_id: ID des Scans oder None für alle Scans

        Returns:
            Wenn scan_id angegeben ist, ein Dictionary mit Status-Informationen
            Wenn scan_id None ist, eine Liste von Dictionaries mit Status-Informationen für alle Scans
        """
        if scan_id is not None:
            if scan_id in self.active_scans:
                return self.active_scans[scan_id].copy()
            return None
        else:
            return [scan.copy() for scan in self.active_scans.values()]

    def cleanup_completed_scans(self):
        """
        Entfernt abgeschlossene Scans aus der Liste der aktiven Scans.

        Returns:
            Anzahl der bereinigten Scans
        """
        completed_scans = []

        for scan_id, scan_info in self.active_scans.items():
            thread = scan_info.get('thread')
            if thread and not thread.is_alive() and scan_info['status'] not in ['running', 'paused']:
                completed_scans.append(scan_id)

        for scan_id in completed_scans:
            del self.active_scans[scan_id]

        return len(completed_scans)

# Main function for test purposes
def main():
    """Testfunktion für die Scanner-Integration."""
    import argparse

# Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description='ROM Scanner Integration Test')
    parser.add_argument('directory', help='Verzeichnis zum Scannen')
    parser.add_argument('--recursive', '-r', action='store_true', help='Unterverzeichnisse durchsuchen')
    parser.add_argument('--symlinks', '-s', action='store_true', help='Symbolischen Links folgen')
    parser.add_argument('--no-cache', '-n', action='store_true', help='Cache nicht verwenden')

    args = parser.parse_args()

    def on_file_found(path):
        print(f"Datei gefunden: {path}")

    def on_rom_found(info):
        print(f"ROM gefunden: {info['name']} ({info['system']})")

    def on_progress(current, total):
        print(f"Fortschritt: {current}/{total} ({int(current/total*100 if total else 0)}%)")

    def on_complete(stats):
        print("\nScan abgeschlossen:")
        print(f"Verarbeitete Dateien: {stats.get('files_processed', 0)}")
        print(f"Gefundene Dateien: {stats.get('files_found', 0)}")
        print(f"Gefundene ROMs: {stats.get('roms_found', 0)}")
        print(f"Gefundene Archive: {stats.get('archives_found', 0)}")
        print(f"Fehler: {stats.get('errors', 0)}")
        print(f"Dauer: {stats.get('duration_seconds', 0):.2f} Sekunden")

# Show systems
        system_counts = stats.get('system_counts', {})
        if system_counts:
            print("\nGefundene Systeme:")
            for system, count in system_counts.items():
                print(f"  - {system}: {count}")

    def on_error(error):
        print(f"Fehler: {error}")

# Initialize scanner integration
    integration = ScannerIntegration()

# Register callbacks
    integration.register_callback('file_found', on_file_found)
    integration.register_callback('rom_found', on_rom_found)
    integration.register_callback('progress', on_progress)
    integration.register_callback('complete', on_complete)
    integration.register_callback('error', on_error)

# Start scan
    print(f"Starte Scan von {args.directory}...")
    scan_id = integration.scan_directory(
        args.directory,
        recursive=args.recursive,
        follow_symlinks=args.symlinks,
        use_cache=not args.no_cache
    )

    if scan_id:
        print(f"Scan gestartet mit ID: {scan_id}")

# Wait for a conclusion
        try:
            while integration.active_scans[scan_id]['thread'].is_alive():
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nScan wird abgebrochen...")
            integration.stop_scan(scan_id)
            sys.exit(1)
    else:
        print("Scan konnte nicht gestartet werden.")
        sys.exit(1)

if __name__ == "__main__":
    main()
