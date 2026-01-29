# ROM-Sorter-Pro – Release Backlog Checkliste

> **Erstellt:** 2026-01-29  
> **Ziel:** Vollständige Checkliste aller Findings zum Abarbeiten  
> **Legende:** `[x]` = Erledigt, `[ ]` = Offen

---

## 1. P0 – RELEASE-BLOCKER

| Status | ID | Finding | Datei(en) | Test |
|--------|-----|---------|-----------|------|
| - [x] | P0-1 | Cross-Device Move Cancel funktioniert | `src/app/controller.py` | `test_mvp_execute_cancel_mid_copy.py` |
| - [x] | P0-2 | Dry-run erstellt keine Verzeichnisse | `src/app/controller.py` | `test_mvp_execute_dry_run_no_tools.py` |

---

## 2. P1 – KRITISCH

| Status | ID | Finding | Datei(en) | Test |
|--------|-----|---------|-----------|------|
| - [x] | P1-1 | Symlink-Destination vollständig geprüft | `src/app/controller.py`, `src/app/security_helpers.py` | `test_mvp_security_paths.py` |
| - [x] | P1-2 | Exception-Handling in Workers (Qt/Tk) | `src/ui/mvp/qt_app.py`, `src/ui/mvp/tk_app.py` | - |
| - [x] | P1-3 | ZIP Unicode-Traversal geschützt | `src/security/security_utils.py` | `test_mvp_archive_security.py` |

---

## 3. P2 – WICHTIG

| Status | ID | Finding | Datei(en) | Test |
|--------|-----|---------|-----------|------|
| - [x] | P2-1 | Thread-Referenz nach Abschluss cleanen | `src/ui/mvp/qt_app.py` | - |
| - [x] | P2-2 | UIStateMachine bei Cancel aktualisieren | `src/ui/mvp/qt_app.py`, `src/ui/mvp/tk_app.py` | `test_mvp_ui_state_machine.py` |
| - [x] | P2-3 | Rename-Counter mit Limit (max 10.000) | `src/app/sorting_helpers.py` | `test_mvp_collision_policy.py` |
| - [x] | P2-4 | Timeout für externe Tools (default 300s) | `src/app/controller.py` | `test_mvp_wud2app_tools.py` |
| - [x] | P2-5 | ThreadPool Shutdown bei App-Close | `src/ui/mvp/qt_app.py`, `src/ui/mvp/tk_app.py` | - |
| - [x] | P2-6 | Hash-Cache Thread-Safety | `src/hash_utils.py` | `test_mvp_hash_cache.py` |
| - [x] | P2-7 | plan_sort graceful bei Symlink-Dest | `src/app/controller.py` | `test_mvp_security_paths.py` |
| - [x] | P2-8 | Dry-run Status konsistent anzeigen | `src/app/controller.py` | - |
| - [x] | P2-9 | Config-Schema-Validation | `src/config/io.py`, `src/config/schema.py` | `test_mvp_format_validation.py` |
| - [x] | P2-10 | Mid-Conversion Cancel Test | - | `test_mvp_execute_cancel.py` |

---

## 4. P3 – NICE-TO-HAVE / CLEANUP

| Status | ID | Finding | Datei(en) | Aufwand |
|--------|-----|---------|-----------|---------|
| - [x] | P3-1 | Log-Ring-Buffer Overflow-Schutz | `src/ui/mvp/qt_app.py`, `src/ui/mvp/tk_app.py` | Erledigt |
| - [x] | P3-2 | IGIR-Cancel wartet auf Prozess-Ende | `src/ui/mvp/tk_app.py` | Erledigt |
| - [x] | P3-3 | DAT-Index Cancel Token weitergereicht | `src/app/dat_index_controller.py` | Erledigt |
| - [x] | P3-4 | Export-Worker Fehler als Dialog | `src/ui/mvp/qt_app.py` | Erledigt |
| - [x] | P3-5 | Version in zentraler Datei | `src/version.py` | Erledigt |
| - [x] | P3-6 | simple_rom_sorter.py entfernt | - | Erledigt |
| - [x] | P3-7 | Legacy Qt Ordner dokumentieren | `src/ui/qt/` | Erledigt |
| - [x] | P3-8 | Logging nur in main() konfigurieren | `start_rom_sorter.py` | Erledigt |

---

## 5. REFACTORING – TECHNISCHE SCHULDEN

