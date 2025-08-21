# ROM Sorter Pro - Architektur Update 2025

## Überblick zur Architektur

Die ROM Sorter Pro-Anwendung nutzt eine modulare Architektur, die in mehrere Hauptkomponenten unterteilt ist:

### Kernmodule

- **UI-System**: Verwaltet die Benutzeroberfläche mit Tkinter und erweiterten Widgets
- **Scanning-Engine**: Erkennt ROM-Dateien und ihre Eigenschaften
- **Datenbank-Subsystem**: Verwaltet und nutzt ROM-Datenbanken für zusätzliche Metadaten
- **Konfigurationssystem**: Verwaltet Benutzereinstellungen und Programmoptionen

## Bereinigungen August 2025

Im August 2025 wurden folgende Verbesserungen implementiert:

### UI-System Bereinigung

- Entfernung von doppeltem Code zwischen verschiedenen UI-Modulen
- Konsolidierung des Hauptfensters in eine vereinfachte `main_window.py`-Datei
- Verbesserte Themeverwaltung über `enhanced_theme.py`

### Konfigurationssystem

- Vereinfachung der Konfigurationsbeladung
- Einführung einer verbesserten Konfigurationsschnittstelle
- Verbesserte Fehlerbehandlung bei fehlenden Konfigurationsdateien

### Logging-System

- Bereinigung von Konflikten in der Logging-Konfiguration
- Verbesserte Formatierung der Protokolleinträge
- Automatisches Protokollrotation und -verwaltung

## Ordnerstruktur

```text
src/
├── __init__.py
├── config.json        # Hauptkonfigurationsdatei
├── config.py          # Konfigurationsverarbeitung
├── cli/               # Befehlszeilenschnittstelle
├── config/            # Erweiterte Konfigurationskomponenten
├── core/              # Kernfunktionalität
├── database/          # ROM-Datenbank-Integration
├── detectors/         # Konsolendetektoren
├── scanning/          # ROM-Scanning-Engine
├── ui/                # Benutzeroberfläche
│   ├── app.py         # Hauptanwendungsklasse
│   ├── main_window.py # Hauptfenster
│   ├── compat.py      # Kompatibilitätsschicht
│   └── enhanced_theme.py # Theming-System
├── utils/             # Hilfsfunktionen
└── web/               # Web-Interface-Komponenten
```

## Aktuelle Probleme und Lösungen

| Problem | Lösung |
|---------|--------|
| Doppelte UI-Implementierungen | Code in einer einheitlichen UI-Struktur konsolidiert |
| Fehler beim Laden der Konfiguration | Verbesserte Fehlerbehandlung und Standardwerte |
| Logging-Konfigurationsfehler | Entfernung widersprüchlicher Parameter in logging.basicConfig |
| Theme-System-Initialisierung | Verbesserte Initialisierungsroutine in enhanced_theme.py |
