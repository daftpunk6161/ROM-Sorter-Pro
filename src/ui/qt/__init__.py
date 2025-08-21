#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro v2.1.8 - Qt Initialization Module
Phase 1 Implementation: Desktop Optimization

This module initializes the Qt UI components and ensures
that the necessary dependencies are present.
"""

import os
import sys
import logging
from pathlib import Path

# Package constants
__version__ = "2.1.8"
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
    """Check whether the QT dependencies are installed and returns to installation."""
    if qt_available:
        return True, f"Qt {qt_version} ist verfügbar."
    else:
        install_cmd = "pip install PyQt6" if sys.version_info >= (3, 6) else "pip install PyQt5"
        return False, (f"Qt ist nicht verfügbar. Bitte installieren Sie es mit:\n"
                      f"{install_cmd}")

def can_use_qt():
    """Gives back whether QT can be used."""
    # Force QT availability for PyLint
    global qt_available, qt_version

    # Try to import PyQt6
    try:
        import PyQt6.QtWidgets
        qt_available = True
        qt_version = 6
    except ImportError:
        # Try to import PyQt5
        try:
            import PyQt5.QtWidgets
            qt_available = True
            qt_version = 5
        except ImportError:
            qt_available = False
            qt_version = 0

    return qt_available

def get_qt_version():
    """Returns the QT version used."""
    return qt_version

def start_qt_app(args=None):
    """Starts the QT application with the specified arguments."""
    if not qt_available:
        logging.error("Qt ist nicht verfügbar. Die Anwendung kann nicht gestartet werden.")
        return None

    # Import depending on the available QT version
    QApplication = None
    if qt_version == 6:
        try:
            # Some PyQt6 installations have different module structures
            from PyQt6 import QtWidgets
            QApplication = QtWidgets.QApplication
        except (ImportError, AttributeError):
            logging.error("QApplication konnte nicht aus PyQt6.QtWidgets importiert werden.")
    elif qt_version == 5:
        try:
            # Handle PyQt5 import with error catching
            from PyQt5 import QtWidgets
            QApplication = QtWidgets.QApplication
        except (ImportError, AttributeError):
            logging.error("QApplication konnte nicht aus PyQt5.QtWidgets importiert werden.")
    else:
        logging.error("Keine unterstützte Qt-Version verfügbar.")
        return None

    # Verwende sys.argv, wenn keine Argumente angegeben sind
    if args is None:
        args = sys.argv

    # Check if QApplication was successfully imported
    if QApplication is None:
        logging.error("QApplication konnte nicht importiert werden. GUI kann nicht gestartet werden.")
        return None

    app = QApplication(args)
    app.setApplicationName("ROM Sorter Pro")
    app.setApplicationVersion(__version__)

    return app

def show_main_window():
    """Starts the application and shows the main window."""
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
    if qt_version == 6:
        sys.exit(app.exec())
    else:
        # PyQt5 uses exec_() instead of exec()
        sys.exit(app.exec_())
