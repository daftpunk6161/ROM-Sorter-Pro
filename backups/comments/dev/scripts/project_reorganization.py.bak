#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM-Sorter-Pro - Verzeichnisstruktur Reorganisationsplan

Dieses Skript erstellt eine neue, sauberere Verzeichnisstruktur für das ROM-Sorter-Pro Projekt,
indem es Dateien in die entsprechenden Verzeichnisse verschiebt und Duplikate beseitigt.
"""

import os
import shutil
import sys
from pathlib import Path

# Define the root directory
ROOT_DIR = Path(r"r:\Code\ROM-Sorter-Pro")

# Verzeichnisstruktur
DIRS_TO_CREATE = [
    # Hauptverzeichnisse
    ROOT_DIR / "src",

    # Development tools and resources
    ROOT_DIR / "dev",
    ROOT_DIR / "dev/tools",
    ROOT_DIR / "dev/scripts",
    ROOT_DIR / "dev/tests",
    ROOT_DIR / "dev/docs",

    # Distribution and releases
    ROOT_DIR / "dist",

    # Daten
    ROOT_DIR / "data",
    ROOT_DIR / "data/rom_databases",

    # Andere
    ROOT_DIR / "logs",
    ROOT_DIR / "temp",
]

# Files that should be moved to "Dev/Tools"
DEV_TOOLS = [
    "repo_guard.py",
    "diagnose_imports.py",
    "translate_comments.py",
    "split_comments.py",
]

# Files that should be moved to "dev/scripts"
DEV_SCRIPTS = [
    "cleanup_git.py",
    "cleanup_project.py",
    "setup_new_git.bat",
    "run_cleanup.bat",
]

# Files that should be moved to "dev/tests"
DEV_TESTS = [
    "test_console_integration.py",
    "test_console_mappings.py",
    "test_direct_console_mappings.py",
    "test_gui_refactoring.py",
    "standalone_test.py",
]

# Files that should remain in the root directory
ROOT_FILES = [
    "start_rom_sorter.py",
    "start_rom_sorter.bat",
    "start_rom_sorter.sh",
    "simple_rom_sorter.py",
    "install_dependencies.py",
    "README.md",
    "LICENSE",
    ".gitignore",
]

# Modules with duplicates (keep first, delete second)
DUPLICATE_MODULES = [
    # (keep, delete)
    (ROOT_DIR / "src" / "dnd_support.py", ROOT_DIR / "src" / "ui" / "dnd_support.py"),
    (ROOT_DIR / "src" / "web" / "web_interface.py", ROOT_DIR / "src" / "web_interface.py"),
]

def create_directories():
    """Erstelle die notwendigen Verzeichnisse"""
    for directory in DIRS_TO_CREATE:
        if not directory.exists():
            print(f"Erstelle Verzeichnis: {directory}")
            directory.mkdir(parents=True, exist_ok=True)
        else:
            print(f"Verzeichnis existiert bereits: {directory}")

def move_files():
    """Verschiebe Dateien in die entsprechenden Verzeichnisse"""
    # Entwicklungstools
    for file in DEV_TOOLS:
        src = ROOT_DIR / file
        dst = ROOT_DIR / "dev" / "tools" / file
        if src.exists():
            print(f"Verschiebe {src} nach {dst}")
            shutil.move(str(src), str(dst))
        else:
            print(f"Datei nicht gefunden: {src}")

    # Entwicklungsskripte
    for file in DEV_SCRIPTS:
        src = ROOT_DIR / file
        dst = ROOT_DIR / "dev" / "scripts" / file
        if src.exists():
            print(f"Verschiebe {src} nach {dst}")
            shutil.move(str(src), str(dst))
        else:
            print(f"Datei nicht gefunden: {src}")

    # Testdateien
    for file in DEV_TESTS:
        src = ROOT_DIR / file
        dst = ROOT_DIR / "dev" / "tests" / file
        if src.exists():
            print(f"Verschiebe {src} nach {dst}")
            shutil.move(str(src), str(dst))
        else:
            print(f"Datei nicht gefunden: {src}")

    # Dokumentation
    doc_dir = ROOT_DIR / "docs"
    if doc_dir.exists():
        # Show all files from Docs to Dev/Docs
        for item in doc_dir.glob('*'):
            if item.is_file():
                dst = ROOT_DIR / "dev" / "docs" / item.name
                print(f"Verschiebe {item} nach {dst}")
                shutil.move(str(item), str(dst))
            elif item.is_dir() and item.name != "user_guide":
                # Unterordner wie "ISSUES" auch verschieben
                dst_dir = ROOT_DIR / "dev" / "docs" / item.name
                dst_dir.mkdir(exist_ok=True)
                for subitem in item.glob('*'):
                    dst = dst_dir / subitem.name
                    print(f"Verschiebe {subitem} nach {dst}")
                    shutil.move(str(subitem), str(dst))

def handle_duplicates():
    """Löse Duplikatprobleme"""
    for keep, remove in DUPLICATE_MODULES:
        if keep.exists() and remove.exists():
            print(f"Behebe Duplikat: Behalte {keep}, entferne {remove}")
            # Sicherstellen, dass alle Importe aktualisiert werden
            # This would require more complex logic in a real script
            remove.unlink()
        elif not keep.exists() and remove.exists():
            print(f"Warnung: Original {keep} existiert nicht, verschiebe {remove} nach {keep}")
            shutil.move(str(remove), str(keep))
        else:
            print(f"Keine Aktion notwendig für {keep} und {remove}")

def create_readme():
    """Erstelle eine README-Datei mit Projektstrukturinformationen"""
    readme_content = """# ROM-Sorter-Pro

