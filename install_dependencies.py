#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro v2.1.8 - Installation Script for Dependencies

This script installs all necessary dependencies for ROM Sorter Pro.
It is optimized for fast installation and automatic validation.
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
    """Creates required directories for the program."""
    dirs = ["config", "logs", "cache", "data"]
    for directory in dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Directory created: {directory}")


def install_core_requirements():
    """Installs the basic dependencies."""
    try:
        logger.info("Installing basic dependencies...")

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
            "PyQt5==5.15.7",
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
    """Verifies that all basic packages were installed."""
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
    """Installs advanced dependencies for additional features."""
    try:
        logger.info("Installing advanced dependencies...")

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
            "The program will also work without these packages, "
            "but with limited functionality."
        )
        return False


def create_virtual_environment():
    """Creates A Virtual Environment for the Project."""
    try:
        logger.info("Creating virtual environment...")
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
    """Main function for installation."""
    start_time = time.time()
    logger.info("Starting dependency installation...")

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
            logger.info("- python start_rom_sorter.py --gui")
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
