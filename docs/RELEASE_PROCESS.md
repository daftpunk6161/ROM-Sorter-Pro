# Release Process

## Versionierung
- Semantic Versioning (MAJOR.MINOR.PATCH).
- Version konsistent halten in:
  - [src/config.json](../src/config.json) (`_metadata.version`)
  - [start_rom_sorter.py](../start_rom_sorter.py) (Ausgabe bei `--version`)

## Checkliste
1. Changelog aktualisieren: [CHANGELOG.md](../CHANGELOG.md) → Abschnitt **Unreleased** prüfen.
2. Version bumpen (siehe oben).
3. CI/Tests lokal ausführen (Smoke + Lint).
4. Release-Tag erstellen und pushen.

## Minimal-Tests (Release Gate)
- `pytest` MVP Smoke (siehe .vscode Task: `pytest mvp smoke`).
- `ruff check .`

## Tagging
- Tag-Format: `vX.Y.Z`.
- Release-Notes aus `CHANGELOG.md` übernehmen.

## CI Anforderungen
- Tests grün (Smoke + kritische Suites).
- Keine neuen Lint-Errors.
- GUI-Start: Qt oder Tk fallback (Smoke).
