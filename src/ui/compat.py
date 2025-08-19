"""
ROM Sorter UI - Kompatibilitätsmodul

Dieses Modul bietet eine Kompatibilitätsschicht zwischen der alten monolithischen GUI
und der neuen modularen UI-Struktur. Es ermöglicht eine sanfte Migration,
indem es die gleiche Schnittstelle wie die alte GUI bietet, aber die neuen
modularen Komponenten verwendet.
"""

import sys
import os
import logging
from pathlib import Path
import importlib

# Configure logger
logger = logging.getLogger(__name__)

# Check whether the new UI modules are available
UI_MODULES_AVAILABLE = False
try:
    from . import ROMSorterApp, main as ui_main
    from .main_window import ROMSorterWindow
    UI_MODULES_AVAILABLE = True
    logger.info("Neue UI-Module verfügbar")
except ImportError as e:
    logger.warning(f"Neue UI-Module nicht verfügbar: {e}")

# Check whether the old GUI is available
OLD_GUI_AVAILABLE = False
try:
    from .gui import OptimizedROMSorterGUI, launch_gui as old_launch_gui
    OLD_GUI_AVAILABLE = True
    logger.info("Alte GUI verfügbar")
except ImportError as e:
    logger.warning(f"Alte GUI nicht verfügbar: {e}")

# Aliases for downward compatibility
if UI_MODULES_AVAILABLE:
# Use the new UI modules
    ROMSorterGUI = ROMSorterApp
    launch_gui = ui_main

# Convert old options to new options (if necessary)
    def convert_options(old_options):
        """Konvertiere alte GUI-Optionen zu neuen UI-Optionen."""
# Implementation if necessary the conversion
        return old_options

# Compatibility wrapper for the old GUI interface
    class OptimizedROMSorterGUICompat(ROMSorterApp):
        """
        Kompatibilitätsklasse, die die Schnittstelle von OptimizedROMSorterGUI
        implementiert, aber die neue ROMSorterApp verwendet.
        """

        def __init__(self, *args, **kwargs):
            """Initialisiere die Kompatibilitätsklasse."""
            super().__init__()
            logger.info("GUI-Kompatibilitätsmodus aktiviert")

# Here we can make additional adjustments
# To bridge the old and new API

# Add further compatibility methods here if necessary

# Replace the old class with the compatibility class
    OptimizedROMSorterGUI = OptimizedROMSorterGUICompat

else:
# If the new modules are not available, use the old GUI
    if not OLD_GUI_AVAILABLE:
# If neither the old nor the new GUI is available,
# Create Dummy implementations that throw mistakes
        class DummyGUI:
            """Dummy-Implementierung, die einen Fehler wirft, wenn sie verwendet wird."""

            def __init__(self, *args, **kwargs):
                """Initialisiere die Dummy-Klasse."""
                raise ImportError("Keine GUI-Implementierung verfügbar")

            def run(self):
                """Dummy-Implementierung für run-Methode."""
                raise ImportError("Keine GUI-Implementierung verfügbar")

        ROMSorterGUI = DummyGUI
        OptimizedROMSorterGUI = DummyGUI

        def launch_gui():
            """Dummy-Implementierung für launch_gui."""
            raise ImportError("Keine GUI-Implementierung verfügbar")

def is_ui_available():
    """Überprüft, ob eine UI-Implementierung verfügbar ist."""
    return UI_MODULES_AVAILABLE or OLD_GUI_AVAILABLE

def get_ui_mode():
    """Gibt den aktuellen UI-Modus zurück."""
    if UI_MODULES_AVAILABLE:
        return "new"
    elif OLD_GUI_AVAILABLE:
        return "old"
    else:
        return "none"
