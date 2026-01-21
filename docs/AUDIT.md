# ROM-Sorter-Pro — Audit (Phase 0)

Datum: 2026-01-21

## Scope (Pflichtanalyse)
Analysierte Bereiche:
- Einstieg: start_rom_sorter.py, src/main.py
- Konfiguration: src/config.json, src/config-schema.json
- UI: src/ui/compat.py, src/ui/__main__.py, src/ui/mvp/qt_app.py, src/ui/mvp/tk_app.py
- Scanning/Detectors/Core/Security/Database/Conversion: src/scanning/*, src/detectors/*, src/core/*, src/security/*, src/database/*, src/conversion/*
- Legacy UI: _archive/legacy_ui/ui/app.py
- Vorhandene Archiv-Dokumente: _archive/docs/*

## Executive Summary
### P0 (Release-Blocker)
1) **Identifikation ist nicht DAT/Hash-first**: Aktuell existieren Heuristiken/DB/ML-Fallbacks, die bei niedriger Konfidenz nicht strikt zu Unknown normalisieren. Das widerspricht „UNKNOWN > WRONG“.
2) **DAT-Index ist in-memory/pickle**: Der aktuelle DatIndex nutzt cache/dat_index.pkl und ist nicht skalierbar (TB-Scale, inkrementell, sqlite-basiert) und nicht portabel im Sinne der Zielvorgaben.
3) **Archive Awareness ist heuristisch**: ZIP wird nur grob nach Dateinamen gescannt, keine Entry-Hashes; gemischte Archive werden nicht deterministisch behandelt.
4) **IGIR Execute ist nicht strikt gegated**: Der aktuelle UI-Flow kann IGIR direkt ausführen, ohne Safety Diff + expliziten Execute-Button-Workflow.

### P1 (Stabilität/Wartbarkeit)
- **Mehrfach-Implementierungen**: Scanner/Detectors/DB existieren redundant (z. B. detection_handler, console_detector, archive_detector, database/*, core/scan_service). Das erhöht Drift-Risiko.
- **Konversions-Config fragmentiert**: Regeln in src/config.json vs src/conversion/converters.yaml (leer), plus src/utils/external_tools.py.
- **Sicherheits-Checks inkonsistent**: validate_file_operation ist vorhanden, aber Archive-Handling nutzt nur Name-Checks; symlink/zip-slip Schutz ist nicht zentralisiert.

### P2 (Qualität/UX)
- **Controller Boundary ist groß, aber unvollständig**: app/controller.py enthält viele Funktionen, jedoch fehlt identifikations- und normalization-spezifische API nach neuer Zielarchitektur.
- **GUI Export/Tools**: Exporte teilweise asynchron, aber IGIR/Index/Hashing-Workflow fehlt als dedizierter UI-Flow.

## Architektur-Überblick (Ist-Zustand)
```
Entry: start_rom_sorter.py
  -> src/ui/compat.py
     -> src/ui/mvp/qt_app.py / tk_app.py
        -> src/app/api.py + src/app/controller.py
           -> src/core/scan_service.py
              -> src/scanning/high_performance_scanner.py
           -> src/core/normalization.py
           -> src/detectors/*
           -> src/database/*
```

## Identifikation (Ist-Zustand)
- detect_console_fast (filename/ext Heuristik)
- detection_handler kombiniert Archive/CHD/DB/ML
- DatIndex existiert (core/dat_index.py), aber in-memory + pickle Cache
- Kein strikter Hash-first-Stop, kein deterministischer Unknown-Policy-Override in allen Pfaden

## Archive Awareness (Ist-Zustand)
- archive_detector: ZIP Entry-Namen werden geprüft, keine Entry-Hashing/Matching
- Gemischte Archive => heuristische console-Wahl, kein Unknown-by-default

## Normalization/Conversion (Ist-Zustand)
- core/normalization.py validiert Inputs/Manifeste (cue/gdi/folderset)
- converters.yaml vorhanden, aber leer
- external_tools.py unterstützt externe Tools (wud2app/wudcompress/igir), aber ohne neue Safety-Diff/Execute-Gates

## Security (Ist-Zustand)
- security_utils: sanitize_path, validate_file_operation, path traversal checks
- Archive-Sicherheit: nur name-based Checks im archive_detector
- Zielpfad-Containment bei Execute in controller vorhanden, aber nicht zentral durchgesetzt

## Datenbank (Ist-Zustand)
- database/rom_database.py: allgemeine ROM DB (CRC/MD5/SHA1)
- detection_handler nutzt db_debug/db_gui_integration
- Kein dedizierter DAT-Index (sqlite) mit inkrementellem Import

## Lücken vs. Zielanforderung
- DAT/Hash-first Determinismus
- Archive Entry Hashing
- IGIR Safety Diff + explizite Execute Gate
- Portable SQLite Index + Lockfile
- Separate YAML-Regelwerke + JSON Schema Validierung

## Risiken
- Falsch-positive Erkennung → falsch sortierte ROMs (Release-Blocker)
- UI-Blockierung bei Hashing/Index/IGIR ohne Worker
- Datenverlust bei ungesicherten Conversion-Flows

## Empfehlungen (Priorisierung)
P0:
- DAT/Hash-first Pipeline + Unknown Policy erzwingen
- DAT SQLite Index (inkrementell + WAL) + Lockfile
- Archive Entry Hashing + Mixed-Content-Handling
- IGIR: Plan -> Diff -> Execute Gate + Export

P1:
- Controller API vereinheitlichen
- Conversion/Format Regeln in YAML + Schema
- Security zentralisieren (Archive, symlinks)

P2:
- Legacy/Redundanz abbauen
- Dokumentation + CI/Tests erweitern
