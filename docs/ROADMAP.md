# ROM-Sorter-Pro – Roadmap

## Vision
ROM-Sorter-Pro liefert deterministische, sichere und transparente ROM-Identifikation und -Organisation.
DAT/Hash-first, keine False Positives, und ein GUI-first Workflow (Qt primär, Tk Fallback).

## Prinzipien
- **DAT/Hash-first**: Keine heuristische Rate ohne harte Signale.
- **UNKNOWN > falsch**: Sicherheit vor Bequemlichkeit.
- **Dry-run ist heilig**: Keine Writes, keine externen Tools im Dry-run.
- **Transparenz**: Jede Entscheidung ist nachvollziehbar (Signale, Kandidaten, Gründe).
- **Sicherheitsgates**: Pfadvalidierung, Traversal-Schutz, bestätigte Aktionen.
- **Qt-first UI**: Tk bleibt minimal kompatibel, keine Logik-Duplikation.

## Meilensteine (geplant)

| Milestone | Zeitfenster | Fokus | Umfang (Beispiele) |
| --- | --- | --- | --- |
| Baseline-Quality | 2026 Q1 | Stabilität, Sicherheit, Governance | Crash-freier Start, Release-Prozess, Security-Gates, Regression-Suite |
| Detection-Accuracy | 2026 Q1–Q2 | DAT/Hash-Ökosystem | DAT-Manager, Integritätschecks, Unknown-Reduktion, Analytics |
| IGIR-Power-Flow | 2026 Q2 | Power-User Flows | Plan/Diff/Execute, Profile, Export, Rollback-Strategie |
| Normalization-v1 | 2026 Q2 | Formate & Konvertierung | Plattform-Registry, Track-/Folder-Validatoren, Zielprofile |
| GUI-JobSystem | 2026 Q2–Q3 | Job-Queue & UX | Queue, Pause/Resume/Cancel, Log-Filter |
| Performance-Scale | 2026 Q3 | Skalierung | Hash-Caching, IO-Throttling, SQLite-Tuning |
| Integrations | 2026 Q3–Q4 | Exporte & Tools | Frontend-Exporte, Rebuilder-Mode, optionale Plugins |

## Abhängigkeiten
- **Qt/PySide6** für primäre UX; Tk nur als Fallback.
- **SQLite** Indexing für DAT/Hash-Daten.
- **External Tools** (z. B. IGIR) nur mit expliziter Benutzeraktion.

## Risiken
- Über-aggressive Erkennung → UNKNOWN-Rate steigt (akzeptiert, aber UX-Impact).
- Performance-Bottlenecks bei sehr großen Bibliotheken.
- Externe Tool-Integration (IGIR) muss strikt gated sein.
- Plattformdaten (Catalog/Formats) erfordern Pflege und Validierung.