Ein universelles Tool zum Organisieren und Sortieren von ROM-Dateien für verschiedene Konsolen.

## Projektstruktur

- `src/` - Quellcode der Anwendung
  - `cli/` - Kommandozeilen-Interface
  - `config/` - Konfigurationsmanagement
  - `core/` - Kern-Funktionalität
  - `database/` - Datenbankintegration
  - `detectors/` - ROM-Erkennungsmodule
  - `reporting/` - Berichterstattung
  - `scanning/` - ROM-Scanmodule
  - `security/` - Sicherheitsfunktionen
  - `ui/` - Benutzeroberflächen
  - `utils/` - Hilfsfunktionen
  - `web/` - Webschnittstelle

- `data/` - Anwendungsdaten
  - `rom_databases/` - ROM-Datenbanken

- `dev/` - Entwicklungsressourcen (nicht im Release enthalten)
  - `tools/` - Entwicklungswerkzeuge
  - `scripts/` - Hilfsskripte
  - `tests/` - Testdateien
  - `docs/` - Entwicklerdokumentation

- `dist/` - Distributionspakete und Releases

- `logs/` - Logdateien

- `temp/` - Temporäre Dateien

## Startdateien

- `start_rom_sorter.py` - Hauptstartskript
- `start_rom_sorter.bat` - Windows-Startskript
- `start_rom_sorter.sh` - Linux/Mac-Startskript
- `simple_rom_sorter.py` - Vereinfachte Version
- `install_dependencies.py` - Abhängigkeitsinstallation

## Entwicklung

Entwicklungswerkzeuge und -ressourcen befinden sich im `dev`-Verzeichnis und sind nicht Teil des Releases.

"""
    readme_path = ROOT_DIR / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"README erstellt: {readme_path}")

def main():
    """Hauptfunktion zur Ausführung der Reorganisation"""
    print("Starte Projektreorganisation...")

    # Erstelle Verzeichnisse
    create_directories()

    # Verschiebe Dateien
    move_files()

    # Solve duplicates
    handle_duplicates()

    # Erstelle README
    create_readme()

    print("Projektreorganisation abgeschlossen!")

if __name__ == "__main__":
    main()
