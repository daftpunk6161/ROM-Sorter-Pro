# ROM-Sorter-Pro – MVP‑Dokumentation

Diese Dokumentation beschreibt den aktuellen MVP‑Stand des GUI‑Flows.

## 1) Start & Backend

- Start: `python start_rom_sorter.py --gui`
- GUI‑Smoke (ohne UI‑Start): `python start_rom_sorter.py --gui-smoke`
- Backendwahl:
  - `--backend qt` oder `--backend tk`
  - Kurzformen: `--qt` / `--tk`
  - Env‑Override: `ROM_SORTER_GUI_BACKEND=qt|tk`
- Fallback: Wenn Qt nicht verfügbar ist, wird automatisch Tk verwendet.

## 2) GUI‑Flow (Ende‑zu‑Ende)

1. **Source** (ROM‑Ordner) wählen
2. **Destination** (Ziel) wählen
3. **Scan**
4. **Preview Sort (Dry‑run)**
5. **Execute Sort**

## 3) Sort‑Optionen

- **Action**: `copy` (default, nicht‑destruktiv) oder `move`
- **On conflict**: `rename` (default), `skip`, `overwrite`

Zusätzliche Sort‑Logik (Config‑gesteuert):

- `features.sorting.console_sorting_enabled`
- `features.sorting.create_console_folders`
- `features.sorting.region_based_sorting`
- `features.sorting.preserve_folder_structure`

## 4) Filter (MVP)

- Sprache
- Version
- Region
- Extension‑Filter (z. B. `.iso,.chd,.zip` oder `iso,chd`)
- Min/Max‑Größe (MB)
- **Avoid duplicates** (Bevorzugt EU → US)
- **Hide Unknown / Low‑Confidence**

## 5) Ergebnisliste (Tabelle)

Die Tabelle enthält:
- InputPath
- Name
- DetectedConsole/Type
- Confidence
- Signals
- Candidates
- Reason
- PlannedTargetPath
- Action
- Status/Error

Zusatzaktionen:
- **ⓘ Details** öffnet die komplette Detailansicht (Tk).
- **Warum unbekannt?** ist nur für Unknown/Low‑Confidence aktiv.

## 6) DAT‑Matching

- Unterstützte DAT‑Formate: `.xml` (Logiqx), `.dat` (ClrMamePro), `.zip` (mit `.dat/.xml` im ZIP)
- Index: `data/index/romsorter_dat_index.sqlite`
- Auto‑Load per Settings‑Toggle (GUI)

Konfiguration (Auszug) in `src/config.json`:

```
"dats": {
  "enabled": true,
  "auto_load": false,
  "import_paths": ["D:/DATs"],
  "index_path": "data/index/romsorter_dat_index.sqlite"
}
```

## 6.1) Detection‑Policy (Strict + Ambiguität)

Die Erkennung ist **strict**: ohne exakte DAT‑Treffer wird nicht geraten.

Regeln:
- **Exact DAT/Hashes** → `confidence=1000`, `is_exact=true`, sofort akzeptiert.
- **Extension‑Unique** → nur akzeptiert, wenn die Kandidatenlage eindeutig ist.
- **Ambiguität** (Top‑Score zu nah an Runner‑Up) → `Unknown`.
- **Konfliktgruppe** (Top‑Kandidaten teilen Konfliktgruppe) → `Unknown`.
- **Widerspruch** (Erkennung ≠ bestes Kandidatensignal) → `Unknown`.

Policy‑Parameter in `platform_catalog.yaml`/`platform_catalog.json`:

```
"policy": {
  "min_score_delta": 1.0,
  "min_top_score": 2.0,
  "contradiction_min_score": 2.0
}
```

Hinweis: Bei zu aggressiven Regeln steigen Unknown‑Fälle, dafür weniger False Positives.

## 6.2) Platform‑Catalog (YAML)

- Primär: `src/platforms/platform_catalog.yaml`
- Fallback: `src/config/platform_catalog.json`
- Optionales Override: `ROM_SORTER_PLATFORM_CATALOG` (Dateipfad)
- Optionales Override via Config: `platform_catalog_path` in `src/config.json`

## 6.3) Detection‑Signals (Kurzreferenz)

Die Spalte **Signals** in der Ergebnisliste enthält maschinenlesbare Hinweise, die die Erkennung beeinflussen.

Typische Signals:
- `dat_exact`: Exakter DAT‑Treffer (Hash/Merkmale). Setzt `is_exact=true` und `confidence=1000`.
- `extension_unique`: Eindeutige Zuordnung aus Dateiendung in eindeutiger Kandidatenlage.
- `ambiguous`: Mehrere Kandidaten sind nahezu gleich gut → Ergebnis wird `Unknown`.
- `conflict_group`: Top‑Kandidaten teilen eine Konfliktgruppe → Ergebnis wird `Unknown`.
- `contradiction`: Detektion widerspricht Top‑Kandidatensignal → Ergebnis wird `Unknown`.

Die Spalte **Candidates** zeigt die Kandidatenliste mit Scores/Quellen, die zur Entscheidung geführt haben.

