from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
import logging
import os
import sys

# Import UI components
from .base import STYLE, BaseApp, center_window, create_tooltip
from .main_window import ROMSorterWindow
from .widgets import ProgressDialog, FolderSelector, ToggleSwitch, FileListBox
from .panels import StatisticsPanel, LogPanel, OptionsPanel
from .custom_widgets import CustomTreeview, DragDropSupport

# Scanner options great for compatibility
class ScannerOptions:
    """Konfigurationsoptionen für den Scanner."""

    def __init__(self, recursive: bool = True, hash_method: str = "crc32",
                 parallel: bool = True, max_workers: int = None):
        """
        Initialisiere die Scanner-Optionen.

        Args:
            recursive: Durchsuche Ordner rekursiv
            hash_method: Zu verwendende Hash-Methode (crc32, md5, sha1)
            parallel: Verwende parallele Verarbeitung
            max_workers: Maximale Anzahl an Worker-Threads
        """
        self.recursive = recursive
        self.hash_method = hash_method
        self.parallel = parallel
        self.max_workers = max_workers

    def __str__(self) -> str:
        """String-Repräsentation der Optionen."""
        return (f"ScannerOptions(recursive={self.recursive}, hash_method={self.hash_method}, "
                f"parallel={self.parallel}, max_workers={self.max_workers})")

# Try to import the module imports
try:
# Correct imports for the new module structure
    from ..scanning.scanner import OptimizedScanner as Scanner
    from ..scanning.adaptive_scanner import AdaptiveScanner
    from ..config import ConfigManager
except ImportError:
# Fallback if the module cannot be imported directly
# This can happen in some test scenarios or in direct execution
    import sys
    from os.path import dirname, abspath, join
    sys.path.insert(0, dirname(dirname(abspath(__file__))))
    from scanning.scanner import OptimizedScanner as Scanner
    from scanning.adaptive_scanner import AdaptiveScanner
    from config import ConfigManager


class ROMSorterApp:
    """Hauptanwendungsklasse, die das GUI und die Logik verbindet."""

    def __init__(self):
        """Initialisiere die Anwendung."""
# Basic configuration
        self.app_dir = Path(__file__).parent.parent.parent
        self.config_manager = ConfigManager(self.app_dir / "config.json")
        self.config = self.config_manager.load_config()

# Set up logging
        self._setup_logging()

# Create the main window
        self.window = ROMSorterWindow()

# Expand the main window with the app logic
        self._setup_window()

# Processed command line arguments
        self._process_command_line_args()

        logging.info("ROM Sorter Anwendung gestartet")

    def _setup_logging(self):
        """Richte das Logging ein."""
        log_dir = self.app_dir / "logs"
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"rom_sorter_{self._get_date_string()}.log"

# Configure the logger
        logging.basicConfig(
            level=logging.DEBUG if self.config.get("debug_mode", False) else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

    def _get_date_string(self):
        """Gib einen Datums-String für Logdateien zurück."""
        import datetime
        return datetime.datetime.now().strftime("%Y%m%d")

    def _setup_window(self):
        """Erweitere das Hauptfenster mit der App-Logik."""
# Connect configuration with UI elements
        self._connect_config_to_ui()

# Register event handler
        self._register_event_handlers()

# Initialize the scanner
        self._init_scanner()

    def _connect_config_to_ui(self):
        """Verbinde die Konfiguration mit den UI-Elementen."""
# Here the UI elements would be linked to the configuration values
# Placeholder for the actual implementation
        pass

    def _register_event_handlers(self):
        """Registriere Event-Handler für UI-Interaktionen."""
# Event handler for buttons, menus etc. would be registered here
# Placeholder for the actual implementation
        pass

    def _init_scanner(self):
        """Initialisiere den Scanner mit den aktuellen Einstellungen."""
# Create scanner options
        options = ScannerOptions(
            recursive=self.config.get("recursive_scan", True),
            hash_method=self.config.get("hash_method", "crc32"),
            parallel=self.config.get("parallel_processing", True),
            max_workers=self.config.get("max_workers", 4)
        )

# Create scanner
        if self.config.get("use_adaptive_scanner", False):
            self.scanner = AdaptiveScanner(max_workers=options.max_workers)
        else:
# The Optimized Scanner Only Takes Filter_Extensions and Max_Workers as a Parameter
            self.scanner = Scanner(None, options.max_workers)

        logging.debug("Scanner initialisiert mit Optionen: %s", options)

    def _process_command_line_args(self):
        """Verarbeite Befehlszeilenargumente."""
        args = sys.argv[1:]

        if not args:
            return

# Easy argument processing
# In a complete implementation, to argument parser would be used here
        for i, arg in enumerate(args):
            if arg == "--source" and i + 1 < len(args):
                self.window.source_path.set(args[i + 1])
            elif arg == "--dest" and i + 1 < len(args):
                self.window.dest_path.set(args[i + 1])
            elif arg == "--auto-start":
# Automatic start if both source and target folders are set
                if self.window.source_path.get() and self.window.dest_path.get():
                    self.window.after(1000, self.window._on_start_sorting)

    def run(self):
        """Starte die Anwendung."""
        self.window.mainloop()

    def cleanup(self):
        """Bereinige Ressourcen bei Beendigung."""
# Saving configuration
        self.config_manager.save_config(self.config)

# Close the logger
        logging.shutdown()

# Give other resources released
        if hasattr(self, 'scanner'):
            self.scanner.cleanup()


def main():
    """Hauptfunktion zum Starten der Anwendung."""
    app = ROMSorterApp()
    try:
        app.run()
    except Exception as e:
        logging.exception("Unbehandelte Ausnahme: %s", e)
        messagebox.showerror(
            "Fehler",
            f"Ein unerwarteter Fehler ist aufgetreten:\n{e}"
        )
    finally:
        app.cleanup()


if __name__ == "__main__":
    main()
