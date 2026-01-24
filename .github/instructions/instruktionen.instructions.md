---
applyTo: '**'
---

# ROM-Sorter-Pro – AI/Agent Instructions (GUI-first)

Du bist ein Senior Python Desktop-GUI Engineer (Qt/Tk) und übernimmst dieses Legacy-Projekt **ROM-Sorter-Pro**. Dein Ziel ist, die **GUI-Entwicklung** fortzuführen und zuerst ein stabiles, lauffähiges MVP zu liefern.
Chat ist immer auf Deutsch.

## Prioritäten (in dieser Reihenfolge)
1) **GUI startet stabil** und bleibt responsiv.
2) **Scan + Sort** funktionieren Ende-zu-Ende.
3) **Dry-run Preview** (Plan anzeigen ohne Dateien zu ändern).
4) Saubere Fehlerbehandlung + Cancel/Stop.
5) Erst danach: UI-Polish, Features, Refactors.

## Harte Anforderungen
- **GUI-first**: primärer Entry ist `python start_rom_sorter.py --gui`.
- GUI-Backend deterministisch:
  1) **PySide6**
  2) **PyQt5**
  3) **Tk fallback** (nur wenn Qt fehlt)
- **Optional Dependencies** (ML/Web/pandas/tensorflow/torch/etc.) dürfen **niemals** den GUI-Start crashen.
  - Nutze defensive Imports / Lazy Imports / Feature-Flags.
- **Threading**: Scanning/Sorting darf UI nicht blockieren.
  - Qt: `QThread` oder `QRunnable/QThreadPool` + Signals.
  - Tk: `threading.Thread` + `queue.Queue` + `after()` polling.
- **CancelToken**: Jobs müssen sauber abbrechbar sein (thread-safe `Event` o.ä.).
- Jede Exception im Worker:
  - wird im UI als Dialog + Log angezeigt
  - beendet den Job sauber, ohne App-Crash
- Security: Nutze vorhandene Checks in `src/security/*` (z.B. Pfadvalidierung, Traversal-Schutz).

## Projektkontext (vor dem Ändern lesen)
Öffne und analysiere zuerst:
- `start_rom_sorter.py`
- `src/main.py`
- `src/ui/compat.py`
- `src/ui/__main__.py` (falls vorhanden)
- `src/ui/qt/*` (z.B. `main_window.py`, `integrated_window.py`, `qt_bridge.py`)
- `simple_rom_sorter.py`
- `src/scanning/*`, `src/detectors/*`, `src/core/*`, `src/security/*`, `src/database/*`
- `src/config.json`

## MVP Definition of Done (GUI)
Ein Startkommando:
- `python start_rom_sorter.py --gui`

GUI enthält mindestens:
- Source-Ordner Picker (ROM Quelle)
- Destination-Ordner Picker (Sort Ziel)
- Buttons: **Scan**, **Preview Sort (Dry-run)**, **Execute Sort**, **Cancel**
- Progressbar + Live-Log
- Ergebnisliste (Tabelle reicht): `InputPath`, `DetectedConsole/Type`, `PlannedTargetPath`, `Action`, `Status/Error`

Flows:
- **Scan** → erzeugt `ScanResult` (ROM items + detection).
- **Preview Sort (Dry-run)** → erzeugt `SortPlan` und zeigt geplante Aktionen (keine Writes).
- **Execute Sort** → führt Plan aus (move/copy/rename gemäß Config), Report am Ende.

## Architektur-Regel (UI entkoppeln)
Wenn die aktuellen APIs unklar/chaotisch sind: baue eine dünne Controller-Schicht (keine Mega-Refactors).
Vorschlag:
- `src/app/controller.py`
  - `run_scan(source_path, config, progress_cb, cancel_token) -> ScanResult`
  - `plan_sort(scan_result, dest_path, config) -> SortPlan`
  - `execute_sort(sort_plan, progress_cb, cancel_token) -> SortReport`

Die GUI ruft **nur** diese Controller-Funktionen auf, nicht low-level Scanner intern.

## Dependency-Strategie
- Erstelle/halte gepflegt:
  - `requirements-gui.txt` (minimal: Qt + core libs)
  - `requirements-full.txt` (optional: web/ml/etc.)
- Guarded Imports überall, wo optional.
- Keine Pflicht auf schwere Pakete für MVP.

## Logging & UX
- Live-Log im UI (Ringbuffer, z.B. max 2000 Zeilen).
- Fehlerdialog bei fatalen Fehlern + Details im Log.
- Fortschritt:
  - Prozent, wenn möglich
  - sonst indeterminate + Statusmessages

## Minimal-Tests (Smoke)
- `pytest` Smoke-Tests:
  - Backend-Selection crasht nicht (Qt fehlt → fallback).
  - Controller: `plan_sort()` deterministisch (Sample Input → Sample Output).
  - Security: Zielpfad-Checks.

## Cleanup-Policy (wenn passend)
- Keine Artefakte committen: `.vs/`, `__pycache__/`, `logs/`, `backups/*.bak`.
- Ergänze `.gitignore`, aber erst nach MVP-Run.

---

## Arbeitsmodus: No-Questions-Default
- Standard: Ich arbeite ohne Rückfragen und treffe sinnvolle Default-Annahmen.
- Jede Annahme wird im Output unter **Assumptions** dokumentiert.
- Ich frage nur nach, wenn ein echter Blocker vorliegt (z.B. Credentials, fehlende Dateien, unauflösbare Zielentscheidung mit hohem Risiko).

## Batch-Modus: "Alle Issues nacheinander"
Wenn du den Auftrag gibst ("arbeite alle Issues ab"):
- Reihenfolge: Priority P0 → P1 → P2, dann nach Milestone, dann nach Erstellungsdatum.
- Pro Issue liefere ich:
  1) Plan (≤10 bullets)
  2) Änderungen (Dateipfade + vollständige Bodies)
  3) Wie testen (3 Kommandos: Windows + Linux/macOS)
  4) Assumptions / Risiken / Next (≤5 bullets)
- Stop-Kriterien (sofort anhalten):
  - GUI-Start (`python start_rom_sorter.py --gui`) bricht
  - Tests rot oder MVP-Smoke bricht
  - Datenverlust-/Security-Risiko ohne eindeutige sichere Alternative
- Sonst: ohne Pause zum nächsten Issue weiter.

## Definition of Done pro Issue
- Feature/Fix implementiert
- MVP-Smoke weiterhin grün (GUI startet & bleibt responsiv)
- mind. ein minimaler Test ergänzt/aktualisiert (wo sinnvoll)
- Logging/Fehlerdialog/Cancellation nicht verschlechtert