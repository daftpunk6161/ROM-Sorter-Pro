# 🎮 ROM Sorter Pro – GUI Refactoring Analyse

> **Status:** Vorschlag / Nicht umgesetzt  
> **Erstellt:** 29. Januar 2026  
> **Ziel:** Schlankes, übersichtliches, selbstsprechendes GUI

---

## 📊 Ist-Zustand (Kritische Betrachtung)

### Aktuelle Probleme

| Problem | Schweregrad | Bereich |
|---------|-------------|---------|
| **~5.000 Zeilen** in einer Datei (`qt_app_impl.py`) | 🔴 Kritisch | Architektur |
| Header überladen (15+ Widgets) | 🔴 Kritisch | UX |
| Doppelte Pfad-Eingaben (Haupt-Tab, Konvertierungen, IGIR) | 🟠 Hoch | UX |
| Vermischung von allgemeinen Einstellungen & Tab-spezifischen Funktionen | 🟠 Hoch | UX |
| Filter/Presets im linken Panel versteckt | 🟡 Mittel | UX |
| Status-Pills ohne klare Bedeutung | 🟡 Mittel | UX |
| Stepper zeigt keinen echten Fortschritt | 🟡 Mittel | UX |

### Aktuelle Tab-Struktur (6 Tabs)

```
🏠 Dashboard │ 🗂️ Sortierung │ 🧰 Konvertierungen │ 🧪 IGIR │ 🗃️ Datenbank │ ⚙️ Einstellungen
```

**Probleme:**
- IGIR und Konvertierungen sind thematisch verwandt, aber getrennt
- Datenbank/DAT-Index ist Konfiguration, kein Workflow
- Pfad-Eingaben existieren dreifach (Sortierung, Konvertierungen, IGIR)

---

## 🏗️ Vorgeschlagene Neue Struktur

### Neue Tab-Aufteilung (5 Tabs)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🏠 Home  │  🔀 Sortieren  │  🧰 Konvertieren  │  ⚙️ Einstellungen  │  📊 Reports │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📑 Tab-Details

### Tab 1: 🏠 Home (Dashboard + Quick-Start)

**Zweck:** Willkommen, Schnellstart-Wizard, letzte Jobs

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ 🏠 Home                                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ Willkommen ───────────────────────────────────────────────────────┐ │
│  │  ROM Sorter Pro v2.x                                               │ │
│  │  Sortiere deine ROM-Sammlung in wenigen Schritten                  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ Schnellstart ─────────────────────────────────────────────────────┐ │
│  │  1️⃣ Quelle wählen  →  2️⃣ Ziel wählen  →  3️⃣ Scannen  →  4️⃣ Los!  │ │
│  │                                                                    │ │
│  │  [📂 Quelle wählen...]  [📂 Ziel wählen...]  [▶ Zum Sortieren]    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ Zuletzt verwendet ────────────────────────────────────────────────┐ │
│  │  📁 C:\ROMs\Unsortiert        →  📁 D:\Spiele\Sortiert            │ │
│  │  📁 E:\Backup\ROMs            →  📁 F:\Library\Games              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ Status ───────────────────────────────────────────────────────────┐ │
│  │  📊 Letzter Scan: 1.234 ROMs  │  ✅ DAT-Index: 15.234 Einträge    │ │
│  │  🎮 Erkannte Systeme: 12      │  ⏱️ Letzte Sortierung: vor 2h     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Inhalt:**
- Hero-Card: "Wähle Quelle → Wähle Ziel → Los!"
- Zuletzt verwendete Pfade (Quick-Access Chips)
- Status-Zusammenfassung (Scan-Ergebnis, letzte Sortierung)
- DAT-Index-Status (kompakt: "✅ 15.234 ROMs indiziert")

---

### Tab 2: 🔀 Sortieren (Hauptworkflow)

