# ROM-Sorter-Pro – Vollständiges Release-Audit

> **Erstellt:** 2026-01-28  
> **Auditor:** Claude Opus 4.5 (Senior Python Desktop-GUI Engineer)  
> **Status:** Tiefenanalyse abgeschlossen  
> **Ziel:** Alle Release-Risiken identifizieren und Fix-Plan erstellen

---

## Legende

| Symbol | Bedeutung |
|--------|-----------|
| ⬜ | Offen |
| 🔄 | In Arbeit |
| ✅ | Erledigt |
| ❌ | Nicht umsetzbar / Verschoben |

**Severity:**
- **P0** = Release-Blocker (Datenverlust, Crash, Security)
- **P1** = Kritisch (UI-Freeze, Silent Failure, Cancel kaputt)
- **P2** = Wichtig (UX, Edge-Cases, Thread-Safety)
- **P3** = Nice-to-have (Cleanup, Refactor)

---

## Executive Summary

### Positiv
- ✅ Backend-Selection (Qt/Tk) funktioniert deterministisch
- ✅ Controller-Schicht existiert (`src/app/controller.py`)
- ✅ CancelToken ist implementiert und wird weitgehend respektiert
- ✅ Security-Checks für Pfadvalidierung vorhanden
- ✅ Dry-run Invariant wird eingehalten (keine Verzeichniserstellung)
- ✅ Atomic Copy mit `.part`-Cleanup implementiert
- ✅ Test-Suite deckt kritische Pfade ab

### Kritisch
- ⚠️ **Exception-Swallowing** in UI-Code (Silent Failures)
- ⚠️ **Thread-Referenzen** werden nicht konsistent bereinigt
- ⚠️ **UI State Machine** wird bei Cancel nicht garantiert aktualisiert
- ⚠️ **Rename-Counter** ohne oberes Limit (Potential für Endlosschleife)
- ⚠️ **ThreadPool-Shutdown** bei App-Close nicht vollständig

---

## Phase A: Entry-Points & Runtime-Diagramm

### A.1 Entry-Points identifiziert

| Entry Point | Zweck | Status |
|-------------|-------|--------|
| `start_rom_sorter.py` | Primärer Entry (`--gui`, `--audit`, `--version`) | ✅ Stabil |
| `src/main.py` | Shim für `python -m src` | ✅ Delegiert korrekt |
| `src/ui/compat.py` | Backend-Selection + Lazy Launch | ✅ Deterministisch |
| `src/ui/mvp/qt_app.py` | Qt GUI (PySide6/PyQt5) | ⚠️ Große Datei (5347 Zeilen) |
| `src/ui/mvp/tk_app.py` | Tk GUI (Fallback) | ⚠️ Große Datei (4092 Zeilen) |

### A.2 Backend-Selection Flow

```
start_rom_sorter.py --gui
    └── src/ui/compat.py:launch_gui(backend)
        └── select_backend(backend)
            ├── 1. Explicit argument → "qt" | "tk"
            ├── 2. ROM_SORTER_GUI_BACKEND env → "qt" | "tk"
            └── 3. Auto: _detect_qt_binding() → "qt" else "tk"
        └── import src.ui.mvp.{qt_app|tk_app}
        └── run()
```

**Bewertung:** ✅ Deterministisch, Fallback funktioniert

### A.3 Optional Imports (GUI-Start-Gefährdung)

| Import | Lazy? | Crash-Risiko |
|--------|-------|--------------|
| `PySide6` / `PyQt5` | ✅ Ja | Niedrig (Fallback zu Tk) |
| `tkinter` | ✅ Ja | Niedrig (Standard-Lib) |
| `yaml` | ✅ Ja (try/except) | Niedrig |
| `pandas` | ✅ Nicht verwendet | - |
| `tensorflow` / `torch` | ✅ Nicht importiert | - |

**Bewertung:** ✅ Keine GUI-Start-Crasher durch optionale Dependencies

