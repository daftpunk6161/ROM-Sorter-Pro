#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Installationsskript für Abhängigkeiten

Dieses Skript installiert alle notwendigen Abhängigkeiten für ROM Sorter Pro.
Es ist optimiert für schnelle Installation und automatische Validierung.
"""

import os
import sys
import subprocess
import time
import logging
import platform
import venv
import importlib
from logging import StreamHandler

# Set up logging
logger = logging.getLogger("InstallationHelper")
logger.setLevel(logging.INFO)
handler = StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


def setup_directories():
    """Erstellt benötigte Verzeichnisse für das Programm."""
    dirs = ["config", "logs", "cache", "data"]
    for directory in dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Verzeichnis erstellt: {directory}")


def install_core_requirements():
    """Installiert die grundlegenden Abhängigkeiten."""
    try:
        logger.info("Installiere grundlegende Abhängigkeiten...")
        
# Check whether PIP is available
        subprocess.check_call([sys.executable, "-m", "pip", "--version"])
        
# PIP upgrades
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--upgrade", "pip"
        ])
        
# Install basic packages
        subprocess.check_call([
            sys.executable, "-m", "pip",
            "install",
            "PyQt5==5.15.2",
            "py7zr",
            "pyyaml",
            "configparser",
            "colorlog",
        ])
        
        logger.info("Grundlegende Abhängigkeiten erfolgreich installiert")
        return True
    except Exception as e:
        logger.error(f"Fehler bei der Installation: {str(e)}")
        return False


def verify_core_packages():
    """Überprüft, ob alle grundlegenden Pakete installiert wurden."""
    failed = []
    
    try:
        import PyQt5.QtCore
        logger.info(f"PyQt5 Version: {PyQt5.QtCore.QT_VERSION_STR}")
    except ImportError:
        logger.error("PyQt5 konnte nicht importiert werden.")
        failed.append("PyQt5")
    
    try:
        import py7zr
        logger.info("py7zr wurde erfolgreich installiert.")
    except ImportError:
        logger.error("py7zr konnte nicht importiert werden.")
        failed.append("py7zr")
    
    try:
        import yaml
        logger.info("PyYAML wurde erfolgreich installiert.")
    except ImportError:
        logger.error("PyYAML konnte nicht importiert werden.")
        failed.append("pyyaml")
    
    try:
        import requests
        logger.info("Requests wurde erfolgreich installiert.")
    except ImportError:
        logger.error("Requests konnte nicht importiert werden.")
        failed.append("requests")
    
    if failed:
        logger.error(
            f"Folgende Pakete konnten nicht installiert werden: "
            f"{', '.join(failed)}"
        )
        return False
    return True


def install_optional_packages():
    """Installiert erweiterte Abhängigkeiten für zusätzliche Features."""
    try:
        logger.info("Installiere erweiterte Abhängigkeiten...")
        
# Install extended packages
        subprocess.check_call([
            sys.executable, "-m", "pip",
            "install",
            "requests",
            "pillow",
            "beautifulsoup4",
        ])
        
        logger.info("Erweiterte Abhängigkeiten erfolgreich installiert")
        return True
    except Exception as e:
        logger.error(
            f"Fehler bei der Installation der erweiterten Abhängigkeiten: {str(e)}"
        )
        logger.info(
            "Das Programm wird auch ohne diese Pakete funktionieren, "
            "aber mit eingeschränkter Funktionalität."
        )
        return False


def create_virtual_environment():
    """Erstellt eine virtuelle Umgebung für das Projekt."""
    try:
        logger.info("Erstelle virtuelle Umgebung...")
        venv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '.venv'
        )
        
# Create virtual environment
        venv.create(venv_path, with_pip=True)
        
# Determine the path to the activation file
        if platform.system() == "Windows":
            activate_path = os.path.join(venv_path, "Scripts", "activate.bat")
        else:
            activate_path = os.path.join(venv_path, "bin", "activate")
        
        logger.info("Virtuelle Umgebung erfolgreich erstellt")
        logger.info(f"Aktivieren Sie die virtuelle Umgebung mit: {activate_path}")
        return True
    except Exception as e:
        logger.error(
            f"Fehler beim Erstellen der virtuellen Umgebung: {str(e)}"
        )
        return False


def main():
    """Hauptfunktion für die Installation."""
    start_time = time.time()
    logger.info("Starte Installation der Abhängigkeiten...")
    
# Check Whether we are in A Virtual Environment
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
# Create virtual environment if not yet available and desired
    if not in_venv and "--novenv" not in sys.argv:
        create_virtual_environment()
        logger.info(
            "Bitte aktivieren Sie die virtuelle Umgebung und führen Sie "
            "dieses Skript erneut aus."
        )
        return
    
# Create directory structure
    setup_directories()
    
# Install basic dependencies
    if install_core_requirements():
# Optional: Install extended packages
        install_optional_packages()
        
# Check the installation
        if verify_core_packages():
            elapsed_time = time.time() - start_time
            logger.info(
                f"Abhängigkeiten erfolgreich installiert in "
                f"{elapsed_time:.2f} Sekunden"
            )
            
            logger.info(
                "\nStarten Sie ROM Sorter Pro mit einem der folgenden Befehle:"
            )
            logger.info("- python main.py")
            logger.info("- python -m src.main")
        else:
            logger.error(
                "Nicht alle grundlegenden Abhängigkeiten konnten installiert werden"
            )
    else:
        logger.error(
            "Installation der grundlegenden Abhängigkeiten fehlgeschlagen"
        )


if __name__ == "__main__":
    main()
