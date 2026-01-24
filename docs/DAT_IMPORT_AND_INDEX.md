# DAT Import & SQLite Index (Portable, Incremental, TB‑Scale)

## Ziel
- deterministische Hash-Identifikation
- Portabler Index im Repo (nicht committed)
- Inkrementeller Import
- WAL + batch inserts

## Storage Layout (Default)
- Index: data/index/romsorter_dat_index.sqlite (gitignored)
- Lockfile: data/index/romsorter_dat_index.lock (gitignored)
- Logs: data/logs/
- Cache: data/cache/
- Reports: data/reports/igir/

## DAT Quellen
- Konfiguriert in src/config.json
  - config.dats.import_paths[] (z. B. D:\DATs\**\*.dat)
- DATs liegen **nicht** im Repo
- GUI: "DAT Quellen…" verwaltet Import-Pfade (Add/Remove) und zeigt Integritäts-Check.
- Integritäts-Check zeigt: vorhandene/fehlende Pfade + DAT/XML/ZIP Counts.

## Index Schema (Minimum)
**rom_hashes**
- dat_id
- platform_id
- rom_name
- set_name
- crc32
- sha1
- size_bytes

**dat_files**
- dat_id
- source_path (UNIQUE)
- mtime
- size_bytes
- content_hash (optional)
- active

**Indexes**
- UNIQUE(sha1) WHERE sha1 IS NOT NULL
- INDEX(crc32, size_bytes)
- INDEX(dat_id)

## Inkrementelle Ingest-Regeln
- DAT File unverändert → Skip
- DAT File geändert → delete/replace rows für dat_id
- DAT File entfernt → deactivate dat_id + remove hashes (hard cleanup)

## Coverage Report (Analytics)
- Active/Inactive DAT Files
- ROM Hashes (gesamt)
- Game Names (gesamt)
- Plattform-Counts (ROMs/Games)

Coverage wird aus dem SQLite Index berechnet und kann im GUI als Statistik angezeigt werden.

## SQLite Performance
- PRAGMA journal_mode=WAL
- PRAGMA synchronous=NORMAL
- PRAGMA temp_store=MEMORY
- Batch inserts 10k–100k
- Prepared statements

## Lockfile
- JSON mit pid, process_start_time_utc, created_at_utc, hostname, user, index_path
- Atomic create
- Stale detection via PID + process start time
- Immer release in finally

## Ist-Zustand (MVP)
- SQLite Index aktiv (data/index/romsorter_dat_index.sqlite)
- Inkrementeller Import inkl. Remove/Deactivate
- Lockfile für parallele Index-Jobs
- Coverage-Report im UI verfügbar