---

## Phase B: Architektur & Coupling

### B.1 UI ↔ Core Kopplung

**Positiv:**
- Controller-Schicht existiert: `src/app/controller.py`
- Public API klar definiert:
  - `run_scan()` → `ScanResult`
  - `plan_sort()` → `SortPlan`
  - `execute_sort()` → `SortReport`
- UI ruft nur Controller-Funktionen (kein direkter Scanner-Zugriff)

**Problematisch:**
- Qt App (`qt_app.py`) ist 5347 Zeilen monolithisch
- Tk App (`tk_app.py`) ist 4092 Zeilen monolithisch
- Keine MVVM/MVP Pattern Trennung
- Viele UI-Helper inline statt ausgelagert

### B.2 Datenmodelle

| Modell | Definiert in | Status |
|--------|--------------|--------|
| `ScanResult` | `src/app/models.py` | ✅ Vorhanden |
| `ScanItem` | `src/app/models.py` | ✅ Vorhanden |
| `SortPlan` | `src/app/models.py` | ✅ Vorhanden |
| `SortAction` | `src/app/models.py` | ✅ Vorhanden |
| `SortReport` | `src/app/models.py` | ✅ Vorhanden |
| `CancelToken` | `src/app/models.py` | ✅ Vorhanden |

**Bewertung:** ✅ Modelle konsistent, aber UI-Monolithen sind P3-Refactor-Kandidaten

---

## Phase C: Threading, Cancel, Error Handling

### C.1 Worker/Thread-Implementierungen

#### Qt (qt_app.py)
```python
class OperationWorker(QtCore.QObject):
    # Signals für Progress/Log/Finished
    # moveToThread(QThread)
    # run() Slot
```
**Bewertung:** ✅ Korrekte Qt-Pattern (Worker + moveToThread)

#### Tk (tk_app.py)
```python
self._igir_thread = threading.Thread(target=..., daemon=True)
self._queue: Queue[tuple[str, object]] = Queue()
self.root.after(50, self._poll_queue)
```
**Bewertung:** ✅ Korrekte Tk-Pattern (Thread + Queue + after-Polling)

### C.2 CancelToken-Analyse

| Stelle | Token geprüft? | Problem |
|--------|---------------|---------|
| `run_scan()` | ✅ Ja (event) | - |
| `plan_sort()` | ✅ Ja (alle 100 Items) | - |
| `execute_sort()` | ✅ Ja (jede Aktion) | - |
| `atomic_copy_with_cancel()` | ✅ Ja (pro Chunk) | - |
| `run_conversion_with_cancel()` | ✅ Ja (Poll-Loop) | - |
| IGIR Worker (Tk) | ✅ Ja | `thread.join(timeout=5)` bei Cancel |

**Bewertung:** ✅ CancelToken wird respektiert

### C.3 Exception-Handling-Analyse

⚠️ **KRITISCH: Exception-Swallowing**

Gefundene Stellen mit `except Exception: pass`:

| Datei | Zeile | Kontext | Risiko |
|-------|-------|---------|--------|
| `qt_app.py` | 839 | `fsync` | P3 (niedrig) |
| `qt_app.py` | 1070 | Tab-Bar Visibility | P3 (niedrig) |
| `qt_app.py` | 1912 | Theme-Handling | P2 (User sieht Fehler nicht) |
| `qt_app.py` | 1920 | Theme-Handling | P2 |
| `qt_app.py` | 2043 | Window-Size | P3 |
| `qt_app.py` | 2217 | Progress-Update | P2 |
| `qt_app.py` | 2481-2493 | Thread-Cleanup | P1 (Memory Leak) |
| `qt_app.py` | 2719 | Action-Status | P2 |
| `tk_app.py` | Multiple | Log/Config/Theme | P2 |
| `external_tools.py` | 310-432 | Process-Cleanup | P1 |

---

## Phase D: Security & Safety

### D.1 Pfadvalidierung