**Zweck:** Der komplette Scan→Plan→Execute Flow

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ 🔀 Sortieren                                                             │
├─────────────────────────────────────────────────────────────────────────┤
│ 📂 Quelle                              📂 Ziel                          │
│ [C:\ROMs\Unsortiert            ][📁]   [D:\Sortiert              ][📁]  │
│                                                                         │
│ Preset: [Standard ▼]  Modus: [Copy ▼]  Konflikt: [Umbenennen ▼]        │
├───────────────────────────────────────────────────────────────┬─────────┤
│                                                               │🔍Filter │
│  ┌─────────────────────────────────────────────────────────┐  ├─────────┤
│  │ Datei            │ System │ Aktion │ Ziel     │ Status  │  │Sprache: │
│  ├──────────────────┼────────┼────────┼──────────┼─────────┤  │[All]    │
│  │ Super Mario.nes  │ NES    │ copy   │ NES/     │ ✅      │  │[DE] [EN]│
│  │ Zelda.smc        │ SNES   │ copy   │ SNES/    │ ⏳      │  │         │
│  │ Unknown.bin      │ ???    │ skip   │ -        │ ⚠️      │  │Region:  │
│  │ Sonic.md         │ Genesis│ copy   │ Genesis/ │ ✅      │  │[All]    │
│  │ ...              │        │        │          │         │  │[EU] [US]│
│  └─────────────────────────────────────────────────────────┘  │         │
│                                                               │Version: │
│                                                               │[All ▼]  │
│                                                               │         │
│                                                               │☐ Dedupe │
│                                                               │☐ Unknown│
│                                                               │  ausbl. │
│                                                               │         │
│                                                               │[🗑Reset]│
├───────────────────────────────────────────────────────────────┴─────────┤
│ 📋 Details: Super Mario.nes                                             │
│ System: NES (Confidence: 95%) │ DAT-Match: ✅ │ Region: USA │ CRC: A1B2 │
│ Grund: Extension + Folder + DAT-Lookup                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

**Schlüsseländerungen:**
- **Pfade nur hier** (nicht dreifach!)
- **Filter als einklappbare Sidebar rechts** (nicht versteckt in Sub-Tab)
- **Details-Panel** nur bei Auswahl sichtbar
- **Tabelle nimmt maximalen Platz ein**
- **Presets:** Dropdown oben bei den Pfaden (nicht versteckt)

---

### Tab 3: 🧰 Konvertieren (inkl. IGIR)

**Zweck:** ROM-Format-Konvertierungen und IGIR-Integration

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ 🧰 Konvertieren                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ Schnellstart ─────────────────────────────────────────────────────┐ │
│  │                                                                    │ │
│  │  [▶ Konvertierungen prüfen (Audit)]  [▶ Konvertierungen ausführen] │ │
│  │                                                                    │ │
│  │  Status: Bereit │ Letzte Prüfung: 45 Kandidaten gefunden           │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ IGIR Integration ─────────────────────────────────────────────────┐ │
│  │                                                                    │ │
│  │  Status: ✅ IGIR gefunden (v2.14.3)          [🔄 Prüfen]          │ │
│  │                                                                    │ │
│  │  Template: [Vollständig sortieren     ▼]                          │ │
│  │  Profil:   [Standard                  ▼]                          │ │
│  │                                                                    │ │
│  │  [▶ IGIR Plan erstellen]  [▶ IGIR Ausführen]  [⏹ Abbrechen]       │ │
│  │                                                                    │ │
│  │  ☐ Copy-first (Staging vor Ausführung)                            │ │
│  │                                                                    │ │
│  │  Diff-Reports: [📄 CSV öffnen] [📄 JSON öffnen]                   │ │
│  │                                                                    │ │
│  │  ▼ Erweiterte Konfiguration                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐ │ │
│  │  │ IGIR Executable: [C:\Tools\igir.exe                    ][📁] │ │
│  │  │ Args Template:                                               │ │
│  │  │ ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │ │ --input {input}                                          │ │ │
│  │  │ │ --output {output_dir}                                    │ │ │
│  │  │ │ --dat-path {dat_path}                                    │ │ │
│  │  │ └──────────────────────────────────────────────────────────┘ │ │
│  │  │ [💾 Speichern]                                               │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ Externe Tools Status ─────────────────────────────────────────────┐ │
│  │                                                                    │ │
│  │  wud2app:      ✅ v1.2 (gefunden)     [🔄 Prüfen]                 │ │
│  │  wudcompress:  ✅ v2.1 (gefunden)     [🔄 Prüfen]                 │ │
│  │                                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Änderungen gegenüber Alt:**
- **IGIR ist jetzt Teil von Konvertieren** (gleiche Domäne: Format-Transformation)
- **Erweiterte Konfiguration eingeklappt** (Clean Default)
- **Keine separaten Pfad-Eingaben** (nutzt Pfade aus Sort-Tab)

---

### Tab 4: ⚙️ Einstellungen (zentrale Konfiguration)

