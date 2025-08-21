"""Rome Sarter Pro - Compatibility Module V2.1.8 This module Offers A Compatibility Layer Between the Old and New Ui Structure. It Enables Gentle Migration and Ensures That Older Code Parts Can Work With The New Implementation."""

import sys
import os
import logging
from pathlib import Path

# Logger konfigurieren
logger = logging.getLogger(__name__)

# Setze Standard DND_AVAILABLE Variable
DND_AVAILABLE = False

# The new UI modules are now available
UI_MODULES_AVAILABLE = True
try:
    from .main_window import ROMSorterWindow
    from .app import ROMSorterApp, main as ui_main
    UI_MODULES_AVAILABLE = True
    logger.info("Neue UI-Module verfügbar")
except ImportError as e:
    UI_MODULES_AVAILABLE = False
    logger.warning(f"Neue UI-Module nicht verfügbar: {e}")

# Try to import the old GUI (should fail in most cases)
OLD_GUI_AVAILABLE = False
try:
    from .gui import OptimizedROMSorterGUI as OldGUI, launch_gui as old_launch_gui
    from .gui_dnd import DND_AVAILABLE
    OLD_GUI_AVAILABLE = True
    logger.info("Alte GUI verfügbar")
except ImportError as e:
    logger.warning(f"Alte GUI nicht verfügbar: {e}")
    # Fallback if the old GUI is not available

# Konvertiere alte Optionen in neue Optionen
def convert_options(old_options):
    """Convert old GUI options to new UI options."""
    # Implementation of the conversion if necessary
    return old_options

# Compatibility class for the old API
class OptimizedROMSorterGUICompat(ROMSorterWindow):
    """Compatibility class for the old GUI-API."""

    def __init__(self, *args, **kwargs):
        """Initialize the compatibility class."""
        super().__init__()
        logger.info("GUI-Kompatibilitätsklasse initialisiert")

    def run(self):
        """Carry out the old run method."""
        self.mainloop()

# Exportiere unter dem alten Namen
OptimizedROMSorterGUI = OptimizedROMSorterGUICompat

# Start the GUI with the new implementation
def launch_gui():
    """Start the GUI with the new implementation."""
    app = ROMSorterWindow()
    app.mainloop()
    return 0

except ImportError as e:
    logger.error(f"Fehler beim Import der UI-Module: {e}")

    # Fallback-Dummy-Implementierung
    class DummyGUI:
        """Dummy implementation that throws an error when used."""

        def __init__(self, *args, **kwargs):
            """Initialize the dummy class."""
            raise ImportError("Keine GUI-Implementierung verfügbar")

        def run(self):
            """Dummy implementation for run method."""
            raise ImportError("Keine GUI-Implementierung verfügbar")

    OptimizedROMSorterGUI = DummyGUI

    def launch_gui():
        """Dummy implementation for launch_gui."""
        raise ImportError("Keine GUI-Implementierung verfügbar")

def is_ui_available():
    """Check Whether a ui implementation is available."""
    return UI_MODULES_AVAILABLE

def get_ui_mode():
    """Gives back the current UI mode."""
    return "modern" if UI_MODULES_AVAILABLE else "none"
