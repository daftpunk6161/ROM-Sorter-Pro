# Refactor Plan (Phased, GUI‑First)

## Phase 0 — Audit + Docs (jetzt)
- Dokumente in docs/* erstellen/aktualisieren
- Epics/Issues vorbereiten

## Phase 1 — Controller Boundary
- UI spricht nur über Controller API
- Ziel-API:
  - run_scan()
  - identify()
  - plan_normalization()
  - execute_normalization()
  - plan_sort()
  - execute_sort()

## Phase 2 — DAT/Hash-First Identification
- Strict Order: DAT -> Signatures -> Heuristic
- Unknown-Regeln zentralisieren
- Signals/Candidates vereinheitlichen

## Phase 3 — SQLite DAT Index
- WAL + batch inserts
- Incremental ingest
- Lockfile mit PID+start_time
- Portables data/index Layout

## Phase 4 — Archive Awareness
- ZIP Entry Hashing
- Mixed content → Unknown
- 7z/rar optional

## Phase 5 — Normalization Engine
- Plattform-Formate in YAML + Schema
- preferred_outputs + normalize_to_single_file
- Converter Registry + Runner

## Phase 6 — IGIR Integration
- Plan → Safety Diff → Execute Gate
- Export CSV/JSON
- Cancel/timeout

## Phase 7 — UI Enhancements
- Buttons für Index/IGIR
- „Why Unknown?“ View
- Progress/Cancel stabil

## Phase 8 — CI/Repo Hygiene
- Coverage Gate
- .gitignore Daten-Dirs
- Legacy-Abbau nach Stabilisierung

## Nicht‑Ziele (kurzfristig)
- ML/AI Erkennung
- Web UI
- Große UI-Polish Refactors
