#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro v2.1.8 - Desktop-Integration Startpunkt
Phase 1 Implementation: Desktop-Optimierung und Integration

This module serves as the main entry point for the new desktop version
with Qt-UI and integrated high-performance scanner.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join('logs', f'rom_sorter_{Path(__file__).stem}.log'))
    ]
)

logger = logging.getLogger(__name__)

def ensure_dependencies():
    """Ensures that all necessary dependencies are installed."""
    qt_available = False

# Try to import PYQT6 first
    try:
        import PyQt6
        logger.info("PyQt6 ist installiert")
        qt_available = True
    except ImportError:
        logger.warning("PyQt6 ist nicht installiert - versuche PyQt5 als Alternative...")

# Experiments PYQT5 AS A Fallback
        try:
            import PyQt5
            logger.info("PyQt5 ist als Fallback installiert")
            qt_available = True
        except ImportError:
            logger.error("Weder PyQt6 noch PyQt5 ist installiert - versuche Installation...")

            try:
                import subprocess

# Try to install PYQT6 first
                try:
                    logger.info("Versuche PyQt6 zu installieren...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt6"])
                    logger.info("PyQt6 wurde erfolgreich installiert")
                    qt_available = True
                except Exception as e:
                    logger.warning(f"PyQt6 Installation fehlgeschlagen: {e}")
                    logger.warning("Versuche PyQt5 zu installieren...")

# Try as fallback PYQT5
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt5"])
                        logger.info("PyQt5 wurde als Fallback erfolgreich installiert")
                        qt_available = True
                    except Exception as e2:
                        logger.error(f"PyQt5 Installation fehlgeschlagen: {e2}")
                        logger.error("Bitte installiere PyQt6 oder PyQt5 manuell mit: pip install PyQt6")
            except Exception as e:
                logger.error(f"Fehler beim Installationsversuch: {e}")

    return qt_available

def main():
    """Hauptfunktion zum Starten der Anwendung."""
    parser = argparse.ArgumentParser(description="ROM Sorter Pro - Desktop Edition")
    parser.add_argument('--debug', action='store_true', help='Debug-Modus aktivieren')
    parser.add_argument('--config', help='Pfad zur Konfigurationsdatei')
    parser.add_argument('--cli', action='store_true', help='Startet im CLI-Modus ohne GUI')
    args = parser.parse_args()

# Set log level based on Debug-Flag
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug-Modus aktiviert")

# Make sure the logs directory exists
    os.makedirs('logs', exist_ok=True)

# Check and install dependencies if not in CLI mode
    if not args.cli and not ensure_dependencies():
        logger.warning("Qt-Abhängigkeiten fehlen, starte im CLI-Modus als Fallback")
        args.cli = True  # Setze CLI-Modus als Fallback

    try:
# Add the main directory to the Python path, if necessary
        current_dir = Path(__file__).parent.resolve()  # src/
        root_dir = current_dir.parent.resolve()       # Projektroot

# Add both directories to the path
        for directory in [str(root_dir), str(current_dir)]:
            if directory not in sys.path:
                sys.path.insert(0, directory)
                logger.debug(f"Verzeichnis zum Python-Pfad hinzugefügt: {directory}")

# Start the application according to the chosen mode
        if args.cli:
# Cli mode: Start the console version
            from .cli.console_interface import start_cli_mode
            logger.info("Starte ROM Sorter Pro CLI-Edition...")
            start_cli_mode()
        else:
# GUI mode: Start the desktop UI
            from .ui.qt.integrated_window import start_integrated_ui
            logger.info("Starte ROM Sorter Pro Desktop-Edition...")
            start_integrated_ui()

    except ImportError as e:
        logger.error(f"Fehler beim Importieren der Module: {e}")
        logger.error("Bitte stelle sicher, dass alle Abhängigkeiten installiert sind")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