## 7) Normalization (InputKinds + Validatoren)

Neue Engine: `src/core/normalization.py`

- Klassifizierung: RawRom, ArchiveSet, DiscImage, DiscTrackSet, GameFolderSet
- Validierung:
  - `.cue`/`.gdi` prüfen fehlende Track‑Dateien
  - Folder‑Sets prüfen `required_manifests` aus `platform_formats.yaml`

Konfiguration:
- `src/platforms/platform_formats.yaml`
- `src/conversion/converters.yaml`

## 7.1) Converters (Schema)

Schemafelder u. a.:
- `exe_path`, `enabled`, `platform_ids`, `extensions`, `input_kinds`, `output_extension`, `args_template`

Dry‑Run führt keine Tools aus und benötigt keine Executables.

Fallback:
- Wenn `src/conversion/converters.yaml` leer ist, werden Conversion‑Regeln aus `src/config.json` (features.sorting.conversion) geladen.

## 7.2) Format‑Matrix (InputKinds → typische Formate)

| InputKind | Beschreibung | Typische Formate |
| --- | --- | --- |
| RawRom | Einzeldatei | `.nes`, `.sfc`, `.smc`, `.gb`, `.gba` |
| ArchiveSet | Komprimiertes Set | `.zip`, `.7z` |
| DiscImage | Einzel‑Disc‑Image | `.iso`, `.chd`, `.cso` |
| DiscTrackSet | Track‑Set mit Manifest | `.cue` + Tracks, `.gdi` + Tracks |
| GameFolderSet | Ordner‑Set | Plattform‑spezifische Ordner (z. B. Wii U, PS3) |

Die endgültige Zuordnung wird in `src/platforms/platform_formats.yaml` definiert.

## 8) External Tools (WUD)

- Unterstützt: `wud2app`, `wudcompress`
- Konfiguration in `src/config.json` → `external_tools`
- Probe‑Status wird im UI angezeigt

## 8.1) Safety‑Regeln (Plan/Execute)

- **Dry‑Run** schreibt keine Dateien und startet keine externen Tools.
- **Path‑Security**: Zielpfade werden validiert (Traversal‑Schutz, keine unerlaubten Pfade).
- **Collisions**: Konflikte werden gemäß `on_conflict` behandelt (`rename`, `skip`, `overwrite`).

Bei Verstößen wird die Aktion übersprungen und der Fehler im Report protokolliert.

## 9) Tests (MVP)

Empfohlene Tests:
- `dev/tests/test_mvp_backend_selection.py`
- `dev/tests/test_mvp_controller_planning.py`
- `dev/tests/test_mvp_conversion_runner.py`
- `dev/tests/test_mvp_format_validation.py`
- `dev/tests/test_mvp_execute_cancel.py`
- `dev/tests/test_mvp_execute_cancel_mid_copy.py`
- `dev/tests/test_mvp_security_paths.py`
- `dev/tests/test_mvp_lang_version_parsing.py`
- `dev/tests/test_mvp_igir_gates.py`
- `dev/tests/test_mvp_identify_rules.py`
- `dev/tests/test_mvp_dat_sources.py`
- `dev/tests/test_mvp_dat_index.py`
- `dev/tests/test_mvp_frontend_exports.py`
- `dev/tests/test_mvp_logging_json.py`
- `dev/tests/test_mvp_hash_cache.py`
- `dev/tests/test_mvp_plan_cancel.py`
- `dev/tests/test_mvp_rebuilder_mode.py`
- `dev/tests/test_mvp_golden_fixtures.py`
- `dev/tests/test_mvp_start_version.py`
- `dev/tests/test_mvp_gui_smoke.py`
- `dev/tests/test_mvp_execute_dry_run_no_tools.py`

## 9.1) GUI‑Threading (Kurzüberblick)

- Qt: `QThread` + Worker‑Objekte (Scan/Plan/Execute/IGIR/Export)
- Tk: `threading.Thread` + Queue + `after()` Polling
- Cancel: `CancelToken` in langen Operationen
- Keine UI‑Blocker: Export‑Tasks laufen im Worker
- Konfig‑I/O und DB‑Dialoge bleiben kurz; bei langen Aktionen künftig auslagern.
- DB‑Manager: Backup/Migration/Status laufen asynchron.

## 10) Archiv

Legacy‑Code, alte Tools und Runtime‑Artefakte liegen in `_archive/`.

## 12) Datenbank (Entrypoints)

Siehe [DB_ENTRYPOINTS.md](DB_ENTRYPOINTS.md) für die empfohlenen DB‑Routen.

## 11) Troubleshooting (Kurz)

- **GUI startet nicht**: Qt fehlt → `pip install -r requirements-gui.txt` oder `--backend tk`.
- **Keine Treffer bei Scan**: DAT‑Matching prüfen, `dat_paths` konfigurieren, Auto‑Load aktivieren.
- **Viele Unknowns**: Detection‑Policy ggf. lockern (Catalog‑Policy‑Werte).
- **External‑Tool Fehler**: Pfade in `src/config.json` → `external_tools` prüfen.