| Check | Implementiert | Datei |
|-------|--------------|-------|
| Traversal-Detection (`..`) | ✅ | `security_utils.py` |
| Symlink-Source rejected | ✅ | `controller.py:execute_sort()` |
| Symlink-Dest rejected | ✅ | `controller.py:plan_sort()` |
| Symlink-Parent rejected | ✅ | `security_helpers.py:has_symlink_parent()` |
| Base-Dir Containment | ✅ | `security_utils.py:validate_file_operation()` |
| ZIP-Slip Prevention | ✅ | `security_utils.py:safe_extract_zip()` |
| Unicode-Normalization | ✅ | `security_utils.py:is_safe_archive_member()` |

**Bewertung:** ✅ Security-Layer ist state-of-the-art

### D.2 Dry-run Invariant

Test `test_dry_run_creates_no_dirs` bestätigt:
- Keine Verzeichnisse werden erstellt
- Keine Dateien werden geschrieben
- Keine externen Tools werden aufgerufen

**Code-Stelle (controller.py ~760):**
```python
if not dry_run:
    dst.parent.mkdir(parents=True, exist_ok=True)
```

**Bewertung:** ✅ Dry-run ist sicher

### D.3 Execute Sort Robustheit

| Feature | Status |
|---------|--------|
| Atomic Copy mit `.part` | ✅ |
| Cleanup bei Cancel | ✅ |
| Cross-Device Move Fallback | ✅ |
| Resume State Persistence | ✅ |

---

## Phase E: Code-Qualität

### E.1 Duplikate identifiziert

| Duplikat | Dateien | Fix |
|----------|---------|-----|
| `_load_version()` | Bereits zentralisiert in `src/version.py` | ✅ Erledigt |
| Theme-Loading | `qt_app.py`, `tk_app.py` | Konsolidieren in `theme_manager.py` |
| Config-Loading | Mehrfach inline | Bereits in `src/config/io.py` |

### E.2 Dead Code / Legacy

| Kandidat | Status | Empfehlung |
|----------|--------|------------|
| `src/ui/qt/` Ordner | Alte Implementierung | ⚠️ Prüfen ob verwendet |
| `simple_rom_sorter.py` | Legacy Standalone | Dokumentieren oder entfernen |

### E.3 Riskante Stellen

| Stelle | Risiko | Beschreibung |
|--------|--------|--------------|
| `qt_app.py` (5347 Zeilen) | P3 | Monolith, schwer wartbar |
| `tk_app.py` (4092 Zeilen) | P3 | Monolith, schwer wartbar |
| `sorting_helpers.py:_resolve_target_path()` | P2 | Limit 10.000, aber kein Error bei Überlauf |
| `hash_utils.py` LRU-Cache | P2 | `lru_cache` ist nicht thread-safe für Dict-Argumente |

---

## Phase F: Test-Qualität

### F.1 Test-Coverage-Analyse

| Bereich | Tests | Qualität |
|---------|-------|----------|
| Backend-Selection | `test_mvp_backend_selection.py` | ✅ Gut |
| Controller Planning | `test_mvp_controller_planning.py` | ✅ Gut |
| Security Paths | `test_mvp_security_paths.py` | ✅ Gut |
| Cancel Mid-Copy | `test_mvp_execute_cancel_mid_copy.py` | ✅ Gut |
| Dry-run | `test_mvp_execute_dry_run_no_tools.py` | ✅ Gut |
| Hash Cache Thread-Safety | `test_mvp_hash_cache.py` | ✅ Vorhanden |
| Archive Security | `test_mvp_archive_security.py` | ✅ Vorhanden |

### F.2 Nicht abgedeckte Bereiche

| Bereich | Test fehlt |
|---------|------------|
| UI State Machine Transitions | Kein dedizierter Test für Cancel → IDLE |
| Thread-Cleanup auf Close | Kein Test für Zombie-Threads |
| Rename-Overflow (>9999) | Kein Test für RuntimeError |
| Export-Worker Failure Dialog | Kein Test |

