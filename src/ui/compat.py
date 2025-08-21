"""
ROM Sorter Pro - Kompatibilitätsmodul v2.1.8

Dieses Modul bietet eine Kompatibilitätsschicht zwischen der alten und neuen UI-Struktur.
Es ermöglicht eine sanfte Migration und stellt sicher, dass ältere Code-Teile
mit der neuen Implementierung arbeiten können.
"""

import sys
import os
import logging
from pathlib import Path

# Logger konfigurieren
logger = logging.getLogger(__name__)

# Setze Standard DND_AVAILABLE Variable
DND_AVAILABLE = False

# Die neuen UI-Module sind jetzt verfügbar
UI_MODULES_AVAILABLE = True
try:
    from .main_window import ROMSorterWindow
    from .app import ROMSorterApp, main as ui_main
    UI_MODULES_AVAILABLE = True
    logger.info("Neue UI-Module verfügbar")
except ImportError as e:
    UI_MODULES_AVAILABLE = False
    logger.warning(f"Neue UI-Module nicht verfügbar: {e}")

# Versuche die alte GUI zu importieren (sollte in den meisten Fällen fehlschlagen)
OLD_GUI_AVAILABLE = False
try:
    from .gui import OptimizedROMSorterGUI as OldGUI, launch_gui as old_launch_gui
    from .gui_dnd import DND_AVAILABLE
    OLD_GUI_AVAILABLE = True
    logger.info("Alte GUI verfügbar")
except ImportError as e:
    logger.warning(f"Alte GUI nicht verfügbar: {e}")
    # Fallback, wenn die alte GUI nicht verfügbar ist

# Konvertiere alte Optionen in neue Optionen
def convert_options(old_options):
    """Konvertiere alte GUI-Optionen zu neuen UI-Optionen."""
    # Implementierung der Konvertierung wenn nötig
    return old_options

# Kompatibilitätsklasse für die alte API
class OptimizedROMSorterGUICompat(ROMSorterWindow):
    """Kompatibilitätsklasse für die alte GUI-API."""

    def __init__(self, *args, **kwargs):
        """Initialisiere die Kompatibilitätsklasse."""
        super().__init__()
        logger.info("GUI-Kompatibilitätsklasse initialisiert")

    def run(self):
        """Führe die alte run-Methode aus."""
        self.mainloop()

# Exportiere unter dem alten Namen
OptimizedROMSorterGUI = OptimizedROMSorterGUICompat

# Starte die GUI mit der neuen Implementierung
def launch_gui():
    """Starte die GUI mit der neuen Implementierung."""
    app = ROMSorterWindow()
    app.mainloop()
    return 0

except ImportError as e:
    logger.error(f"Fehler beim Import der UI-Module: {e}")

    # Fallback-Dummy-Implementierung
    class DummyGUI:
        """Dummy-Implementierung, die einen Fehler wirft, wenn sie verwendet wird."""

        def __init__(self, *args, **kwargs):
            """Initialisiere die Dummy-Klasse."""
            raise ImportError("Keine GUI-Implementierung verfügbar")

        def run(self):
            """Dummy-Implementierung für run-Method."""
            raise ImportError("Keine GUI-Implementierung verfügbar")

    OptimizedROMSorterGUI = DummyGUI

    def launch_gui():
        """Dummy-Implementierung für launch_gui."""
        raise ImportError("Keine GUI-Implementierung verfügbar")

def is_ui_available():
    """Überprüft, ob eine UI-Implementierung verfügbar ist."""
    return UI_MODULES_AVAILABLE

def get_ui_mode():
    """Gibt den aktuellen UI-Modus zurück."""
    return "modern" if UI_MODULES_AVAILABLE else "none"
