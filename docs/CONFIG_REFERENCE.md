# Config Reference

Primäre Konfiguration: [src/config.json](../src/config.json)

## Allgemein
- `_metadata.version` – Produktversion (muss mit Release-Version konsistent sein).
- `platform_catalog_path` – optionaler Override für Plattformkatalog.

## DAT / Hash
- `dat_matching.enabled` – DAT Matching aktivieren.
- `dat_matching.auto_load` – Auto-Load der DATs.
- `dat_matching.dat_paths` – Suchpfade für DATs.
- `dats.import_paths` – Import-Quellen für DATs.
- `dats.index_path` – SQLite Index Pfad.
- `dats.lock_path` – Lockfile für Indexing.

## GUI
- `gui_settings.theme` – UI Theme.
- `gui_settings.drag_drop_enabled` – Drag&Drop.
- `gui_settings.remember_window_size` – Fenstergröße merken.
- `gui_settings.window_width` / `window_height` – Startgröße.
- `ui.language` – UI‑Sprache (`de_DE`/`en_US`).

## Sorting / Execution
- `features.sorting.console_sorting_enabled`
- `features.sorting.create_console_folders`
- `features.sorting.region_based_sorting`
- `features.sorting.preserve_folder_structure`
- `features.sorting.rename_template`
- `features.sorting.confidence_threshold`

## Backup / Rollback / Resume
- `features.backup.enabled` – Report‑Backup aktivieren.
- `features.backup.local_dir` – Lokaler Backup‑Ordner.
- `features.backup.onedrive_enabled` – OneDrive‑Ziel aktivieren.
- `features.backup.onedrive_dir` – Optionaler OneDrive‑Pfad (auto‑detect sonst).
- `features.rollback.enabled` – Rollback‑Manifest erzeugen (nur Move).
- `features.rollback.manifest_path` – Pfad zum Manifest.
- `features.progress_persistence.enabled` – Resume‑Checkpointing aktivieren.
- `features.progress_persistence.save_interval_sec` – Intervall in Sekunden.
- `features.progress_persistence.scan_resume_path` – Scan‑Resume‑Pfad.
- `features.progress_persistence.sort_resume_path` – Sort‑Resume‑Pfad.

## Plugins
- `features.plugins.enabled` – Plugin‑System aktivieren.
- `features.plugins.paths` – Liste mit Plugin‑Ordnern.

### Conversion Tools
- `features.sorting.conversion.enabled`
- `features.sorting.conversion.require_dat_match`
- `features.sorting.conversion.fallback_on_missing_tool`
- `features.sorting.conversion.tools` – Tool-Pfade (chdman, 7z, maxcso, etc.)
- `features.sorting.conversion.rules` – Regeln (name, systems, extensions, to_extension, tool, args)

## Performance
- `performance.caching.*` – Cache-Größen & TTLs.
- `performance.processing.*` – Batch/Chunk/Workers/IO.
- `performance.optimization.*` – Pattern/Hash/Progress.

## Priorisierung (Dedupe/Selection)
- `prioritization.region_order`
- `prioritization.language_order`
- `prioritization.region_priorities`
- `prioritization.language_priorities`
- `prioritization.quality_indicators.*`

## Externe Kataloge / Schemas
- Plattformkatalog: [src/platforms/platform_catalog.yaml](../src/platforms/platform_catalog.yaml)
- Plattform-Formate: [src/platforms/platform_formats.yaml](../src/platforms/platform_formats.yaml)
- Converter-Regeln: [src/conversion/converters.yaml](../src/conversion/converters.yaml)
- DAT-Quellen: [src/dats/dat_sources.yaml](../src/dats/dat_sources.yaml)
- IGIR-Config: [src/tools/igir.yaml](../src/tools/igir.yaml)

## Environment Variablen
- `ROM_SORTER_USE_PYDANTIC=1` – aktiviert optionale Pydantic-Config-Validierung beim Laden.
- `ROM_SORTER_PROFILE=1` – aktiviert Scan-Profiling.
- `ROM_SORTER_PROFILE_PATH=/path/scan.prof` – Zielpfad für das Profiling-Output.
- `ROM_SORTER_PLATFORM_FORMATS=/path/platform_formats.yaml` – Override für Plattform-Formate.
- `ROM_SORTER_CONVERTERS=/path/converters.yaml` – Override für Converter-Regeln.
- `ROM_SORTER_PLUGIN_PATHS=/path/plugins1;/path/plugins2` – Plugin‑Suchpfade (Windows‑Separator `;`).

### IGIR (Copy-first)
`igir.yaml` unterstützt `copy_first` für Copy-first-Staging vor dem finalen Output.

### Plattform-Formate (preferred outputs)
`platform_formats.yaml` kann pro Plattform `preferred_outputs` definieren. 
Diese Liste steuert, welcher Converter bevorzugt gewählt wird, wenn mehrere Ausgänge möglich sind.
