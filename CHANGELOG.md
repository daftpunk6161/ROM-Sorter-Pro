# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
und dieses Projekt verwendet [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Added
- UI-Helfer: minimaler State-Machine-Helper und Backend-Worker-Handle für GUI-Jobs.
- Controller-Facades (Scan/Sort/Conversion) als dünne API-Schicht.
- Optionales Pydantic-Config-Model + Validation (Env-Flag gesteuert).
- Sphinx API-Doku-Grundgerüst (docs/api).
- Fixture-Export-Skript und echte DAT/ROM Fixtures für Regression-Tests.
- Neue GUI-Themes: Clean Slate, Midnight Pro, Retro Console.
- Doku: User Manual, API Reference, Developer Guide.
- Tests: E2E Scan→Plan→Execute, Performance-Benchmark, Memory-Leak- und Security-Fuzz-Smoke.

### Changed
- Docs aktualisiert: Feature Catalog, DAT Import & Index, Identification Strategy, Test Strategy.
- GUI: Library-Report, Presets und Auswahl-Ausführung ergänzt (Qt/Tk).
- Controller: Cancel-Checks in Planung, Dry-run Conversion Guard, .part Cleanup und Custom Exceptions.
- Scan-Service: Cancel-Checks in Callbacks + Profile-Output-Pfad per Env.
- Optional-Import-Logging (Qt/Tk) + Legacy-Qt-Module als stubs (ohne Qt-Import).
- CI: Smoke-Liste erweitert, Docs/Security Jobs ergänzt, workflow_dispatch aktiviert.
- requirements-full.txt ergänzt um optionales pydantic.
- GUI: Tabs auf 5 reduziert (Home/Sortieren/Konvertieren/Einstellungen/Reports), Header/Statusbar verschlankt.
- GUI: Filter-Sidebar rechts, Reports-Tab mit Exporten und Report-Summary.
- IGIR in Konvertieren integriert inkl. Statuszeile/Probe-Button und Version-Anzeige.
- GUI: Tastenkürzel für Scan (Ctrl+S), Preview (Ctrl+P), Execute (Ctrl+E).
- Theme: Auto/System-Theme nutzt OS-Erkennung (Light/Dark).
- Execute: atomare Dateischreibvorgänge via atomicwrites (Copy-Helper).
- GUI: Konsolen/System-Filter in der Filter-Sidebar.
- GUI: Favoriten für Source/Ziel-Pfade im Home-Tab.
- GUI: Multi-Drag&Drop nutzt gemeinsamen Stammordner.

### Fixed
- Symlink-Zielpfade werden im Plan frühzeitig abgewiesen.

### Security
- Symlink-Parent-Checks + striktere Pfadvalidierung bei geplanten Zielen.

## [1.0.0] - 2026-01-24

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
