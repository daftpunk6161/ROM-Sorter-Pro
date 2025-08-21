from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
import logging
import os
import sys
import time

# Versuche, das erweiterte Logging-System zu importieren
try:
    from ..utils.logging_integration import (
        initialize_logging, get_logger, log_context,
        log_performance, log_exception
    )
    ENHANCED_LOGGING = True
except ImportError:
    ENHANCED_LOGGING = False

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
    from ..config import EnhancedConfig, get_enhanced_config
except ImportError:
# Fallback if the module cannot be imported directly
# This can happen in some test scenarios or in direct execution
    import sys
    from os.path import dirname, abspath, join
    sys.path.insert(0, dirname(dirname(abspath(__file__))))
    from scanning.scanner import OptimizedScanner as Scanner
    from scanning.adaptive_scanner import AdaptiveScanner
    try:
        from config import EnhancedConfig, get_enhanced_config
    except ImportError:
        # Fallback zu einer einfachen Konfigurationsklasse, wenn die eigentliche nicht verfügbar ist
        class EnhancedConfig:
            def __init__(self, *args, **kwargs):
                self.config = {}

        def get_enhanced_config():
            return EnhancedConfig()


class ROMSorterApp:
    """Hauptanwendungsklasse, die das GUI und die Logik verbindet."""

    def __init__(self):
        """Initialisiere die Anwendung."""
# Basic configuration
        self.app_dir = Path(__file__).parent.parent.parent
        self.config_manager = get_enhanced_config(str(self.app_dir / "config.json"))

        # Initialisiere self.config mit Werten aus config_manager
        try:
            # Für EnhancedConfig
            if hasattr(self.config_manager, '_config'):
                self.config = self.config_manager._config
            else:
                # Fallback für alte Konfiguration
                self.config = {}
        except Exception as e:
            logging.error(f"Fehler beim Initialisieren der Konfiguration: {e}")
            self.config = {}

# Set up logging
        self._setup_logging()

# Create the main window
        self.window = ROMSorterWindow()

# Expand the main window with the app logic
        self._setup_window()

# Initialisiere erweitertes Theme-System und DND-Unterstützung
        self._initialize_enhanced_systems()

