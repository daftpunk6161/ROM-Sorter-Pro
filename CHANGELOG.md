# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
und dieses Projekt verwendet [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Added

### Changed

### Fixed

### Security

## [2.1.8] - 2026-01-24

### Added
- Golden-Fixture-Test für Sortierplan (Basis für Regression-Suite).

### Changed
- GUI-DB-Dialoge (Qt/Tk) loggen Task-Fehler; Cancel zeigt sofort den Status und IGIR-Abbruch deaktiviert den Button; IGIR erzeugt Report/Temp-Verzeichnisse vor dem Lauf, verlangt dest_root, liefert Standard-Templates und zeigt sie im GUI; IGIR-Templates können im GUI übernommen/angepasst werden; Sprach/Regionsfilter unterstützen Mehrfachauswahl; DAT-Quellen-Manager (Qt/Tk) mit Integritäts-Check und DAT/XML/ZIP Counts; Plan-Flow respektiert CancelToken (Test); Plan-Start validiert Zielpfad (Test); Resume-Dateien werden validiert; Track-Set‑Validierung erweitert + Platform-Format-Registry ergänzt + UI-Hinweis bei Unknown; JSON-Logging per Env-Flag verfügbar; Pytest nutzt Projekt-Temp als Base.
- Lokale Identification-Overrides (YAML/JSON) inkl. UI-Button zum Öffnen der Mapping-Datei.
- Normalization-Plan bevorzugt Converter anhand `preferred_outputs` aus Platform-Formats.
- Normalization-Execution liefert per-Item Status im Report.
- IGIR-Tab bietet jetzt direkte Buttons zum Öffnen der Diff-Reports (CSV/JSON).
- IGIR-Template übernimmt jetzt auch Plan-Args beim Speichern.
- IGIR Execute verlangt jetzt einen vorhandenen Diff-Report (Plan vorher notwendig).
- IGIR unterstützt Profile (active_profile + profiles) inkl. UI-Auswahl.
- GUI-Backend-Fehler werden mit kombinierten Details geloggt (Qt/Tk) + Test.
- External-Tools-Runner validiert jetzt Pfade (inkl. Symlink-Schutz) + Test.
- SQLite-DAT-Index: inkrementeller Rebuild entfernt fehlende DATs und liefert Coverage-Report.
- UI zeigt Normalisierungshinweise in der Ergebnis-Tabelle; DAT-Quellen-Dialog zeigt Coverage-Statistik (Qt/Tk).
- IGIR Execute unterstützt Copy-first Staging (Rollback-Strategie) inkl. UI-Toggle.
- GUI Job-System: Queue (mit Priorität), Pause/Resume und Live-Log-Filter (Qt/Tk).
- Hash-Cache berücksichtigt jetzt Pfad+mtime+Größe; IO-Throttling für große Dateien; SQLite-Pragmas weiter getunt.
- Rebuilder-Modus (Copy-only) im UI und Frontend-Exporte (EmulationStation/LaunchBox) aus Sort-Plan.
- Filter sind im Arbeitsbereich integriert; IGIR-Tab vereinfacht mit „Erweitert anzeigen“.

### Fixed
- Qt-UI Typing-Anmerkungen bereinigt, um Pylance Fehler zu vermeiden.

### Security