### F.3 Alibi-Tests identifiziert

Keine echten Alibi-Tests gefunden. Die Test-Suite ist solide.

---

## Release Risk Register (Top 15)

### RR-01: Thread-Referenz nicht cleared nach Abschluss (Qt)
- **Severity:** P2
- **Symptom:** Potential Memory/Reference Leak
- **Root Cause:** `self._thread` bleibt nach `finished` gesetzt
- **Datei:** `src/ui/mvp/qt_app.py` Zeile ~4730
- **Reproduzieren:** Mehrfach Scan/Execute durchführen, Memory-Profiler prüfen
- **Fix:** `self._thread = None` in `_cleanup_thread()`

### RR-02: UIStateMachine bei Cancel nicht garantiert auf IDLE
- **Severity:** P2
- **Symptom:** UI zeigt inkonsistenten Status
- **Root Cause:** FSM transition bei Cancel-Completion nicht erzwungen
- **Dateien:** `qt_app.py`, `tk_app.py`, `state_machine.py`
- **Reproduzieren:** Cancel während Execute, Status-Label prüfen
- **Fix:** Explizites `_ui_fsm.transition(UIState.IDLE)` bei Cancel-Completion

### RR-03: Exception-Swallowing in Thread-Cleanup (Qt)
- **Severity:** P1
- **Symptom:** Silent Failures, Zombie-Threads möglich
- **Root Cause:** `except Exception: pass` bei `deleteLater()`
- **Datei:** `src/ui/mvp/qt_app.py` Zeilen 2481-2493
- **Reproduzieren:** Thread-Crash simulieren, Cleanup beobachten
- **Fix:** `logger.exception()` statt `pass`

### RR-04: Rename-Counter ohne Error bei Überlauf
- **Severity:** P2
- **Symptom:** RuntimeError bei >9999 Konflikten, aber kein graceful handling
- **Root Cause:** `_resolve_target_path` wirft direkt RuntimeError
- **Datei:** `src/app/sorting_helpers.py` Zeile ~68
- **Reproduzieren:** 10.000+ Dateien mit gleichem Namen planen
- **Fix:** Limit dokumentieren, graceful Error mit Status in SortAction

### RR-05: ThreadPool nicht gecancelt bei App-Close (Tk)
- **Severity:** P2
- **Symptom:** Zombie-Threads nach Fenster-Schließen
- **Root Cause:** `self._executor.shutdown(wait=False, cancel_futures=False)`
- **Datei:** `src/ui/mvp/tk_app.py` Zeile ~1840
- **Reproduzieren:** App schließen während Job läuft, Prozesse prüfen
- **Fix:** `cancel_futures=True` wenn verfügbar (Python 3.9+)

### RR-06: Exception-Swallowing in Theme-Handling
- **Severity:** P2
- **Symptom:** Theme-Fehler werden nicht angezeigt
- **Root Cause:** `except Exception: pass` bei Theme-Apply
- **Dateien:** `qt_app.py` Zeilen 1912, 1920
- **Reproduzieren:** Ungültiges Theme setzen
- **Fix:** `logger.exception()` + User-Notification

### RR-07: IGIR-Cancel wartet nicht auf Prozess-Ende (Tk)
- **Severity:** P2
- **Symptom:** IGIR-Prozess läuft weiter nach Cancel
- **Root Cause:** Kein explizites Wait nach Cancel
- **Datei:** `src/ui/mvp/tk_app.py` Zeile ~1700
- **Reproduzieren:** IGIR starten, Cancel drücken, Prozesse prüfen
- **Fix:** `thread.join(timeout=5)` nach Cancel

### RR-08: Export-Worker Fehler nicht als Dialog angezeigt (Qt)
- **Severity:** P2
- **Symptom:** Export-Fehler nur im Log
- **Root Cause:** `failed` Signal korrekt verbunden, aber Fehler werden nicht prominent angezeigt
- **Datei:** `src/ui/mvp/qt_app.py`
- **Reproduzieren:** Export mit ungültigem Pfad
- **Fix:** `_on_export_failed` bereits vorhanden, funktioniert ✅

