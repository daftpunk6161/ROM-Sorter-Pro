# Datenbank‑Entrypoints (MVP)

## Empfohlener Entry‑Point

Verwende für DB‑Operationen im MVP ausschließlich:
- `src/app/db_controller.py`
  - `init_db()`
  - `migrate_db()`
  - `backup_db()`
  - `scan_roms()`
  - `import_dat()`

## Interne/Legacy‑Routen

Diese sollten nicht direkt von der UI aufgerufen werden:
- `scripts/update_rom_database.py` (low‑level Implementierung)
- `src/database/database_gui.py` (UI‑Dialog, nur GUI‑Schicht)
- `src/database/connection_pool.py` (Connection‑Helpers)

## Hinweis

Die UI nutzt weiterhin die DB‑Dialoge, aber jede langfristige Integration sollte über `src/app/db_controller.py` laufen, um konsistente Semantik zu gewährleisten.
