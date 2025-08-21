#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Hauptanwendungsklasse v2.1.8
"""

import os
import sys
import time
import logging
import tkinter as tk
from typing import Dict, List, Optional, Any, Callable

# Attempts to import the extended logging system
try:
    from ..utils.logging_integration import (
        initialize_logging, get_logger, log_context,
        log_performance, log_exception
    )
    ENHANCED_LOGGING = True
except ImportError:
    ENHANCED_LOGGING = False

# Import UI components
from .base import STYLE, BaseApp, center_window
from .main_window import ROMSorterWindow

class ROMSorterApp:
    """Hauptanwendungsklasse für ROM Sorter Pro."""

    def __init__(self):
        """Initialisiere die Anwendung."""
        self.window = None
        self.config = {}
        self.config_manager = None

        # Initialisiere das Logging-System
        self._setup_logging()

        # Lade die Konfiguration
        self._load_config()

        # Erstelle das Hauptfenster
        self._create_window()

        # Theme-System initialisieren
        self._setup_theme()

        # Kommandozeilenargumente verarbeiten
        self._process_command_line_args()

    def _setup_logging(self):
        """Initialisiere das Logging-System."""
        if ENHANCED_LOGGING:
            try:
                initialize_logging(log_dir="logs", app_name="rom_sorter")
            except TypeError:
                # Fallback wenn app_name nicht unterstützt wird
                initialize_logging(log_dir="logs")
            logger = get_logger("src.ui.app")
            logger.info("Erweitertes Logging-System initialisiert")
        else:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler("logs/rom_sorter.log"),
                    logging.StreamHandler()
                ]
            )

    def _load_config(self):
        """Lade die Konfiguration."""
        # Verwende vereinfachten Ansatz mit Standardkonfiguration
        self.config = {"ui": {"theme": "system"}}

        try:
            # Versuche, die Konfiguration zu laden
            import json
            import os

            # Suche nach config.json in Standardorten
            config_paths = [
                os.path.join(os.path.dirname(__file__), "..", "config.json"),
                os.path.join(os.path.dirname(__file__), "..", "..", "config.json"),
            ]

            for path in config_paths:
                if os.path.exists(path):
                    try:
                        with open(path, 'r') as f:
                            loaded_config = json.load(f)
                            self.config.update(loaded_config)
                        logging.info(f"Konfiguration aus {path} geladen")
                        break
                    except json.JSONDecodeError:
                        logging.warning(f"Ungültige JSON-Datei: {path}")

            # Erstelle eine einfache Konfigurationsklasse für Kompatibilität
            class SimpleConfigManager:
                def __init__(self, config):
                    self.config = config

                def save(self):
                    # Konfiguration speichern (nur Dummy-Funktion)
                    pass

                def get(self, section, key, default=None):
                    return self.config.get(section, {}).get(key, default)

            # Setze self.config_manager auf die neue Klasse
            self.config_manager = SimpleConfigManager(self.config)

        except Exception as e:
            logging.warning(f"Fehler beim Laden der Konfiguration: {e}")
            # Standardkonfiguration wird verwendet

    def _create_window(self):
        """Erstelle das Hauptfenster."""
        self.window = ROMSorterWindow()

        # Konfiguration an das Fenster weitergeben (wenn möglich)
        if hasattr(self.window, "apply_config"):
            self.window.apply_config(self.config)

    def _setup_theme(self):
        """Initialisiere das Theme-System."""
        try:
            from .enhanced_theme import (
                initialize_theme_system, set_theme
            )

            # Theme-Typ aus der Konfiguration laden
            theme_type = self.config.get("ui", {}).get("theme", "system")

            # Theme-System initialisieren
            initialize_theme_system(self.window)

            # Nicht das System-Theme setzen, sondern nur wenn explizit angegeben
            if theme_type != "system":
                set_theme(theme_type)

            logging.info(f"Theme-System initialisiert mit Theme-Typ: {theme_type}")
        except ImportError as e:
            logging.warning(f"Theme-System konnte nicht initialisiert werden: {e}")

    def _process_command_line_args(self):
        """Verarbeite Befehlszeilenargumente."""
        args = sys.argv[1:]

        if not args:
            return

        # Einfache Argument-Verarbeitung
        for i, arg in enumerate(args):
            if arg == "--source" and i + 1 < len(args):
                self.window.source_path.set(args[i + 1])
            elif arg == "--dest" and i + 1 < len(args):
                self.window.dest_path.set(args[i + 1])
            elif arg == "--auto-start":
                # Automatischer Start, wenn Quell- und Zielordner gesetzt sind
                if self.window.source_path.get() and self.window.dest_path.get():
                    self.window.after(1000, self.window._on_start_sorting)

    def run(self):
        """Starte die Anwendung."""
        self.window.mainloop()

    def cleanup(self):
        """Bereinige Ressourcen bei Beendigung."""
        # Konfiguration speichern
        try:
            # Versuche zuerst, save() zu verwenden (EnhancedConfig)
            if hasattr(self.config_manager, 'save'):
                self.config_manager.save()
            # Fallback zur alten Methode
            elif hasattr(self.config_manager, 'save_config'):
                self.config_manager.save_config(self.config)
            else:
                logging.error("Config manager hat keine save oder save_config Methode!")
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Konfiguration: {e}")

        # Logger schließen
        logging.shutdown()


# Dekorator für Performance-Messung, falls verfügbar
def performance_decorator(func):
    """Dekorator für Performance-Messung."""
    if ENHANCED_LOGGING:
        from ..utils.logging_integration import log_performance
        return log_performance(logger_name="src.ui", operation="app_execution")(func)
    else:
        return func


@performance_decorator
def main():
    """Hauptfunktion zum Starten der Anwendung."""
    app = ROMSorterApp()
    try:
        if ENHANCED_LOGGING:
            # Starte Anwendung mit Context
            from ..utils.logging_integration import log_context
            with log_context(session_id=f"session_{int(time.time())}", mode="gui"):
                app.run()
        else:
            # Normale Ausführung
            app.run()
    except Exception as e:
        # Fehlerbehandlung
        if ENHANCED_LOGGING:
            from ..utils.logging_integration import get_logger
            logger = get_logger("src.ui.app")
            logger.exception("Unbehandelte Ausnahme: %s", e)
        else:
            logging.exception("Unbehandelte Ausnahme: %s", e)

        # Zeige Fehlermeldung
        if hasattr(tk, "messagebox"):
            tk.messagebox.showerror(
                "Fehler",
                f"Ein unerwarteter Fehler ist aufgetreten:\n{e}"
            )
    finally:
        # Aufräumen
        app.cleanup()

    return 0


if __name__ == "__main__":
    main()
