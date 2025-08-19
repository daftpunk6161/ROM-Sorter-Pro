#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROM Sorter Pro - Dependency Manager

This module handles checking and installing the required dependencies
for ROM Sorter Pro, including optional dependencies for advanced features.

Features:
- Checking installed packages and versions
- Automatic installation of missing packages
- Support for optional dependencies (ML, GUI, etc.)
- Platform-specific adaptations
"""

import os
import sys
import subprocess
import logging
import platform
import importlib.util
from typing import Dict, List, Set, Tuple, Optional, Union, Any

# Try to import PKG_Resources (optional dependency)
try:
    import pkg_resources
    HAS_PKG_RESOURCES = True
except ImportError:
    HAS_PKG_RESOURCES = False

# Configure logger
logger = logging.getLogger(__name__)

# Required dependencies
REQUIRED_PACKAGES = [
    "PyQt5",            # GUI-Framework
    "pandas",           # Data processing
    "requests",         # HTTP requests
    "pillow",           # Image processing
    "appdirs",          # Paths for application data
    "tqdm",             # Progress display
]

# Optional dependencies according to functionality
OPTIONAL_PACKAGES = {
    "ml": [
        "scikit_learn",  # Machine learning (scikit-learn is installed as scikit_learn)
        "numpy",         # Numerical computations
        "tensorflow",    # Tensorflow for machine learning
    ],
    "ai": [
        "tensorflow",    # Deep Learning (if GPU available)
        "torch",         # Pytorch (alternative to tensorflow)
    ],
    "web": [
        "flask",         # Web-Interface
        "flask-cors",    # Cross-Origin Resource Sharing
    ],
    "advanced": [
        "pyunpack",      # Support for various archive formats
        "rarfile",       # RAR file support
        "py7zr",         # 7Z file support
    ],
    "gui_extensions": [
        "PyQt5-stubs",   # Typing information for PYQT5
        "pyqtgraph",     # Plotting and graphics
    ],
}

# Platform-specific dependencies
PLATFORM_PACKAGES = {
    "Windows": [
        "pywin32",       # Windows-API-Zugriff
        "winshell",      # Windows Shell-Integration
    ],
    "Darwin": [
        "pyobjc",        # macOS-API-Zugriff
    ],
    "Linux": [
        "python-xlib",   # X11 support for Linux
    ],
}


class DependencyManager:
    """Verwaltet die Abhängigkeiten für ROM Sorter Pro."""

    def __init__(self):
        """Initialisiert den DependencyManager."""
        self.platform = platform.system()
        self.installed_packages = self._get_installed_packages()
        logger.debug(f"Plattform: {self.platform}")
        logger.debug(f"Installierte Pakete: {len(self.installed_packages)}")

    def _get_installed_packages(self) -> Dict[str, str]:
        """
        Ermittelt die installierten Python-Pakete und ihre Versionen.

        Returns:
            Dictionary mit Paketnamen und Versionen
        """
        installed = {}
        try:
            # Use PKG_Resources to determine installed packages
            if HAS_PKG_RESOURCES:
                for package in pkg_resources.working_set:
                    # Speichere sowohl den key als auch den Projektnamen
                    installed[package.key] = package.version
                    # For Scikit-Learn, Especialy the name with a hyphen
                    if package.key == "scikit_learn":
                        installed["scikit-learn"] = package.version
            else:
                # Fallback: Use PIP List via SubroCess
                try:
                    import json
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "list", "--format", "json"],
                        check=True, capture_output=True, text=True
                    )
                    packages = json.loads(result.stdout)
                    for package in packages:
                        name = package["name"].lower().replace("-", "_")
                        installed[name] = package["version"]
                        # For Scikit-Learn, Especialy the name with a hyphen
                        if name == "scikit_learn":
                            installed["scikit-learn"] = package["version"]
                except Exception as e:
                    logger.error(f"Fehler beim Ausführen von pip list: {e}")
        except Exception as e:
            logger.error(f"Fehler beim Ermitteln der installierten Pakete: {e}")

        return installed

    def is_package_installed(self, package_name: str) -> bool:
        """
        Prüft, ob ein bestimmtes Paket installiert ist.

        Args:
            package_name: Name des zu prüfenden Pakets

        Returns:
            True, wenn das Paket installiert ist, sonst False
        """
        # Normalize the package name for comparison
        package_name = package_name.lower().replace('-', '_')
        return package_name in self.installed_packages

    def get_missing_packages(self, include_optional: bool = False,
                           optional_groups: List[str] = None) -> List[str]:
        """
        Ermittelt fehlende erforderliche und optionale Pakete.

        Args:
            include_optional: Ob optionale Pakete geprüft werden sollen
            optional_groups: Liste der optionalen Paketgruppen, die geprüft werden sollen

        Returns:
            Liste fehlender Pakete
        """
        missing = []

        # Checked packages
        for package in REQUIRED_PACKAGES:
            if not self.is_package_installed(package):
                missing.append(package)

        # Check platform -specific packages
        if self.platform in PLATFORM_PACKAGES:
            for package in PLATFORM_PACKAGES[self.platform]:
                if not self.is_package_installed(package):
                    missing.append(package)

        # Check optional packages
        if include_optional:
            if optional_groups is None:
                # Check all optional groups
                for group, packages in OPTIONAL_PACKAGES.items():
                    for package in packages:
                        if not self.is_package_installed(package):
                            missing.append(package)
            else:
                # Only check the specified optional groups
                for group in optional_groups:
                    if group in OPTIONAL_PACKAGES:
                        for package in OPTIONAL_PACKAGES[group]:
                            if not self.is_package_installed(package):
                                missing.append(package)

        return missing

    def install_packages(self, packages: List[str], upgrade: bool = False,
                       quiet: bool = False) -> bool:
        """
        Installiert die angegebenen Pakete mit pip.

        Args:
            packages: Liste der zu installierenden Pakete
            upgrade: Ob bestehende Pakete aktualisiert werden sollen
            quiet: Ob die Ausgabe unterdrückt werden soll

        Returns:
            True bei Erfolg, False bei Fehler
        """
        if not packages:
            logger.debug("Keine Pakete zu installieren")
            return True

        logger.info(f"Installiere {len(packages)} Pakete: {', '.join(packages)}")

        try:
            # Baue den pip-Befehl
            cmd = [sys.executable, "-m", "pip", "install"]

            if upgrade:
                cmd.append("--upgrade")

            if quiet:
                cmd.append("--quiet")

            cmd.extend(packages)

            # Carry out the PIP command
            logger.debug(f"Ausführen: {' '.join(cmd)}")
            process = subprocess.run(cmd, check=True, capture_output=True, text=True)

            # Update the list of installed packages
            self.installed_packages = self._get_installed_packages()

            logger.info("Paketinstallation abgeschlossen")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Fehler bei der Paketinstallation: {e}")
            logger.error(f"Ausgabe: {e.stdout}")
            logger.error(f"Fehler: {e.stderr}")
            return False

        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei der Paketinstallation: {e}")
            return False

    def ensure_required_dependencies(self, include_platform: bool = True,
                                   auto_install: bool = False) -> bool:
        """
        Stellt sicher, dass alle erforderlichen Abhängigkeiten installiert sind.

        Args:
            include_platform: Ob plattformspezifische Pakete geprüft werden sollen
            auto_install: Ob fehlende Pakete automatisch installiert werden sollen

        Returns:
            True, wenn alle erforderlichen Abhängigkeiten vorhanden sind, sonst False
        """
        # Ermittle fehlende erforderliche Pakete
        missing = self.get_missing_packages(include_optional=False)

        # Add platform -specific packages if necessary
        if include_platform and self.platform in PLATFORM_PACKAGES:
            for package in PLATFORM_PACKAGES[self.platform]:
                if not self.is_package_installed(package) and package not in missing:
                    missing.append(package)

        if not missing:
            logger.info("Alle erforderlichen Abhängigkeiten sind installiert")
            return True

        logger.warning(f"Fehlende erforderliche Abhängigkeiten: {', '.join(missing)}")

        # Install automatically if desired
        if auto_install:
            return self.install_packages(missing)

        return False

    def check_optional_group(self, group: str) -> Tuple[bool, List[str]]:
        """
        Prüft, ob alle Pakete einer optionalen Gruppe installiert sind.

        Args:
            group: Name der optionalen Gruppe

        Returns:
            Tuple mit (alle_installiert, fehlende_pakete)
        """
        if group not in OPTIONAL_PACKAGES:
            logger.warning(f"Unbekannte optionale Gruppe: {group}")
            return False, []

        missing = []
        for package in OPTIONAL_PACKAGES[group]:
            if not self.is_package_installed(package):
                missing.append(package)

        return not missing, missing

    def ensure_optional_group(self, group: str, auto_install: bool = False) -> bool:
        """
        Stellt sicher, dass alle Pakete einer optionalen Gruppe installiert sind.

        Args:
            group: Name der optionalen Gruppe
            auto_install: Ob fehlende Pakete automatisch installiert werden sollen

        Returns:
            True, wenn alle Pakete der Gruppe vorhanden sind, sonst False
        """
        all_installed, missing = self.check_optional_group(group)

        if all_installed:
            logger.info(f"Alle Pakete der Gruppe '{group}' sind installiert")
            return True

        logger.warning(f"Fehlende Pakete in Gruppe '{group}': {', '.join(missing)}")

        # Install automatically if desired
        if auto_install:
            return self.install_packages(missing)

        return False

    def can_import_module(self, module_name: str) -> bool:
        """
        Prüft, ob ein bestimmtes Python-Modul importiert werden kann.

        Args:
            module_name: Name des zu prüfenden Moduls

        Returns:
            True, wenn das Modul importiert werden kann, sonst False
        """
        try:
            spec = importlib.util.find_spec(module_name)
            return spec is not None
        except (ImportError, AttributeError):
            return False


def check_dependencies(auto_install: bool = False) -> bool:
    """
    Prüft alle erforderlichen Abhängigkeiten und installiert sie bei Bedarf.

    Args:
        auto_install: Ob fehlende Pakete automatisch installiert werden sollen

    Returns:
        True, wenn alle erforderlichen Abhängigkeiten vorhanden sind, sonst False
    """
    manager = DependencyManager()
    return manager.ensure_required_dependencies(auto_install=auto_install)


def ensure_gui_dependencies(auto_install: bool = False) -> bool:
    """
    Stellt sicher, dass alle für die GUI erforderlichen Pakete installiert sind.

    Args:
        auto_install: Ob fehlende Pakete automatisch installiert werden sollen

    Returns:
        True, wenn alle GUI-Abhängigkeiten vorhanden sind, sonst False
    """
    manager = DependencyManager()

    # Check whether PYQT5 is installed
    if not manager.is_package_installed("PyQt5"):
        logger.warning("PyQt5 ist nicht installiert")
        if auto_install:
            return manager.install_packages(["PyQt5"])
        return False

    return True


def ensure_ml_dependencies(auto_install: bool = False) -> bool:
    """
    Stellt sicher, dass alle für ML erforderlichen Pakete installiert sind.

    Args:
        auto_install: Ob fehlende Pakete automatisch installiert werden sollen

    Returns:
        True, wenn alle ML-Abhängigkeiten vorhanden sind, sonst False
    """
    manager = DependencyManager()
    return manager.ensure_optional_group("ml", auto_install=auto_install)


def ensure_ai_dependencies(auto_install: bool = False) -> bool:
    """
    Stellt sicher, dass alle für AI erforderlichen Pakete installiert sind.

    Args:
        auto_install: Ob fehlende Pakete automatisch installiert werden sollen

    Returns:
        True, wenn alle AI-Abhängigkeiten vorhanden sind, sonst False
    """
    manager = DependencyManager()
    return manager.ensure_optional_group("ai", auto_install=auto_install)


def has_gpu_support() -> bool:
    """
    Prüft, ob GPU-Unterstützung verfügbar ist.

    Returns:
        True, wenn GPU-Unterstützung verfügbar ist, sonst False
    """
    manager = DependencyManager()

    # Check whether tensorflow or pytorch is installed
    tf_available = manager.can_import_module("tensorflow")
    torch_available = manager.can_import_module("torch")

    if not tf_available and not torch_available:
        return False

    # Check GPU support in Tensorflow
    if tf_available:
        try:
            import tensorflow as tf
            gpus = tf.config.list_physical_devices('GPU')
            return len(gpus) > 0
        except Exception as e:
            logger.debug(f"Fehler beim Prüfen der TensorFlow GPU-Unterstützung: {e}")

    # Check GPU support in Pytorch
    if torch_available:
        try:
            import torch
            return torch.cuda.is_available()
        except Exception as e:
            logger.debug(f"Fehler beim Prüfen der PyTorch GPU-Unterstützung: {e}")

    return False


# Example of the use of the dependent cym manager
if __name__ == "__main__":
    # Konfiguriere Logging
    logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    print("ROM Sorter Pro - Dependency Manager")
    print("---------------------------------")

    manager = DependencyManager()

    print(f"Plattform: {manager.platform}")
    print(f"Installierte Pakete: {len(manager.installed_packages)}")
    print()

    # Check necessary dependencies
    missing_required = manager.get_missing_packages()
    if missing_required:
        print(f"Fehlende erforderliche Abhängigkeiten: {', '.join(missing_required)}")

        # Frage, ob fehlende Pakete installiert werden sollen
        choice = input("Möchten Sie die fehlenden Pakete installieren? (j/n): ")
        if choice.lower() in ['j', 'ja', 'y', 'yes']:
            if manager.install_packages(missing_required):
                print("Installation erfolgreich")
            else:
                print("Fehler bei der Installation")
    else:
        print("Alle erforderlichen Abhängigkeiten sind installiert")

    # Check optional dependencies
    print("\nOptionale Abhängigkeiten:")
    for group in OPTIONAL_PACKAGES:
        all_installed, missing = manager.check_optional_group(group)
        if all_installed:
            status = "✓"
        else:
            status = f"✗ ({len(missing)} fehlend)"

        print(f"  {group}: {status}")

    # Check GPU support
    if has_gpu_support():
        print("\nGPU-Unterstützung: Verfügbar")
    else:
        print("\nGPU-Unterstützung: Nicht verfügbar")
