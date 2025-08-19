# GUI Refactoring Plan

Dieses Dokument beschreibt den Plan zur Aufteilung der übergroßen `gui.py`-Datei in kleinere, wartbarere Module.

## Ziel

Das Ziel dieses Refactorings ist es, die übergroße `gui.py`-Datei (>4600 Zeilen) in mehrere kleinere, spezialisierte Module aufzuteilen, um die Wartbarkeit zu verbessern und die Code-Qualität zu erhöhen.

## Neue Modulstruktur

Die `gui.py`-Datei wird in folgende Komponenten aufgeteilt:

### 1. `gui_core.py`

Kernfunktionalität der GUI-Klasse:

- Hauptklasse `ROMSorterGUI`
- Basis-Initialisierungsmethoden
- Layout-Management
- UI-Setup-Methoden

### 2. `gui_handlers.py`

Event-Handler und Callback-Funktionen:

- Button-Callbacks
- Menü-Callbacks
- Dialog-Handler
- Progress-Update-Funktionen

### 3. `gui_components.py`

Wiederverwendbare UI-Komponenten:

- Drop-Zone
- Custom-Widgets
- Dialog-Templates
- Status-Display

### 4. `gui_scanner.py`

Scanner-bezogene Funktionalität:

- Scan-Methoden
- Erkennung-Management
- Fortschrittsanzeige
- Scan-Statistiken

### 5. `gui_dnd.py`

Drag-and-Drop Funktionalität:

- DnD-Handlers
- Dateiverarbeitung
- DnD-Integration
- Drop-Event-Verarbeitung

## Implementierungsschritte

1. Erstellen der neuen Modul-Dateien
2. Extrahieren der relevanten Funktionen und Klassen aus der `gui.py`
3. Anpassen der Importstruktur zwischen den Modulen
4. Aktualisieren von Referenzen
5. Testen der Funktionalität
6. Entfernen der alten `gui.py`, sobald alle Funktionalitäten übertragen wurden

## Vorteile

- Verbesserte Wartbarkeit
- Reduzierte Dateigrößen
- Bessere Code-Organisation
- Einfachere Fehlersuche
- Klare Trennung von Zuständigkeiten
