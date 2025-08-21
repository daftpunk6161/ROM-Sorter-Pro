#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro v2.1.7 - Qt Initialization Module
Phase 1 Implementation: Desktop Optimization

This module initializes the Qt UI components and ensures
that the necessary dependencies are present.
"""

import os
import sys
import logging
from pathlib import Path

# Package constants
__version__ = "2.1.7"
__author__ = "ROM Sorter Pro Team"

# Initialization status
qt_available = False
qt_version = None

# Try to import QT and set status accordingly
try:
    from PyQt6 import QtCore
    qt_available = True
    qt_version = 6
    logging.info("PyQt6 successfully loaded.")
except ImportError:
    try:
        from PyQt5 import QtCore
        qt_available = True
        qt_version = 5
        logging.info("PyQt5 erfolgreich geladen (Fallback).")
    except ImportError:
        # Neither PYQT6 nor PYQT5 available
        qt_available = False
        qt_version = None
        logging.warning("PyQt6 konnte nicht geladen werden. Versuche mit 'pip install PyQt6' zu installieren.")
        logging.warning("Auch PyQt5 ist nicht verfügbar. Die UI wird nicht verfügbar sein.")

def check_qt_dependencies():
    """Überprüft, ob die Qt-Abhängigkeiten installiert sind und gibt Anweisungen zur Installation zurück."""
    if qt_available:
        return True, f"Qt {qt_version} ist verfügbar."
    else:
        install_cmd = "pip install PyQt6" if sys.version_info >= (3, 6) else "pip install PyQt5"
        return False, (f"Qt ist nicht verfügbar. Bitte installieren Sie es mit:\n"
                      f"{install_cmd}")

def can_use_qt():
    """Gibt zurück, ob Qt verwendet werden kann."""
    return qt_available

def get_qt_version():
    """Gibt die verwendete Qt-Version zurück."""
    return qt_version

def start_qt_app(args=None):
    """Startet die Qt-Anwendung mit den angegebenen Argumenten."""
    if not qt_available:
        logging.error("Qt ist nicht verfügbar. Die Anwendung kann nicht gestartet werden.")
        return None

    # Import depending on the available QT version
    if qt_version == 6:
        from PyQt6.QtWidgets import QApplication
    elif qt_version == 5:
        from PyQt5.QtWidgets import QApplication
    else:
        logging.error("Keine unterstützte Qt-Version verfügbar.")
        return None

    # Verwende sys.argv, wenn keine Argumente angegeben sind
    if args is None:
        args = sys.argv

    app = QApplication(args)
    app.setApplicationName("ROM Sorter Pro")
    app.setApplicationVersion(__version__)

    return app

def show_main_window():
    """Startet die Anwendung und zeigt das Hauptfenster an."""
    if not qt_available:
        status, message = check_qt_dependencies()
        print(message)
        return False

    # Import Mainwindow only when QT is available
    if qt_version == 6:
        try:
            from .main_window import ROMSorterMainWindow
        except ImportError:
            from main_window import ROMSorterMainWindow
    else:
        try:
            from .main_window import ROMSorterMainWindow
        except ImportError:
            from main_window import ROMSorterMainWindow

    app = start_qt_app()
    if not app:
        return False

    # Create and show the main window
    main_window = ROMSorterMainWindow()
    main_window.show()

    # Start the event loop
    sys.exit(app.exec())
