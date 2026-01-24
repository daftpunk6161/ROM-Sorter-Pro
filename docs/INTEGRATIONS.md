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

Beispiel:
```csv
Title,ApplicationPath,Platform
Super Mario Bros,C:\ROMs\NES\Super Mario Bros.nes,NES
```

## Hinweise

- Exportfunktionen laufen asynchron, die GUI bleibt responsiv.
- Für genaue Pfadstrukturen bitte zuerst eine **Vorschau** erzeugen.