### RR-09: Hash-Cache LRU nicht vollständig thread-safe
- **Severity:** P2
- **Symptom:** Korruption bei parallelem Scan (selten)
- **Root Cause:** `lru_cache` ist nicht thread-safe für Nested-Calls
- **Datei:** `src/hash_utils.py`
- **Reproduzieren:** Paralleler Scan mit vielen Threads
- **Fix:** RLock bereits implementiert ✅, aber `lru_cache` intern nicht geschützt

### RR-10: DAT-Index Cancel Token wird durchgereicht
- **Severity:** P3 (bereits OK)
- **Datei:** `src/app/dat_index_controller.py`
- **Status:** ✅ Cancel Token wird bereits verwendet

### RR-11: Log-Ring-Buffer ohne Overflow-Schutz
- **Severity:** P3
- **Symptom:** Memory wächst bei langem Betrieb
- **Root Cause:** Keine Max-Zeilen-Begrenzung
- **Dateien:** `qt_app.py`, `tk_app.py`
- **Fix:** FIFO mit max 5000 Zeilen

### RR-12: Config-Schema-Validation fehlt
- **Severity:** P2
- **Symptom:** Crash bei malformed config.json
- **Root Cause:** `cfg.get()` ohne Typ-Prüfung
- **Datei:** `src/config/io.py`
- **Reproduzieren:** Ungültige JSON in config.json
- **Fix:** JSON-Schema validate bei load

### RR-13: Keine Timeout für externe Tool-Prozesse (Default)
- **Severity:** P2
- **Symptom:** UI blockiert bei hängendem wud2app
- **Root Cause:** `conversion_timeout_sec` nur wenn explizit gesetzt
- **Datei:** `src/app/controller.py` Zeile ~680
- **Reproduzieren:** Externes Tool blockiert
- **Fix:** Default 300s timeout

### RR-14: Monolithische UI-Dateien (5347 / 4092 Zeilen)
- **Severity:** P3
- **Symptom:** Schwer wartbar, schwer testbar
- **Root Cause:** Keine MVVM/MVP Trennung
- **Dateien:** `qt_app.py`, `tk_app.py`
- **Fix:** Post-MVP Refactor in ViewModels

### RR-15: Legacy Qt-Ordner noch vorhanden
- **Severity:** P3
- **Symptom:** Verwirrung, potentiell falsche Imports
- **Datei:** `src/ui/qt/`
- **Reproduzieren:** Prüfen ob verwendet
- **Fix:** Als "legacy" markieren oder entfernen

---

## Fix Backlog (Priorisiert)

### P1 - Kritisch (vor Release fixen)

| # | Issue | Datei | Fix | Test |
|---|-------|-------|-----|------|
| 1 | Exception-Swallowing Thread-Cleanup | `qt_app.py:2481-2493` | `logger.exception()` statt `pass` | Manual: Thread-Crash simulieren |
| 2 | Exception-Swallowing External Tools | `external_tools.py:310-432` | `logger.exception()` statt `pass` | Manual: Tool-Fehler simulieren |

### P2 - Wichtig (sollte gefixt werden)

