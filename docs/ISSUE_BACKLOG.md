# Issue Backlog (Epics)

## Epics (Proposed)
- **E1** DAT Import + Incremental SQLite Index (CRC32+SHA1, WAL, batch inserts, TB-scale)
  - Milestone: Detection-Accuracy
  - Priority: P0
- **E2** Lockfile (PID+starttime) + robust recovery + tests
  - Milestone: Detection-Accuracy
  - Priority: P0
- **E3** Archive-aware hashing (ZIP entries) + mixed content handling + security
  - Milestone: Detection-Accuracy
  - Priority: P0
- **E4** Deterministic identification pipeline (DAT→Signatures→Heuristic) + UNKNOWN rules + tests
  - Milestone: Detection-Accuracy
  - Priority: P0
  - Status: in Arbeit (DAT/Unknown-Regeln + Tests ergänzt)
- **E5** Normalization engine (kinds, manifests, preferred outputs per platform) + tests
  - Milestone: Normalization-v1
  - Priority: P1
- **E6** IGIR integration (plan + safety diff + export + execute button gates) + tests
  - Milestone: Detection-Accuracy
  - Priority: P1
  - Status: erledigt (Gates, UI-Bestätigung, Tests)
- **E7** GUI worker model (progress/cancel/timeout, no blocking) + smoke tests
  - Milestone: MVP-GUI
  - Priority: P1
  - Status: teilweise erledigt (Scan/Plan/Execute/Export asynchron, Doku ergänzt)
- **E8** Tooling/CI + baseline docs + repo cleanup
  - Milestone: CI-Hardening
  - Priority: P2

## Umsetzung
- Scripts: scripts/issues/gh_setup.ps1 + scripts/issues/gh_create_epics.ps1
- Epics manifest: issues/epics.json
