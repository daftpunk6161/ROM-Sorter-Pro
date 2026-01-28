# ROM-Sorter-Pro – Release Audit Backlog

> **Erstellt:** 2026-01-28  
> **Status:** Pre-Release Audit  
> **Ziel:** Alle Findings abarbeiten vor v1.0 Release

---

## Legende

| Symbol | Bedeutung |
|--------|-----------|
| ⬜ | Offen |
| 🔄 | In Arbeit |
| ✅ | Erledigt |
| ❌ | Nicht umsetzbar / Verschoben |

**Severity:**
- **P0** = Release-Blocker (Datenverlust, Crash)
- **P1** = Kritisch (Security, UI-Freeze)
- **P2** = Wichtig (UX, Edge-Cases)
- **P3** = Nice-to-have

---

## 1. P0 – Release-Blocker

### 1.1 Cross-Device Move nutzt falsche Funktion
- [ ] **Status:** ⬜ Offen
- **Severity:** P0
- **Symptom:** Hänger bei Move zwischen Laufwerken + Cancel
- **Root Cause:** `_atomic_copy_with_cancel` (mit Underscore) statt `atomic_copy_with_cancel`
- **Datei:** `src/app/controller.py` Zeile ~867-900
- **Fix:** 
  ```python
  # Ändern von:
  ok = _atomic_copy_with_cancel(...)
  # Zu:
  ok = atomic_copy_with_cancel(...)
  ```
- **Test:** `test_mvp_execute_cancel_mid_copy::test_execute_sort_cancel_mid_move_cross_device` (NEU erstellen)
- **Reproduzieren:** Move von USB→HDD, dann Cancel drücken

---

### 1.2 Dry-run erstellt Verzeichnisse
- [ ] **Status:** ⬜ Offen
- **Severity:** P0
- **Symptom:** Leere Verzeichnisse nach dry-run Preview
- **Root Cause:** `dst.parent.mkdir()` wird vor dry-run Check ausgeführt
- **Datei:** `src/app/controller.py` Zeile ~718-720
- **Fix:** `mkdir` nur wenn `not dry_run`
- **Test:** `test_mvp_execute_dry_run_no_tools::test_dry_run_creates_no_dirs` (NEU erstellen)
- **Reproduzieren:** Dry-run mit Conversion-Plan ausführen

---

## 2. P1 – Kritische Issues

### 2.1 Symlink-Destination bei plan nicht vollständig geprüft
- [ ] **Status:** ⬜ Offen
- **Severity:** P1
- **Symptom:** Symlink-Destination wird bei nicht-existenten Pfaden akzeptiert
- **Root Cause:** Check existiert nur für bereits existierende Pfade
- **Datei:** `src/app/controller.py` Zeile ~360-375
- **Fix:** `resolve()` vs `absolute()` Check auch für nicht-existente Pfade
- **Test:** `test_mvp_security_paths::test_plan_sort_rejects_symlink_parent` erweitern

---

### 2.2 Exception-Swallowing in Tk Worker
- [ ] **Status:** ⬜ Offen
- **Severity:** P1
- **Symptom:** Silent Failures, User sieht keine Fehlermeldung
- **Root Cause:** `except Exception: pass` an diversen Stellen
- **Datei:** `src/ui/mvp/tk_app.py` (mehrere Stellen)
- **Fix:** `except Exception as e: logger.exception(...)` statt `pass`
- **Betroffene Stellen:**
  - [ ] Zeile ~1200-1220 (Theme-Handling)
  - [ ] Zeile ~1500-1510 (Template-Handling)
  - [ ] Zeile ~2000+ (Dialog-Handling)

---

### 2.3 ZIP-Extraktion Unicode-Traversal
- [ ] **Status:** ⬜ Offen
- **Severity:** P1
- **Symptom:** Zip-Slip bei Unicode-Normalisierung möglich
- **Root Cause:** `safe_extract_zip` prüft nicht alle normalisierten Pfade
- **Datei:** `src/security/security_utils.py` Zeile ~305-330
- **Fix:** Unicode-Normalisierung vor Check + zusätzliche Pattern
- **Test:** `test_mvp_archive_security::test_safe_extract_unicode_traversal` (NEU erstellen)

---

## 3. P2 – Wichtige Issues

### 3.1 Thread-Referenz nicht cleared nach Abschluss (Qt)
- [ ] **Status:** ⬜ Offen
- **Severity:** P2
- **Symptom:** Potential Memory/Reference Leak
- **Root Cause:** `self._thread` bleibt nach `finished` gesetzt
- **Datei:** `src/ui/mvp/qt_app.py` Zeile ~4730
- **Fix:** `self._thread = None` in `_on_finished` Callback