**Zweck:** Alle Einstellungen an einem Ort

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ ⚙️ Einstellungen                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ Allgemein ────────────────────────────────────────────────────────┐ │
│  │                                                                    │ │
│  │  Theme:              [Midnight Pro          ▼]                    │ │
│  │                                                                    │ │
│  │  ☑ Drag & Drop aktivieren                                         │ │
│  │  ☑ Fenstergröße merken                                            │ │
│  │  ☐ Log standardmäßig anzeigen                                     │ │
│  │                                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ Sortierung ───────────────────────────────────────────────────────┐ │
│  │                                                                    │ │
│  │  Standard-Modus:     [Copy ▼]       Konflikt: [Umbenennen ▼]      │ │
│  │                                                                    │ │
│  │  ☑ Konsolenordner erstellen                                       │ │
│  │  ☐ Regionsordner erstellen                                        │ │
│  │  ☐ Quell-Unterordner beibehalten                                  │ │
│  │                                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ DAT-Index ────────────────────────────────────────────────────────┐ │
│  │                                                                    │ │
│  │  Status: ✅ 15.234 ROMs │ 3 Pfade konfiguriert                    │ │
│  │                                                                    │ │
│  │  [📂 DAT-Ordner hinzufügen]  [🔄 Index neu bauen]  [🗑 Cache löschen] │
│  │  [📋 DAT-Quellen verwalten...]                                    │ │
│  │                                                                    │ │
│  │  ☐ DATs beim Start automatisch laden                              │ │
│  │                                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ Datenbank ────────────────────────────────────────────────────────┐ │
│  │                                                                    │ │
│  │  Pfad: C:\ROM-Sorter-Pro\data\romsorter.db                        │ │
│  │  Status: ✅ OK │ ROMs: 5.432 │ Konsolen: 24                       │ │
│  │                                                                    │ │
│  │  [🔧 DB-Manager öffnen]  [💾 Backup]  [📂 Ordner öffnen]          │ │
│  │                                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ Erweitert ────────────────────────────────────────────────────────┐ │
│  │                                                                    │ │
│  │  ☐ Review Gate aktivieren (Bestätigung vor Execute)               │ │
│  │  ☐ External Tools aktivieren                                      │ │
│  │                                                                    │ │
│  │  [📝 Mapping Overrides öffnen]                                    │ │
│  │                                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Änderungen:**
- **DAT-Index und Datenbank** hierher verschoben (sind Konfiguration, kein Workflow)
- **Review Gate / External Tools** hier statt im Header
- **Alle Einstellungen zentral** statt über Tabs verstreut

---

### Tab 5: 📊 Reports (Export & Statistiken)

**Zweck:** Bibliotheks-Reports und Export-Funktionen

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ 📊 Reports & Export                                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─ Bibliothek-Report ────────────────────────────────────────────────┐ │
│  │                                                                    │ │
│  │  📊 Übersicht                                                      │ │
│  │  ├─ Gesamt: 1.234 ROMs                                            │ │
│  │  ├─ Erkannt: 1.180 (95.6%)                                        │ │
│  │  └─ Unbekannt: 54 (4.4%)                                          │ │
│  │                                                                    │ │
│  │  🎮 Top Systeme           🌍 Top Regionen                         │ │
│  │  ├─ NES: 245              ├─ USA: 412                             │ │
│  │  ├─ SNES: 198             ├─ Europe: 356                          │ │
│  │  ├─ Genesis: 156          ├─ Japan: 289                           │ │
│  │  └─ ...                   └─ ...                                  │ │
│  │                                                                    │ │
│  │  [🔄 Report aktualisieren]  [💾 Report speichern...]              │ │
│  │                                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ Export ───────────────────────────────────────────────────────────┐ │
│  │                                                                    │ │
│  │  Scan-Ergebnisse:                                                 │ │
│  │  [📄 CSV exportieren]  [📄 JSON exportieren]                      │ │
│  │                                                                    │ │
│  │  Sortierplan:                                                     │ │
│  │  [📄 CSV exportieren]  [📄 JSON exportieren]                      │ │
│  │                                                                    │ │
│  │  Audit-Ergebnisse:                                                │ │
│  │  [📄 CSV exportieren]  [📄 JSON exportieren]                      │ │
│  │                                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─ Frontend-Export ──────────────────────────────────────────────────┐ │
│  │                                                                    │ │
│  │  [🎮 EmulationStation Gamelist]  [🎮 LaunchBox CSV]               │ │
│  │                                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🎛️ Header-Verschlankung

### Vorher (überladen)
```
[App Title] [Stepper 1-2-3] [Scan] [Preview] [Execute] [Cancel] 
[⌘ Palette] [Log] [Review Gate ☐] [External Tools ☐] 
[Theme ▼] [Status] [Queue] [DAT] [Safety]
```

