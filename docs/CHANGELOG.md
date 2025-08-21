# Changelog - ROM Sorter Pro

## Version 2.1.8 (August 21, 2025)

### Code Improvements

- **Configuration Modularization**: Split large config.py into modular components for better maintainability
- **Enhanced Documentation**: Added comprehensive documentation in docs/MASTER.md and specialized topic guides
- **Code Quality**: Improved docstrings and comments throughout the codebase
- **Project Structure**: Better organization of source code with clear responsibilities

### Project Infrastructure

- **Central Documentation**: Created comprehensive MASTER.md as central documentation reference
- **Better Logging**: Enhanced logging system with consistent error messages
- **Cleanup Scripts**: Improved path handling in cleanup_project.py

## Version 2.1.8 (August 21, 2025)

### Code Improvements

- **Console Mapping Improved**: Removed duplicate keys from the CONSOLE_MAP dictionary and created a separate file for console definitions
- **Intelligent File Detection**: New functionality for detecting ambiguous file extensions like .bin, .cso, .chd, and .sgx
- **Improved Architecture**: Separation of console definitions and GUI code for better maintainability
- **New Tests**: Added comprehensive tests for the console mapping system

### Project Infrastructure

- **repo_guard.py**: New tool for quality assurance and adherence to coding standards
- **Improved Comments**: Translation of all German comments in Python files to English
- **Version Consistency**: Uniform version numbers across all files in the project

### Technical Bug Fixes

- **Circular Imports**: Elimination of circular import dependencies
- **DND_AVAILABLE**: Improved handling of Drag & Drop availability
- **Code Duplication**: Unified duplicated modules and improved code organization

### Known Issues Fixed

- Error in detecting PlayStation 2 vs. PlayStation Portable files (.cso)
- Conflict between Atari 2600 and PlayStation files (.bin)
- Issues with detection of SuperGrafx vs. PC-Engine games (.sgx)

### Neue Funktionen

- Erweiterte Konsolen-Erkennung mit verbesserter Genauigkeit
- Optimierter Scanner für große ROM-Sammlungen
- Vereinfachte Benutzeroberfläche mit zusätzlichen Anpassungsmöglichkeiten
- Verbesserte Metadaten-Integration mit mehr Quellen

### Optimierungen

- Erheblich verbesserte Leistung bei der Verarbeitung großer Archive
- Reduzierter Speicherverbrauch durch optimierte Algorithmen
- Schnelleres Starten der Anwendung

### Fehlerbehebungen

- Behebung von Speicherlecks bei langfristiger Nutzung
- Korrektur von Anzeigefehlern in der dunklen Theme-Variante
- Behebung von Abstürzen beim Import sehr großer ROM-Sammlungen