---

### 3.2 UIStateMachine bei Cancel nicht aktualisiert
- [ ] **Status:** ⬜ Offen
- **Severity:** P2
- **Symptom:** UI zeigt "running" obwohl Job beendet
- **Root Cause:** FSM transition bei cancel nicht garantiert
- **Dateien:** 
  - `src/ui/mvp/qt_app.py`
  - `src/ui/mvp/tk_app.py`
  - `src/ui/state_machine.py`
- **Fix:** `fsm.transition(UIState.IDLE)` bei Cancel-Completion

---

### 3.3 Rename-Counter kann explodieren
- [ ] **Status:** ⬜ Offen
- **Severity:** P2
- **Symptom:** Endlosschleife bei >1000 Konflikten
- **Root Cause:** `_resolve_target_path` iteriert bis Match ohne Limit
- **Datei:** `src/app/sorting_helpers.py`
- **Fix:** Max 9999 Versuche, dann Error
- **Test:** `test_mvp_collision_policy::test_rename_overflow` (NEU erstellen)

---

### 3.4 Keine Timeout für externe Tool-Prozesse
- [ ] **Status:** ⬜ Offen
- **Severity:** P2
- **Symptom:** UI blockiert bei hängendem wud2app
- **Root Cause:** `run_conversion_with_cancel` hat keinen default timeout
- **Datei:** `src/app/execute_helpers.py` Zeile ~89-105
- **Fix:** Default 300s timeout + Config-Option
- **Test:** `test_mvp_wud2app_tools::test_timeout` (NEU erstellen)

---

### 3.5 ThreadPool nicht gecancelt bei App-Close
- [ ] **Status:** ⬜ Offen
- **Severity:** P2
- **Symptom:** Zombie-Threads nach Fenster-Schließen
- **Root Cause:** Kein explizites ThreadPool-Shutdown
- **Dateien:**
  - `src/ui/mvp/qt_app.py`
  - `src/ui/mvp/tk_app.py`
- **Fix:** `closeEvent`/`_on_close` ruft Cancel + join

---

### 3.6 Hash-Cache nicht thread-safe
- [ ] **Status:** ⬜ Offen
- **Severity:** P2
- **Symptom:** Korruption bei parallelem Scan (selten)
- **Root Cause:** SQLite ohne explizites Locking
- **Datei:** `src/hash_utils.py`
- **Fix:** `check_same_thread=False` oder explizites Locking
- **Test:** `test_mvp_hash_cache::test_concurrent_access` (NEU erstellen)

---

### 3.7 plan_sort wirft Exception bei Symlink-Dest
- [ ] **Status:** ⬜ Offen
- **Severity:** P2
- **Symptom:** Crash statt graceful handling
- **Root Cause:** `raise InvalidPathError` ohne Recovery
- **Datei:** `src/app/controller.py` Zeile ~360
- **Fix:** Catch + Action mit status="error" statt raise

---

### 3.8 Dry-run Status inkonsistent
- [ ] **Status:** ⬜ Offen
- **Severity:** P2
- **Symptom:** Log zeigt "Would convert" aber Status zeigt "converted"
- **Root Cause:** `action_status_cb` setzt falschen Status
- **Datei:** `src/app/controller.py` Zeile ~720
- **Fix:** Status = "dry-run (convert)" konsistent in Report

---

### 3.9 Keine Config-Schema-Validation
- [ ] **Status:** ⬜ Offen
- **Severity:** P2
- **Symptom:** Crash bei malformed config.json
- **Root Cause:** `cfg.get()` ohne Schema-Prüfung
- **Datei:** `src/config/io.py`
- **Fix:** JSON-Schema validate bei load
- **Test:** `test_mvp_format_validation::test_config_schema` (NEU erstellen)

---

### 3.10 Kein Test für mid-conversion cancel
- [ ] **Status:** ⬜ Offen
- **Severity:** P2
- **Symptom:** Untested Edge-Case
- **Root Cause:** Fehlender Test
- **Datei:** `dev/tests/test_mvp_execute_cancel.py`
- **Fix:** Monkeypatch subprocess + cancel Test hinzufügen

---

## 4. P3 – Nice-to-Have / Cleanup