### Nachher (fokussiert)
```
┌─────────────────────────────────────────────────────────────────────────┐
│ 🎮 ROM Sorter Pro v2.x        [▶ Scan] [▶ Preview] [▶ Execute] [⏹]    │
├─────────────────────────────────────────────────────────────────────────┤
│ [════════════════░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 45% - Scanning...   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Status-Bar (unten, neu)
```
┌─────────────────────────────────────────────────────────────────────────┐
│ ✅ Bereit │ DAT: 15.234 │ Queue: 0 │ Safe Mode │         [📋 Log] [⌘] │
└─────────────────────────────────────────────────────────────────────────┘
```

**Änderungen:**
- Status-Pills → Status-Bar (unten)
- Theme-Auswahl → Einstellungen-Tab
- Review Gate / External Tools → Einstellungen-Tab
- Stepper → In Progress-Bar integriert (farblich: grün=done, blau=current, grau=pending)
- Log-Toggle → Status-Bar

---

## 🎨 Theme-Vorschläge (3 Neue)

### Theme 1: "Clean Slate" (Minimalistisch Hell)

```python
CLEAN_SLATE = {
    "key": "clean_slate",
    "name": "Clean Slate",
    "colors": {
        "window": "#FAFBFC",
        "window_text": "#1A1A2E",
        "base": "#FFFFFF",
        "text": "#1A1A2E",
        "button": "#EAECEF",
        "button_text": "#1A1A2E",
        "highlight": "#4A6CF7",
        "highlighted_text": "#FFFFFF",
        "link": "#4A6CF7",
        "placeholder": "#9CA3AF",
        "border": "#E1E4E8",
        "success": "#28A745",
        "warning": "#FFC107",
        "error": "#DC3545",
    }
}
```

**Charakteristik:**
- Sehr wenig visuelle Ablenkung
- Großzügige Weißräume
- Nur Akzentfarbe (Blau) für Interaktives
- Inspiriert von: VS Code Light+, GitHub Light

---

### Theme 2: "Midnight Pro" (Professional Dunkel)

```python
MIDNIGHT_PRO = {
    "key": "midnight_pro",
    "name": "Midnight Pro",
    "colors": {
        "window": "#0D1117",
        "window_text": "#C9D1D9",
        "base": "#161B22",
        "text": "#C9D1D9",
        "button": "#21262D",
        "button_text": "#C9D1D9",
        "highlight": "#58A6FF",
        "highlighted_text": "#0D1117",
        "link": "#58A6FF",
        "placeholder": "#6E7681",
        "border": "#30363D",
        "success": "#3FB950",
        "warning": "#D29922",
        "error": "#F85149",
    }
}
```

**Charakteristik:**
- GitHub Dark-inspiriert
- Kontrastreiche Akzente
- Dezente Ränder
- Augenfreundlich bei langer Nutzung

---

### Theme 3: "Retro Console" (Nostalgie)

```python
RETRO_CONSOLE = {
    "key": "retro_console",
    "name": "Retro Console",
    "colors": {
        "window": "#2C2137",
        "window_text": "#F0E7D5",
        "base": "#3D2F4A",
        "text": "#F0E7D5",
        "button": "#6B4C7A",
        "button_text": "#F0E7D5",
        "highlight": "#FF6B97",
        "highlighted_text": "#2C2137",
        "link": "#FF6B97",
        "placeholder": "#A89DB0",
        "border": "#5A4668",
        "success": "#95D17E",
        "warning": "#FFD166",
        "error": "#EF476F",
    }
}
```

**Charakteristik:**
- SNES/Mega Drive-Ära Farbpalette
- Warme, nostalgische Farben
- Pink-Akzent für interaktive Elemente
- Abgerundete Ecken (12px)

---

## 📋 Implementierungs-Roadmap

### Phase 1: Struktur-Split (Kritisch) 🔴

**Ziel:** `qt_app_impl.py` (5.000 Zeilen) aufteilen

```
src/ui/mvp/
├── __init__.py
├── qt_app.py              # Entry point
├── main_window.py         # Shell, Header, Status-Bar, Tab-Container
├── tabs/
│   ├── __init__.py
│   ├── home_tab.py        # Dashboard/Quick-Start
│   ├── sort_tab.py        # Hauptworkflow
│   ├── convert_tab.py     # Konvertierungen + IGIR
│   ├── settings_tab.py    # Einstellungen
│   └── reports_tab.py     # Export/Reports
├── dialogs/
│   ├── __init__.py
│   ├── db_manager.py      # DBManagerDialog
│   └── dat_sources.py     # DatSourcesDialog
├── widgets/
│   ├── __init__.py
│   ├── drop_line_edit.py  # Drag & Drop Input
│   ├── filter_sidebar.py  # Filter-Sidebar
│   ├── results_table.py   # Ergebnistabelle
│   └── progress_header.py # Progress-Bar + Stepper
├── workers/
│   ├── __init__.py
│   └── qt_workers.py      # Alle Worker-Klassen
└── utils/
    ├── __init__.py
    ├── export_utils.py
    ├── model_utils.py
    └── qt_log_utils.py
