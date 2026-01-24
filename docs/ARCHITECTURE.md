# Architektur (aktuell & Zielbild)

## Aktueller Stand (MVP)

**Entry**: [start_rom_sorter.py](../start_rom_sorter.py)

**Flow (vereinfacht)**
1. Start-Skript lädt Konfiguration und wählt GUI-Backend (Qt bevorzugt, Tk Fallback).
2. UI-Schicht in [src/ui](../src/ui/) startet Qt oder Tk.
3. UI ruft Controller-Funktionen in [src/app/controller.py](../src/app/controller.py) auf.
4. Controller orchestriert Scanning/Identifikation/Sort-Plan über [src/core](../src/core/), [src/scanning](../src/scanning/), [src/detectors](../src/detectors/), [src/security](../src/security/).
5. Config/Schema in [src/config](../src/config/), Plattformdaten in [src/platforms](../src/platforms/).

## Zielbild (Boundary-Regeln)

**Schichten**
- **UI**: Qt/Tk Views + Adapter. Keine Business-Logik.
- **App/Controller**: Orchestrierung, Jobs, Fortschritt, Cancel.
- **Core**: Identifikation, Normalisierung, Plan/Execute.
- **Security**: Pfadvalidierung/Traversal-Schutz für alle IO.
- **Config & Data**: YAML/JSON Schemas, Kataloge, Tools.

**Boundary-Regeln**
- UI importiert **nur** aus `src.app.api` (stabile API).
- Controller kapselt Long-Running Tasks und Error-Handling.
- Core bleibt UI-agnostisch.
- Security-Gates erzwingen Dry-run-Invariant und Pfadvalidierung vor allen Writes.
- Execute erfordert eine vorherige Plan-Vorschau als Safety-Diff.

## Qt/Tk Adapter-Strategie

- Gemeinsames UI-Interface (Commands/Events/Models) in [src/ui/compat.py](../src/ui/compat.py).
- Qt-Implementierung primär (Signals/Slots, QThread/ThreadPool).
- Tk-Implementierung minimal (threading + queue + after()).
- Gleiche Controller-Aufrufe, keine Logik-Duplikation.

## Threading & Cancel

- Alle IO-lastigen Jobs laufen **nicht** auf dem UI-Thread.
- Cancel via thread-safe Token/Event.
- Exceptions werden im UI angezeigt und im Log erfasst.
