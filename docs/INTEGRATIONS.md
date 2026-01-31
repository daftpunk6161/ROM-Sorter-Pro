# Integrationen (MVP)

## Rebuilder-Modus (Copy-only)

Der Rebuilder-Modus erzwingt einen nicht-destruktiven Copy-Flow:

- **Modus:** `copy`
- **Konflikte:** `skip`
- **Quelle bleibt unverändert**

Im GUI aktivieren: **Rebuilder-Modus (Copy-only, Konflikte überspringen)**. Danach wie gewohnt **Vorschau** und **Sortierung ausführen**.

## Frontend-Exporte

Die Exporte basieren auf dem aktuellen **Sortier-Plan**. Nur geplante Aktionen (ohne `skipped`/`error`) werden exportiert.

### EmulationStation (gamelist.xml)

- Datei: `gamelist.xml`
- Struktur: `<gameList>` → `<game>`
- Felder:
  - `path`: relativ zur Zielstruktur (wenn möglich), sonst absolut
  - `name`: Dateiname ohne Extension
  - `platform`: erkannte Konsole (Fallback: `Unknown`)
  - `region` (optional)
  - `lang` (optional, kommagetrennt)

Beispiel:
```xml
<?xml version='1.0' encoding='utf-8'?>
<gameList>
  <game>
    <path>./NES/Super Mario Bros.nes</path>
    <name>Super Mario Bros</name>
    <platform>NES</platform>
  </game>
</gameList>
```

### LaunchBox (CSV)

- Datei: `launchbox_export.csv`
- Spalten:
  - `Title`
  - `ApplicationPath`
  - `Platform`
  - `Region` (optional)
  - `Language` (optional)

Beispiel:
```csv
Title,ApplicationPath,Platform,Region,Language
Super Mario Bros,C:\ROMs\NES\Super Mario Bros.nes,NES,USA,EN

### RetroArch (Playlist .lpl)

- Datei: `roms.lpl`
- JSON-Format mit `items` (Pfad, Label, Core-Infos)

Beispiel (gekürzt):
```json
{
  "version": "1.5",
  "default_core_path": "DETECT",
  "default_core_name": "DETECT",
  "label": "ROMs",
  "items": [
    {
      "path": "C:/ROMs/NES/Super Mario Bros.nes",
      "label": "Super Mario Bros",
      "core_path": "DETECT",
      "core_name": "DETECT",
      "crc32": "00000000",
      "db_name": ""
    }
  ]
}
```

## Import

### LaunchBox (CSV → Overrides)

- CLI: `python start_rom_sorter.py --import-launchbox <datei.csv>`
- Liest `ApplicationPath` + `Platform` und schreibt Overrides.
```

## Hinweise

- Exportfunktionen laufen asynchron, die GUI bleibt responsiv.
- Für genaue Pfadstrukturen bitte zuerst eine **Vorschau** erzeugen.