```

### Phase 2: Layout-Vereinfachung (Hoch) 🟠

1. Header auf Kernelemente reduzieren
2. Pfade-Duplizierung entfernen (nur im Sort-Tab)
3. Filter-Sidebar einbauen (rechts, einklappbar)
4. Status-Bar einführen (ersetzt Pills im Header)
5. IGIR in Konvertieren-Tab integrieren
6. DAT/DB in Einstellungen verschieben

### Phase 3: UX-Polish (Mittel) 🟡

1. Stepper durch Progress-Bar ersetzen
2. Neue Themes einbauen (Clean Slate, Midnight Pro, Retro Console)
3. Empty-States verbessern (Illustrationen, Call-to-Action)
4. Tooltips & Hilfe-Icons hinzufügen
5. Details-Panel nur bei Auswahl anzeigen

### Phase 4: Details (Niedrig) 🟢

1. Keyboard-Shortcuts dokumentieren (Ctrl+K, Ctrl+Enter)
2. Drag & Drop visuelles Feedback
3. Animationen (sanfte Tab-Übergänge)
4. Recent-Files im Home-Tab

---

## 🔄 Vergleich: Alt vs. Neu

| Aspekt | Alt | Neu |
|--------|-----|-----|
| **Tabs** | 6 (Dashboard, Sortierung, Konvertierungen, IGIR, Datenbank, Einstellungen) | 5 (Home, Sortieren, Konvertieren, Einstellungen, Reports) |
| **Pfad-Eingaben** | 3× (Haupt, Konvertierung, IGIR) | 1× (Sort-Tab) |
| **Header-Widgets** | ~15 | ~6 |
| **Filter-Zugang** | Sub-Tab "Filter" (versteckt) | Sidebar rechts (sichtbar) |
| **Einstellungen** | Verstreut über Tabs | Zentral in Settings-Tab |
| **IGIR** | Eigener Tab | Unter Konvertieren (Section) |
| **Datenbank/DAT** | Eigener Tab | Unter Settings |
| **Status-Anzeige** | Pills im Header | Status-Bar unten |
| **Themes** | 4 vorhanden | 7 (+ Clean Slate, Midnight Pro, Retro Console) |
| **Code-Struktur** | 1 Datei (5.000 Zeilen) | Modulare Struktur |

---

## ✅ Definition of Done

Das refactored GUI gilt als fertig, wenn:

1. ✅ **5 Tabs** statt 6 (Home, Sortieren, Konvertieren, Einstellungen, Reports)
2. ✅ **Pfade nur einmal** (im Sort-Tab)
3. ✅ **Header verschlankt** (<6 Widgets + Progress-Bar)
4. ✅ **Filter sichtbar** (Sidebar rechts)
5. ✅ **IGIR in Konvertieren** integriert
6. ✅ **3 neue Themes** verfügbar
7. ✅ **Code modular** (kein 5.000-Zeilen-Monster)
8. ✅ **MVP-Smoke-Tests** weiterhin grün
9. ✅ **GUI startet stabil** (`python start_rom_sorter.py --gui`)

---

## ⚠️ Risiken & Mitigationen

| Risiko | Mitigation |
|--------|------------|
| Breaking Change für bestehende Nutzer | Migration-Guide, alte Optionen unter "Erweitert" |
| IGIR-Power-User vermissen eigenen Tab | Prominente Section, "Erweitert"-Toggle |
| Code-Split führt zu Import-Problemen | Schrittweises Refactoring, CI-Tests nach jedem Schritt |
| Theme-Änderungen brechen Styles | Theme-Preview in Einstellungen beibehalten |

---

## 📝 Nächste Schritte

1. **Review dieses Dokuments** mit Stakeholdern
2. **Prototyp** der neuen Tab-Struktur (Wireframes/Mockups)
3. **Phase 1 starten**: Code-Split von `qt_app_impl.py`
4. **MVP-Tests** nach jedem Refactoring-Schritt ausführen