### 4.1 Log-Ring-Buffer Overflow-Schutz
- [ ] **Status:** ⬜ Offen
- **Severity:** P3
- **Dateien:** `src/ui/mvp/qt_app.py`, `src/ui/mvp/tk_app.py`
- **Fix:** Max 5000 Zeilen, danach FIFO

---

### 4.2 IGIR-Cancel wartet nicht auf Prozess-Ende
- [ ] **Status:** ⬜ Offen
- **Severity:** P3
- **Datei:** `src/ui/mvp/tk_app.py`
- **Fix:** `thread.join(timeout=5)` nach cancel

---

### 4.3 DAT-Index Cancel Token nicht weitergereicht
- [ ] **Status:** ⬜ Offen
- **Severity:** P3
- **Datei:** `src/app/dat_index_controller.py`
- **Fix:** `cancel_token` Parameter durchreichen

---

### 4.4 Export-Worker Fehler nicht angezeigt
- [ ] **Status:** ⬜ Offen
- **Severity:** P3
- **Datei:** `src/ui/mvp/qt_app.py`
- **Fix:** `failed` Signal → Dialog

---

## 5. Code-Duplikate & Dead Code

### 5.1 Duplicate: `_load_version()` Funktion
- [ ] **Status:** ⬜ Offen
- **Severity:** P3
- **Problem:** Gleiche Funktion in zwei Dateien
- **Dateien:**
  - `start_rom_sorter.py`
  - `src/ui/mvp/qt_app.py`
- **Fix:** Zentralisieren in `src/version.py`

---

### 5.2 Unused: `simple_rom_sorter.py`
- [ ] **Status:** ⬜ Offen
- **Severity:** P3
- **Problem:** Legacy-Datei, wird nicht mehr verwendet
- **Datei:** Repo-Root
- **Fix:** Entfernen oder dokumentieren als Standalone-Tool

---

### 5.3 Dead Code Check: `src/ui/qt/` Ordner
- [ ] **Status:** ⬜ Offen
- **Severity:** P3
- **Problem:** Alte Qt-Implementierung neben MVP
- **Datei:** `src/ui/qt/`
- **Fix:** Prüfen ob verwendet, sonst entfernen oder als "legacy" markieren

---

### 5.4 Global State: ThemeManager Singleton
- [ ] **Status:** ⬜ Offen
- **Severity:** P3
- **Problem:** Globaler State erschwert Testing
- **Datei:** `src/ui/theme_manager.py`
- **Fix:** Dependency Injection Pattern

---

### 5.5 Side-Effect: logging.basicConfig bei Import
- [ ] **Status:** ⬜ Offen
- **Severity:** P3
- **Problem:** Logging wird bei Import konfiguriert
- **Datei:** `start_rom_sorter.py`
- **Fix:** Nur in `if __name__ == "__main__"` Block

---

## 6. Refactoring-Empfehlungen (Post-MVP)

### 6.1 Threading-Modernisierung
- [ ] **Status:** ⬜ Offen (Post-MVP)
- **Ist:** `threading.Thread` direkt in UI
- **Soll:** QThread/QRunnable (Qt) bzw. ThreadPoolExecutor (Tk)
- **Dateien:** `src/ui/mvp/qt_app.py`, `src/ui/mvp/tk_app.py`

---

### 6.2 State-Management vereinheitlichen
- [ ] **Status:** ⬜ Offen (Post-MVP)
- **Ist:** `self._is_running` + `_ui_fsm` redundant
- **Soll:** Einheitliche State Machine als Single Source of Truth
- **Dateien:** `src/ui/mvp/qt_app.py`, `src/ui/mvp/tk_app.py`

---

### 6.3 Config mit Pydantic
- [ ] **Status:** ⬜ Offen (Post-MVP)
- **Ist:** Dict-basiert ohne Typsicherheit
- **Soll:** Pydantic Settings mit Validation
- **Dateien:** `src/config/`

---

### 6.4 Error Handling verbessern
- [ ] **Status:** ⬜ Offen (Post-MVP)
- **Ist:** `except Exception: pass`
- **Soll:** Result Types (Ok/Err) oder Structured Exceptions
- **Überall im Projekt**

---

### 6.5 File Operations mit atomicwrites
- [ ] **Status:** ⬜ Offen (Post-MVP)
- **Ist:** `shutil` + `os.replace` direkt
- **Soll:** `atomicwrites` Library für garantierte Atomizität
- **Datei:** `src/app/execute_helpers.py`

---