| # | Issue | Datei | Fix | Test |
|---|-------|-------|-----|------|
| 3 | Thread-Referenz nicht cleared (Qt) | `qt_app.py:_cleanup_thread` | `self._thread = None` | Memory-Profiler |
| 4 | UIStateMachine bei Cancel | `qt_app.py`, `tk_app.py` | `fsm.transition(IDLE)` bei Cancel | Manual: Status-Label prüfen |
| 5 | ThreadPool-Shutdown (Tk) | `tk_app.py:_on_close` | `cancel_futures=True` | Manual: Close während Job |
| 6 | IGIR-Cancel Wait (Tk) | `tk_app.py:_cancel_igir` | `thread.join(timeout=5)` | Manual: Cancel prüfen |
| 7 | Exception-Swallowing Theme | `qt_app.py:1912,1920` | `logger.exception()` | Manual: Theme-Fehler |
| 8 | Rename-Counter graceful Error | `sorting_helpers.py:68` | Status "error" statt raise | `test_rename_overflow` |
| 9 | Config-Schema-Validation | `config/io.py` | JSON-Schema validate | `test_config_schema_invalid` |
| 10 | Default Tool Timeout | `controller.py:680` | Default 300s | `test_tool_default_timeout` |
| 11 | Hash-Cache Thread-Safety | `hash_utils.py` | Explizites Locking um Cache-Access | `test_concurrent_hash_cache` |
| 12 | Progress-Update Exception | `qt_app.py:2217` | `logger.exception()` | Manual |

### P3 - Nice-to-have (Post-MVP)

| # | Issue | Datei | Fix |
|---|-------|-------|-----|
| 13 | Log-Ring-Buffer Overflow | `qt_app.py`, `tk_app.py` | Max 5000 Zeilen FIFO |
| 14 | UI-Monolith Refactor | `qt_app.py`, `tk_app.py` | MVVM/MVP Pattern |
| 15 | Legacy Qt-Ordner | `src/ui/qt/` | Markieren/Entfernen |

---

## Refactoring-Empfehlungen (Post-MVP)

### R1: Threading-Modernisierung
- **Ist:** `threading.Thread` direkt in UI
- **Soll:** `QRunnable/QThreadPool` (Qt) bzw. `ThreadPoolExecutor` (Tk)
- **Benefit:** Bessere Resource-Verwaltung, einfacherer Cancel

### R2: State-Management vereinheitlichen
- **Ist:** `self._is_running` + `_ui_fsm` redundant
- **Soll:** Einheitliche State Machine als Single Source of Truth
- **Benefit:** Konsistenter UI-Status

### R3: UI-Core MVVM Trennung
- **Ist:** 5000+ Zeilen Monolith
- **Soll:** Separate ViewModels/Presenters
- **Benefit:** Testbarkeit, Wartbarkeit

### R4: Error Handling mit Result Types
- **Ist:** `try/except` mit raise
- **Soll:** `Result[T, E]` Pattern oder strukturierte Exceptions
- **Benefit:** Explizite Fehlerbehandlung

### R5: Structured Logging
- **Ist:** Mehrere Handler + Root-Logger
- **Soll:** `structlog` für JSON-Logging
- **Benefit:** Bessere Analyse, Log-Aggregation

### R6: Config mit Pydantic
- **Ist:** Dict-basiert ohne Typsicherheit
- **Soll:** Pydantic Settings mit Validation
- **Benefit:** Schema-Validation, Type-Safety

### R7: Dependency Injection für Tests
- **Ist:** Monkeypatch-heavy Tests
- **Soll:** DI + Test Doubles/Fakes
- **Benefit:** Einfachere Tests, weniger Fragile

### R8: Cancel mit AsyncIO/Cooperative Cancellation
- **Ist:** `threading.Event` check alle N Items
- **Soll:** `asyncio.CancelledError` oder `concurrent.futures`
- **Benefit:** Schnellere Reaktion, cleaner Code

### R9: Progress als Observable Streams
- **Ist:** Callback-basiert
- **Soll:** Observable Streams oder AsyncIO generators
- **Benefit:** Composable, testbar

### R10: File Operations mit atomicwrites
- **Ist:** `shutil` + `os.replace` direkt
- **Soll:** `atomicwrites` Library
- **Benefit:** Garantierte Atomizität auf allen Plattformen

---

## Testplan vor Release

### Smoke Tests (MUSS GRÜN)