| Status | ID | Finding | Datei(en) | Aufwand | Priorität |
|--------|-----|---------|-----------|---------|-----------|
| - [x] | REF-1 | Qt App Modularisierung (5063 Zeilen aufteilen) | `src/ui/mvp/qt_app.py` | Groß | Mittel |
| - [x] | REF-2 | Tk App Modularisierung (4069 Zeilen aufteilen) | `src/ui/mvp/tk_app.py` | Groß | Mittel |
| - [ ] | REF-3 | MVVM/MVP Pattern einführen | `src/ui/mvp/` | Groß | Niedrig |
| - [ ] | REF-4 | Structured Logging mit structlog | Projekt-weit | Mittel | Niedrig |
| - [ ] | REF-5 | Dependency Injection für bessere Tests | Projekt-weit | Groß | Niedrig |
| - [ ] | REF-6 | AsyncIO Integration für native Cancel | `src/app/controller.py` | Groß | Niedrig |
| - [ ] | REF-7 | Observable Progress Streams (RxPY) | `src/app/controller.py` | Mittel | Niedrig |
| - [ ] | REF-8 | Pydantic Config Models | `src/config/` | Mittel | Mittel |
| - [ ] | REF-9 | Result Types (Ok/Err) statt Exceptions | Projekt-weit | Mittel | Niedrig |
| - [x] | REF-10 | atomicwrites Library verwenden | `src/app/execute_helpers.py` | Klein | Niedrig |

---

## 6. TESTS – QUALITÄTSVERBESSERUNG

| Status | ID | Finding | Datei(en) | Aufwand | Priorität |
|--------|-----|---------|-----------|---------|-----------|
| - [x] | TEST-1 | GUI Render Smoke Qt (headless) | `dev/tests/test_mvp_gui_render_smoke.py` | Mittel | Mittel |
| - [x] | TEST-2 | GUI Render Smoke Tk (headless) | `dev/tests/test_mvp_gui_render_smoke.py` | Mittel | Mittel |
| - [x] | TEST-3 | E2E Integration Test (Scan→Plan→Execute) | Neu erstellen | Groß | Mittel |
| - [x] | TEST-4 | Performance Benchmark (10k+ Files) | `scripts/bench_perf_10k.py` | Mittel | Niedrig |
| - [x] | TEST-5 | Memory Leak Detection (tracemalloc) | `dev/tests/test_mvp_memory_leak.py` | Mittel | Niedrig |
| - [x] | TEST-6 | Security Fuzzing (Path/Archive) | `dev/tests/test_mvp_security_fuzzing.py` | Groß | Niedrig |

---

## 7. DOKUMENTATION

| Status | ID | Dokument | Aufwand | Priorität | Beschreibung |
|--------|-----|----------|---------|-----------|--------------|
| - [x] | DOC-1 | User Manual | Groß | Hoch | Benutzerhandbuch für Enduser |
| - [x] | DOC-2 | API Reference | Mittel | Mittel | Controller API Dokumentation |
| - [x] | DOC-3 | Developer Guide | Mittel | Mittel | Architektur für Contributors |
| - [x] | DOC-4 | CHANGELOG aktualisieren | Klein | Hoch | v1.0.0 Release Notes |
| - [ ] | DOC-5 | README Screenshots | Klein | Mittel | Aktuelle UI Screenshots |
| - [ ] | DOC-6 | Video Tutorial | Groß | Niedrig | YouTube/Loom Walkthrough |

---

## 8. FEATURES – WUNSCHLISTE

| Status | ID | Feature | Aufwand | Priorität | Beschreibung |
|--------|-----|---------|---------|-----------|--------------|
| - [ ] | FEAT-1 | Progress Persistence | Mittel | Mittel | Resume nach App-Crash |
| - [ ] | FEAT-2 | Undo/Rollback | Groß | Niedrig | Sortierung rückgängig machen |
| - [ ] | FEAT-3 | Batch-Queue mit Prioritäten | Mittel | Mittel | Job-Queue UI verbessern |
| - [ ] | FEAT-4 | Plugin-System | Groß | Niedrig | Externe Detektoren/Converter |
| - [ ] | FEAT-5 | Cloud Backup Integration | Groß | Niedrig | Optional: Google Drive etc. |
| - [ ] | FEAT-6 | Multi-Language UI (i18n) | Mittel | Mittel | Mehrsprachige Oberfläche |
| - [x] | FEAT-7 | Dark/Light Mode Auto | Klein | Mittel | System-Theme automatisch erkennen |
| - [x] | FEAT-8 | Keyboard Shortcuts | Klein | Mittel | Ctrl+S für Scan etc. |
| - [x] | FEAT-9 | Drag & Drop Verbesserung | Mittel | Mittel | Multi-Folder Drop Support |
| - [ ] | FEAT-10 | Export to SQLite Database | Mittel | Niedrig | Scan-Ergebnisse als DB exportieren |
| - [x] | FEAT-11 | Favorites/Presets für Ordner | Klein | Mittel | Häufig genutzte Pfade speichern |
| - [x] | FEAT-12 | Console Filter in UI | Klein | Mittel | Nur bestimmte Konsolen anzeigen |
| - [ ] | FEAT-13 | Bulk Rename Templates | Mittel | Niedrig | Erweiterte Rename-Optionen |
| - [ ] | FEAT-14 | Statistics Dashboard | Mittel | Niedrig | Grafiken für Library-Übersicht |
| - [ ] | FEAT-15 | Auto-Update Check | Klein | Niedrig | Version-Check beim Start |

