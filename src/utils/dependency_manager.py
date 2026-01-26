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

import sys
import subprocess
import logging
import platform
import importlib
import importlib.util
from typing import Any, Dict, List, Optional, Tuple

# Try to import PKG_Resources (optional dependency)
try:
    pkg_resources = importlib.import_module("pkg_resources")
    HAS_PKG_RESOURCES = True
except Exception:
    pkg_resources = None
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
    """Manages the dependencies for Rome Sorter Pro."""

    def __init__(self):
        """Initialisiert den DependencyManager."""
        self.platform = platform.system()
        self.installed_packages = self._get_installed_packages()
        logger.debug(f"Plattform: {self.platform}")
        logger.debug(f"Installierte Pakete: {len(self.installed_packages)}")

    def _get_installed_packages(self) -> Dict[str, str]:
        """Determine the installed Python packages and their versions. Return: Dictionary with parcel names and versions"""
        installed = {}
        try:
            # Use PKG_Resources to determine installed packages
            if HAS_PKG_RESOURCES and pkg_resources is not None:
                for package in pkg_resources.working_set:
                    # Speichere sowohl den key als auch den Projektnamen
                    installed[package.key] = package.version
                    # For scikit-learn, especialy the name with a hyphen
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
                        # For scikit-learn, especialy the name with a hyphen
                        if name == "scikit_learn":
                            installed["scikit-learn"] = package["version"]
                except Exception as e:
                    logger.error(f"Fehler beim Ausführen von pip list: {e}")
        except Exception as e:
            logger.error(f"Fehler beim Ermitteln der installierten Pakete: {e}")

        return installed

    def is_package_installed(self, package_name: str) -> bool:
        """Check Whether a certain package is installed. ARGS: Package_Name: Name of the Package to Be Tested Return: True When the Package Is Installed, OtherWise False"""
        # Normalize the package name for comparison
        package_name = package_name.lower().replace('-', '_')
        return package_name in self.installed_packages

    def get_missing_packages(self, include_optional: bool = False,
                           optional_groups: Optional[List[str]] = None) -> List[str]:
        """Determine missing necessary and optional packages. Args: Include_optional: whether optional packages should be checked Optional_Groups: List of optional package groups that are to be checked Return: List missing packages"""
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
        """Install the specified packages with PIP. Args: Packages: List of packages to be installed Upgrade: Whether existing packages should be updated Quiet: Whether the output should be suppressed Return: True in the event of success, false in the event of errors"""
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
            subprocess.run(cmd, check=True, capture_output=True, text=True)

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
        """Make sure that all necessary dependencies are installed. Args: Include_platform: Whether platform -specific packages should be checked Auto_Install: Whether missing packages should be installed automatically Return: True, if all the necessary dependencies are available, otherwise false"""
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
        """Check whether all packages of an optional group are installed. Args: Group: name of the optional group Return: Tuble with (all_ installed, missing_packets)"""
        if group not in OPTIONAL_PACKAGES:
            logger.warning(f"Unbekannte optionale Gruppe: {group}")
            return False, []

        missing = []
        for package in OPTIONAL_PACKAGES[group]:
            if not self.is_package_installed(package):
                missing.append(package)

        return not missing, missing

    def ensure_optional_group(self, group: str, auto_install: bool = False) -> bool:
        """Make sure that all packages of an optional group are installed. Args: Group: name of the optional group Auto_Install: Whether missing packages should be installed automatically Return: True when all packages of the group are available, otherwise false"""
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
        """Check Whether a certain python modules can be imported. ARGS: Module_Name: Name of the module to be tested Return: True if the module can be imported, OtherWise False"""
        try:
            spec = importlib.util.find_spec(module_name)
            return spec is not None
        except (ImportError, AttributeError):
            return False


def check_dependencies(auto_install: bool = False) -> bool:
    """Check all necessary dependencies and install them if necessary. Args: Auto_Install: Whether missing packages should be installed automatically Return: True, if all the necessary dependencies are available, otherwise false"""
    manager = DependencyManager()
    return manager.ensure_required_dependencies(auto_install=auto_install)


def ensure_gui_dependencies(auto_install: bool = False) -> bool:
    """Make sure that all packages required for the GUI are installed. Args: Auto_Install: Whether missing packages should be installed automatically Return: True, if all GUI dependencies are available, otherwise false"""
    manager = DependencyManager()

    # Check whether PYQT5 is installed
    if not manager.is_package_installed("PyQt5"):
        logger.warning("PyQt5 ist nicht installiert")
        if auto_install:
            return manager.install_packages(["PyQt5"])
        return False

    return True


def ensure_ml_dependencies(auto_install: bool = False) -> bool:
    """Make sure that all packages required for ML are installed. Args: Auto_Install: Whether missing packages should be installed automatically Return: True, if all ML dependencies are available, otherwise false"""
    manager = DependencyManager()
    return manager.ensure_optional_group("ml", auto_install=auto_install)


def ensure_ai_dependencies(auto_install: bool = False) -> bool:
    """Make sure that all packages required for AI are installed. Args: Auto_Install: Whether missing packages should be installed automatically Return: True, if all AI dependencies are available, otherwise false"""
    manager = DependencyManager()
    return manager.ensure_optional_group("ai", auto_install=auto_install)


def has_gpu_support() -> bool:
    """Check whether GPU support is available. Return: True when GPU support is available, otherwise false"""
    manager = DependencyManager()

    # Check whether tensorflow or pytorch is installed
    tf_available = manager.can_import_module("tensorflow")
    torch_available = manager.can_import_module("torch")

    if not tf_available and not torch_available:
        return False

    # Check GPU support in Tensorflow
    if tf_available:
        try:
            try:
                tf_module = importlib.import_module("tensorflow")
                gpus = tf_module.config.list_physical_devices('GPU')
                return len(gpus) > 0
            except ImportError:
                logger.debug("TensorFlow konnte nicht importiert werden")
                return False
        except Exception as e:
            logger.debug(f"Fehler beim Prüfen der TensorFlow GPU-Unterstützung: {e}")

    # Check GPU support in Pytorch
    if torch_available:
        try:
            try:
                torch_module = importlib.import_module("torch")
                return bool(torch_module.cuda.is_available())
            except ImportError:
                logger.debug("PyTorch konnte nicht importiert werden")
                return False
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