### 6.6 UI-Core Coupling reduzieren
- [ ] **Status:** ⬜ Offen (Post-MVP)
- **Ist:** `qt_app.py` 5000+ Zeilen monolithisch
- **Soll:** MVVM/MVP Pattern mit separaten ViewModels
- **Datei:** `src/ui/mvp/qt_app.py`

---

### 6.7 Structured Logging
- [ ] **Status:** ⬜ Offen (Post-MVP)
- **Ist:** Mehrere Handler + Root-Logger
- **Soll:** structlog für JSON-Logging
- **Dateien:** Überall

---

### 6.8 Dependency Injection für Tests
- [ ] **Status:** ⬜ Offen (Post-MVP)
- **Ist:** Monkeypatch-heavy Tests
- **Soll:** DI + Test Doubles/Fakes
- **Dateien:** `dev/tests/`

---

### 6.9 Cancel mit AsyncIO/Cooperative Cancellation
- [ ] **Status:** ⬜ Offen (Post-MVP)
- **Ist:** `threading.Event` check alle 100 Items
- **Soll:** `asyncio.CancelledError` oder `concurrent.futures`
- **Dateien:** `src/app/controller.py`, `src/app/execute_helpers.py`

---

### 6.10 Progress als Observable Streams
- [ ] **Status:** ⬜ Offen (Post-MVP)
- **Ist:** Callback-basiert
- **Soll:** Observable Streams (RxPY) oder AsyncIO generators
- **Dateien:** `src/app/controller.py`

---

## 7. Neue Tests zu erstellen

| # | Test-Name | Datei | Beschreibung |
|---|-----------|-------|--------------|
| [ ] | `test_execute_sort_cancel_mid_move_cross_device` | `test_mvp_execute_cancel_mid_copy.py` | Cancel bei Cross-Device Move |
| [ ] | `test_dry_run_creates_no_dirs` | `test_mvp_execute_dry_run_no_tools.py` | Dry-run Side-Effects |
| [ ] | `test_safe_extract_unicode_traversal` | `test_mvp_archive_security.py` | ZIP Unicode Attacks |
| [ ] | `test_rename_overflow` | `test_mvp_collision_policy.py` | >1000 Konflikte |
| [ ] | `test_timeout` | `test_mvp_wud2app_tools.py` | Tool Timeout |
| [ ] | `test_concurrent_access` | `test_mvp_hash_cache.py` | Thread-Safety |
| [ ] | `test_config_schema` | `test_mvp_format_validation.py` | Schema Validation |
| [ ] | `test_mid_conversion_cancel` | `test_mvp_execute_cancel.py` | Cancel während Conversion |

---

## 8. Testplan vor Release

### 8.1 Smoke Tests (MUSS GRÜN)
- [ ] `python start_rom_sorter.py --gui-smoke` → "GUI smoke ok"
- [ ] `.\.venv\Scripts\python.exe -m pytest -q dev/tests/test_mvp_*.py` → Alle PASSED
- [ ] `.\.venv\Scripts\python.exe -m pytest -v dev/tests/test_mvp_security_paths.py` → Alle PASSED

### 8.2 Manuelle Integration Tests
- [ ] Scan + Plan (Dry-run) E2E → KEINE Dateien im Dest
- [ ] Execute + Cancel → Keine .part Dateien
- [ ] Cross-Device Move + Cancel → Source intact
- [ ] Symlink-Destination rejected

### 8.3 Performance
- [ ] 10.000 Dateien Scan < 10s

---

## 9. Go/No-Go Checkliste

### GO Kriterien (alle müssen ✅):
- [ ] GUI startet ohne Crash (Qt oder Tk)
- [ ] MVP Smoke Tests 100% grün
- [ ] Security Tests 100% grün
- [ ] Dry-run erstellt KEINE Dateien/Verzeichnisse
- [ ] Cancel funktioniert mid-copy (keine .part Dateien)
- [ ] Symlink-Destinations werden rejected
- [ ] Alle P0 Bugs gefixt
- [ ] Alle P1 Bugs gefixt oder dokumentiert

### NO-GO Kriterien:
- [ ] P0 Bug offen → **KEIN RELEASE**
- [ ] GUI friert >2s → **KEIN RELEASE**
- [ ] Datenverlust bei Cancel → **KEIN RELEASE**
- [ ] Exception-Traceback im UI → **KEIN RELEASE**

---

## Changelog

| Datum | Änderung | Autor |
|-------|----------|-------|
| 2026-01-28 | Initial Audit erstellt | Claude Opus 4.5 |

---

## Notizen

_Platz für Anmerkungen während der Abarbeitung_

---