---

## 9. STATISTIK

### Gesamtübersicht

| Kategorie | Gesamt | ✅ Erledigt | ⬜ Offen |
|-----------|--------|-------------|----------|
| P0 Blocker | 2 | 2 | 0 |
| P1 Kritisch | 3 | 3 | 0 |
| P2 Wichtig | 10 | 10 | 0 |
| P3 Nice-to-Have | 8 | 8 | 0 |
| Refactoring | 10 | 3 | 7 |
| Tests | 6 | 6 | 0 |
| Dokumentation | 6 | 4 | 2 |
| Features | 15 | 5 | 10 |
| **TOTAL** | **60** | **41** | **19** |

### Fortschritt

```
P0-P2 (Release Required): ████████████████████ 100% (15/15)
P3 (Nice-to-Have):        ████████████████████ 100% (8/8)
Refactoring:              ██████░░░░░░░░░░░░░░  30% (3/10)
Tests:                    ████████████████████ 100% (6/6)
Dokumentation:            ████████████░░░░░░░░  67% (4/6)
Features:                 █████░░░░░░░░░░░░░░░  33% (5/15)
```

---

## 10. PRIORISIERTE ROADMAP

### Phase 1: v1.0.0 Release ✅
- [x] Alle P0 Blocker
- [x] Alle P1 Kritisch
- [x] Alle P2 Wichtig

### Phase 2: v1.1.0 (Post-Release Quality)
- [x] DOC-1: User Manual
- [x] DOC-4: CHANGELOG
- [ ] DOC-5: README Screenshots
- [x] TEST-1: GUI Smoke Qt
- [x] TEST-2: GUI Smoke Tk
- [x] REF-1: Qt App Modularisierung
- [x] REF-2: Tk App Modularisierung
- [x] FEAT-7: Dark/Light Mode Auto
- [x] FEAT-8: Keyboard Shortcuts

### Phase 3: v1.2.0 (Features)
- [ ] FEAT-1: Progress Persistence
- [ ] FEAT-3: Batch-Queue Verbesserung
- [ ] FEAT-6: Multi-Language UI
- [x] FEAT-11: Favorites/Presets
- [ ] FEAT-12: Console Filter
- [ ] DOC-2: API Reference
- [ ] DOC-3: Developer Guide

### Phase 4: v2.0.0 (Major)
- [ ] REF-3: MVVM/MVP Pattern
- [ ] REF-5: Dependency Injection
- [ ] REF-6: AsyncIO Integration
- [ ] FEAT-2: Undo/Rollback
- [ ] FEAT-4: Plugin-System
- [ ] FEAT-14: Statistics Dashboard

### Backlog (Unpriorisiert)
- [ ] REF-4: Structured Logging
- [ ] REF-7: Observable Streams
- [ ] REF-8: Pydantic Config
- [ ] REF-9: Result Types
- [ ] REF-10: atomicwrites
- [ ] TEST-3: E2E Integration
- [ ] TEST-4: Performance Benchmark
- [ ] TEST-5: Memory Leak Detection
- [ ] TEST-6: Security Fuzzing
- [ ] DOC-6: Video Tutorial
- [ ] FEAT-5: Cloud Backup
- [ ] FEAT-9: Drag & Drop
- [ ] FEAT-10: SQLite Export
- [ ] FEAT-13: Bulk Rename
- [ ] FEAT-15: Auto-Update

---

## 11. NOTIZEN

_Platz für Anmerkungen während der Abarbeitung:_

```
[2026-01-29] Initiales Audit erstellt - alle P0/P1/P2 bereits erledigt
```

---

## 12. CHANGELOG DIESER CHECKLISTE

| Datum | Änderung |
|-------|----------|
| 2026-01-29 | Initiale Erstellung |
| 2026-01-29 | DOC-4 abgeschlossen, Statistik aktualisiert |
| 2026-01-29 | TEST-1/TEST-2 abgeschlossen, Statistik aktualisiert |
| 2026-01-29 | DOC-1/DOC-2/DOC-3 abgeschlossen, Statistik aktualisiert |
| 2026-01-29 | FEAT-8 abgeschlossen, Statistik aktualisiert |
| 2026-01-29 | FEAT-7 abgeschlossen, Statistik aktualisiert |
| 2026-01-29 | REF-10 abgeschlossen, Statistik aktualisiert |
| 2026-01-29 | TEST-3 abgeschlossen, Statistik aktualisiert |
| 2026-01-29 | TEST-4/TEST-5/TEST-6 abgeschlossen, Statistik aktualisiert |
| 2026-01-29 | FEAT-12 abgeschlossen, Statistik aktualisiert |
| 2026-01-29 | FEAT-11 abgeschlossen, Statistik aktualisiert |
| 2026-01-29 | FEAT-9 abgeschlossen, Statistik aktualisiert |

---