# Processed command line arguments
        self._process_command_line_args()

        logging.info("ROM Sorter Anwendung gestartet")

    def _setup_logging(self):
        """Richte das Logging ein."""
        log_dir = self.app_dir / "logs"
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"rom_sorter_{self._get_date_string()}.log"

        # Zuerst alle bestehenden Handler vom Root-Logger entfernen, um doppelte Ausgaben zu vermeiden
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Erweiterte Logging-Konfiguration verwenden, wenn verfügbar
        if ENHANCED_LOGGING:
            # Konfiguriere subsystem-spezifische Log-Level basierend auf Konfiguration
            subsystem_levels = {}

            # UI-Subsystem
            ui_level = self.config.get("ui", {}).get("log_level", "INFO")
            if isinstance(ui_level, str) and hasattr(logging, ui_level):
                subsystem_levels["src.ui"] = getattr(logging, ui_level)

            # Scanner-Subsystem
            scanner_level = self.config.get("scanner", {}).get("log_level", "INFO")
            if isinstance(scanner_level, str) and hasattr(logging, scanner_level):
                subsystem_levels["src.scanning"] = getattr(logging, scanner_level)

            # Initialisiere das erweiterte Logging-System
            initialize_logging(
                log_dir=str(log_dir),
                level=logging.DEBUG if self.config.get("debug_mode", False) else logging.INFO,
                use_colors=True,
                subsystem_levels=subsystem_levels
            )

            # Verwende den neuen Logger
            self.logger = get_logger("src.ui.app")
            self.logger.info("Erweitertes Logging-System initialisiert")
            return

        # Configure the logger (Fallback zur alten Methode)
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

    @log_exception(logger_name="src.ui.app") if ENHANCED_LOGGING else lambda x: x
    def _init_scanner(self):
        """Initialisiere den Scanner mit den aktuellen Einstellungen."""
        # Create scanner options
        options = ScannerOptions(
            recursive=self.config.get("recursive_scan", True),
            hash_method=self.config.get("hash_method", "crc32"),
            parallel=self.config.get("parallel_processing", True),
            max_workers=self.config.get("max_workers", 4)
        )

        # Performance-Logging context
        if ENHANCED_LOGGING:
            with log_context(subsystem="scanner", action="initialize", options=str(options)):
                # Create scanner
                if self.config.get("use_adaptive_scanner", False):
                    self.scanner = AdaptiveScanner(max_workers=options.max_workers)
                else:
                    # The Optimized Scanner Only Takes Filter_Extensions and Max_Workers as a Parameter
                    self.scanner = Scanner(None, options.max_workers)

                # Verwende den erweiterten Logger, wenn verfügbar
                self.logger.debug(f"Scanner initialisiert mit Optionen: {options}")
        else:
            # Create scanner ohne erweitertes Logging
            if self.config.get("use_adaptive_scanner", False):
                self.scanner = AdaptiveScanner(max_workers=options.max_workers)
            else:
                # The Optimized Scanner Only Takes Filter_Extensions and Max_Workers as a Parameter
                self.scanner = Scanner(None, options.max_workers)

            logging.debug("Scanner initialisiert mit Optionen: %s", options)

    def _initialize_enhanced_systems(self):
        """Initialisiert die erweiterten Systeme wie Themes und DND."""
        # Initialisiere das Theme-System, wenn verfügbar
        try:
            from . import THEME_SUPPORT, initialize_theme_system
            if THEME_SUPPORT:
                # Hole den Theme-Typ aus der Konfiguration
                theme_type = self.config.get("ui", {}).get("theme", "system")

                # Bei Tkinter ist das Hauptfenster bereits das root-Attribut
                root_widget = self.window
                if hasattr(self.window, 'root'):
                    root_widget = self.window.root

                initialize_theme_system(root_widget)

                # Registriere Theme-Callback für spätere Updates
                from . import register_theme_callback, set_theme
                register_theme_callback(self._on_theme_changed)

                # Setze das Theme aus der Konfiguration
                if theme_type != "system":
                    set_theme(theme_type)

                logging.info(f"Theme-System initialisiert mit Theme-Typ: {theme_type}")
        except ImportError as e:
            logging.warning(f"Theme-System konnte nicht initialisiert werden: {e}")

        # Initialisiere die DND-Unterstützung, wenn verfügbar
        try:
            from . import DND_AVAILABLE, DND_MANAGER_AVAILABLE
            if DND_AVAILABLE:
                logging.info("DND-Unterstützung verfügbar und aktiviert")
            else:
                logging.warning("TkinterDnD2 nicht verfügbar, einige Drag & Drop Funktionen sind eingeschränkt")
        except ImportError:
            logging.warning("DND-Unterstützung konnte nicht initialisiert werden")

    def _on_theme_changed(self, theme):
        """Callback für Theme-Änderungen."""
        # Aktualisiere die Konfiguration mit dem neuen Theme-Typ
        if not "ui" in self.config:
            self.config["ui"] = {}
        self.config["ui"]["theme"] = theme.get_type().value
        logging.debug(f"Theme geändert zu: {theme.get_type().value}")

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
        try:
            # Versuche zuerst save() zu verwenden (EnhancedConfig)
            if hasattr(self.config_manager, 'save'):
                self.config_manager.save()
            # Fallback zur alten Methode
            elif hasattr(self.config_manager, 'save_config'):
                self.config_manager.save_config(self.config)
            else:
                logging.error("Config manager hat keine save oder save_config Methode!")
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Konfiguration: {e}")

# Close the logger
        logging.shutdown()

# Give other resources released
        if hasattr(self, 'scanner'):
            try:
                # Versuche cleanup-Methode aufzurufen, falls vorhanden
                if hasattr(self.scanner, 'cleanup'):
                    self.scanner.cleanup()
            except Exception as e:
                logging.error(f"Fehler beim Aufräumen des Scanners: {e}")


@log_performance(logger_name="src.ui", operation="app_execution") if ENHANCED_LOGGING else lambda x: x
def main():
    """Hauptfunktion zum Starten der Anwendung."""
    app = ROMSorterApp()
    try:
        if ENHANCED_LOGGING:
            with log_context(session_id=f"session_{int(time.time())}", mode="gui"):
                app.run()
        else:
            app.run()
    except Exception as e:
        if ENHANCED_LOGGING:
            logger = get_logger("src.ui.app")
            logger.exception("Unbehandelte Ausnahme: %s", e)
        else:
            logging.exception("Unbehandelte Ausnahme: %s", e)

        messagebox.showerror(
            "Fehler",
            f"Ein unerwarteter Fehler ist aufgetreten:\n{e}"
        )
    finally:
        app.cleanup()


if __name__ == "__main__":
    main()