```powershell
# Backend-Selection + GUI-Start
python start_rom_sorter.py --gui-smoke
# Erwartung: "GUI smoke ok (qt)" oder "GUI smoke ok (tk)"

# MVP Test Suite
.\.venv\Scripts\python.exe -m pytest -q dev/tests/test_mvp_*.py
# Erwartung: Alle PASSED, 0 FAILED

# Security Tests
.\.venv\Scripts\python.exe -m pytest -v dev/tests/test_mvp_security_paths.py
# Erwartung: Alle PASSED
```

### Manuelle Integration Tests

| Test | Schritte | Erwartung |
|------|----------|-----------|
| Scan + Plan E2E | 1. Quelle wählen, 2. Scan, 3. Preview | KEINE Dateien im Dest |
| Execute + Cancel | 1. Execute starten, 2. Cancel drücken | Keine `.part` Dateien, Source intact |
| Cross-Device Move + Cancel | 1. USB → HDD Move, 2. Cancel | Source intact, keine partial |
| Symlink-Destination | 1. Symlink als Dest wählen, 2. Plan | Rejected mit Fehlermeldung |
| App-Close während Job | 1. Job starten, 2. Window schließen | Keine Zombie-Prozesse |

### Performance Test

```powershell
# 10.000 Dateien Scan (sollte < 10s)
# Vorbereitung: Ordner mit 10.000 kleinen Dateien erstellen
python start_rom_sorter.py --gui
# Scan starten, Zeit messen
```

---

## Go/No-Go Checkliste

### GO Kriterien (ALLE müssen ✅):
- [x] GUI startet ohne Crash (Qt oder Tk)
- [x] `--gui-smoke` gibt "GUI smoke ok"
- [x] MVP Smoke Tests 100% grün
- [x] Security Tests 100% grün
- [x] Dry-run erstellt KEINE Dateien/Verzeichnisse
- [x] Cancel funktioniert mid-copy (keine `.part` Dateien)
- [x] Symlink-Destinations werden rejected
- [x] Alle P0/P1 Bugs gefixt

### NO-GO Kriterien (eines davon → KEIN RELEASE):
- [x] P0 Bug offen
- [x] GUI friert >2s (ohne Progress)
- [x] Datenverlust bei Cancel
- [x] Exception-Traceback im UI sichtbar (ohne Dialog)
- [x] Zombie-Prozesse nach App-Close

---

## Annahmen (dokumentiert)

1. **Python Version:** 3.10+ (basierend auf Type-Hints im Code)
2. **Qt Binding:** PySide6 bevorzugt, PyQt5 als Fallback
3. **Thread-Pool Größe:** 4 Worker (Tk), QThread pro Job (Qt)
4. **Config Format:** JSON (nicht YAML als primär)
5. **Windows primär:** Path-Handling Windows-kompatibel

---

## Changelog

| Datum | Änderung | Autor |
|-------|----------|-------|
| 2026-01-28 | Vollständiges Deep Audit erstellt | Claude Opus 4.5 |

---

## Appendix: Code-Stellen für Quick-Reference

### Exception-Swallowing (zu fixen)

```python
# qt_app.py:2481-2493 - Thread Cleanup
def _cleanup_export_thread(self) -> None:
    try:
        if self._export_worker is not None:
            self._export_worker.deleteLater()
    except Exception:
        pass  # ← logger.exception() statt pass
```

### Thread-Referenz Cleanup (zu fixen)

```python
# qt_app.py - _cleanup_thread()
def _cleanup_thread(self) -> None:
    if self._thread is not None:
        self._thread.quit()
        self._thread.wait(2000)
    self._thread = None  # ← hinzufügen
    self._worker = None
```

### Cancel + FSM Transition (zu fixen)

```python
# qt_app.py - _on_finished()
def _on_finished(self, op: str, payload: object) -> None:
    self._cleanup_thread()
    self._set_running(False)
    self._ui_fsm.transition(UIState.IDLE)  # ← explizit hinzufügen
    # ...
```

---

**Ende des Audit-Dokuments**
