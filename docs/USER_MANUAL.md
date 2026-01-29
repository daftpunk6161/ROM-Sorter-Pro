# ROM-Sorter-Pro – Benutzerhandbuch

> **Zielgruppe:** Endanwender
> **GUI-Start:** `python start_rom_sorter.py --gui`

---

## 1. Überblick
ROM-Sorter-Pro sortiert ROM-Sammlungen in strukturierte Zielordner. Der typische Ablauf:

1. **Quelle wählen**
2. **Ziel wählen**
3. **Scan** (Analyse)
4. **Preview (Dry‑run)**
5. **Execute (Sortierung)**

Die GUI bietet Filter, Presets und Reports. Qt ist bevorzugt, Tk ist Fallback.

---

## 2. Installation (Kurz)

```bash
pip install -r requirements-gui.txt
python start_rom_sorter.py --gui
```

Optional:
- Qt-Backend erzwingen: `--backend qt` oder `ROM_SORTER_GUI_BACKEND=qt`
- Tk-Backend erzwingen: `--backend tk` oder `ROM_SORTER_GUI_BACKEND=tk`

---

## 3. Home-Tab
- **Schnellstart** (Quelle/Ziel/Zum Sortieren)
- **Zuletzt verwendet** zeigt letzte Pfade
- **Favoriten**: häufig genutzte Quelle/Ziel‑Kombinationen speichern
- **Status** zeigt aktuelle Quelle/Ziel/DAT-Status

---

## 4. Sortieren (Hauptworkflow)

### 4.1 Pfade
- **Quelle**: Ordner mit unsortierten ROMs
- **Ziel**: Ordner für die sortierte Library

### 4.2 Aktionen
- **Scan**: Ermittelt ROMs und Metadaten
- **Preview (Dry‑run)**: Erzeugt Sortierplan ohne Schreibzugriffe
- **Execute**: Führt den Sortierplan aus

### 4.3 Presets
- Speichere und lade Filter-/Sortieroptionen

### 4.4 Filter (Sidebar rechts)
- Sprache, Version, Region
- Konsole/System
- Erweiterungen (`.iso,.chd,.zip`)
- Größenfilter (MB)
- Dedupe / Unknown ausblenden

### 4.5 Ergebnisliste
- Tabelle zeigt geplante Ziele/Status
- **Details** erscheinen bei Auswahl

---

## 5. Konvertieren (inkl. IGIR)

### 5.1 Konvertierungen
- **Konvertierungen prüfen** (Audit)
- **Konvertierungen ausführen**

### 5.2 IGIR Integration
- **Plan erstellen** / **Ausführen**
- **Copy‑first** (Staging)
- **Statuszeile** zeigt Probe-Status und Version

---

## 6. Einstellungen

### 6.1 Allgemein
- Theme, Fenstergröße merken, Drag & Drop

### 6.2 Sortierung
- Standardmodus, Konfliktstrategie
- Konsolen-/Regionsordner, Struktur beibehalten

### 6.3 DAT-Index
- DAT-Ordner hinzufügen, Index bauen, Cache löschen

### 6.4 Datenbank
- DB-Manager öffnen

### 6.5 Erweitert
- Review Gate (Bestätigung vor Execute)
- External Tools aktivieren
- Mapping Overrides öffnen

---

## 7. Reports
- Bibliothek-Report (Übersicht, Top Systeme/Regionen)
- Export (Scan/Plan/Audit als CSV/JSON)
- Frontend-Export (EmulationStation/LaunchBox)

---

## 8. Cancel / Sicherheit
- **Cancel** stoppt Jobs sicher
- **Review Gate** schützt vor unsicheren Aktionen
- Pfadvalidierung verhindert Traversal

---

## 9. Tastenkürzel
- **Ctrl+S**: Scan starten
- **Ctrl+P**: Preview (Dry‑run)
- **Ctrl+E**: Execute Sort
- **Ctrl+Return** (Qt): Quick Execute/Preview

## 9.1 Drag & Drop (Mehrfach)
- Mehrere Ordner/Dateien werden auf den **gemeinsamen Stammordner** reduziert.
- Ideal, um schnell mehrere Unterordner als Quelle zu wählen.

---
## 10. Troubleshooting
- Siehe [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Logs helfen bei Fehlersuche

---

## 11. FAQ (Kurz)
**Q:** Dry‑run schreibt wirklich nichts?
**A:** Ja, Preview erzeugt nur einen Plan.

**Q:** Warum sind Tools deaktiviert?
**A:** „External Tools“ in Einstellungen aktivieren.

**Q:** Qt fehlt?
**A:** Tk Fallback wird genutzt, oder `pip install -r requirements-gui.txt`.
