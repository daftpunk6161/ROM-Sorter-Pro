# ROM-Sorter-Pro – Feature-Backlog & Produkt-Roadmap

> **Erstellt:** 2026-01-30  
> **Aktualisiert:** 2026-01-31  
> **Scope:** GUI-first Desktop-Tool (Qt/Tk-Fallback)  
> **Fokus:** Stabilität, Detection Accuracy, Power-User Workflows  
> **Status:** MVP umgesetzt, Release-Kandidat

---

## A) Pain Points (typisch bei ROM-Sortern)

| # | Pain Point | Impact | Betroffene User |
|---|------------|--------|-----------------|
| 1 | **„Unknown" ohne Erklärung** – User weiß nicht, warum eine ROM nicht erkannt wurde | Hoch | Alle |
| 2 | **False Positives** – ROM wird falschem System zugeordnet, User merkt es erst nach Sortierung | Kritisch | Power-User |
| 3 | **Keine Korrekturmöglichkeit** – Wenn Erkennung falsch, gibt es keinen einfachen Override | Mittel | Power-User |
| 4 | **Langsame Scans bei großen Libraries** (100k+ Dateien) – UI friert ein oder dauert ewig | Hoch | Power-User |
| 5 | **Datenverlust-Angst** – User traut sich nicht „Execute" zu drücken, weil unklar was passiert | Hoch | Einsteiger |
| 6 | **Konflikte/Duplikate** – Mehrere ROMs mit gleichem Zielpfad, unklar welche gewinnt | Mittel | Alle |
| 7 | **Kein Rollback** – Nach fehlerhafter Sortierung manuelles Aufräumen nötig | Hoch | Alle |
| 8 | **DAT-Chaos** – Welche DATs sind geladen? Sind sie aktuell? Decken sie meine ROMs ab? | Mittel | Power-User |
| 9 | **UI-Überfrachtung** – Zu viele Optionen auf einmal, Einsteiger verlieren sich | Mittel | Einsteiger |
| 10 | **Fehlende Transparenz** – Plan ist eine Black Box, man sieht nicht welche Regel/Quelle entschied | Mittel | Power-User |

---

## B) Feature-Katalog (50 Features, kategorisiert)

### B.1 Reliability / Detection Accuracy (15 Features)

#### F01: Why-Unknown-Analyzer (Enhanced)
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Zeigt pro unbekannter ROM die konkreten Gründe (keine DAT-Matches, Extension unknown, Hash-Collision, etc.)
- **User Value:** User versteht sofort, was fehlt und kann gezielt nachbessern
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** DAT-Index, Detection Pipeline
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Golden-Fixture mit bekannten Unknown-Gründen, prüfen ob alle Reasons korrekt angezeigt werden

#### F02: Confidence-Score-Visualisierung
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Zeigt Detection-Confidence als Ampel/Prozentwert in der Ergebnisliste
- **User Value:** Sofort erkennbar, welche Ergebnisse sicher vs. unsicher sind
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Controller liefert bereits confidence
- **MVP-Fit:** Ja
- **Test-Idee:** UI-Snapshot-Test mit verschiedenen Confidence-Stufen

#### F03: Hash-Cross-Check (Multi-DAT)
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Prüft Hash gegen mehrere DAT-Quellen und zeigt Übereinstimmungen/Abweichungen
- **User Value:** Höhere Treffsicherheit, Erkennung von Bad-Dumps
- **Komplexität:** M
- **Risiko:** Mittel (Performance bei vielen DATs)
- **Abhängigkeiten:** DAT-Index-SQLite
- **MVP-Fit:** Ja
- **Test-Idee:** ROM mit bekanntem Hash gegen 3 DATs prüfen, erwartete Matches validieren

#### F04: Heuristik-Pipeline-Visualizer
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Zeigt welche Heuristiken in welcher Reihenfolge geprüft wurden und warum sie matched/failed
- **User Value:** Vollständige Transparenz der Entscheidungskette
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Detection-Handler Refactoring
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Dummy-ROM durch Pipeline, prüfen ob alle Steps geloggt werden

#### F05: Quick-Override-Dialog (Inline)
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Rechtsklick auf ROM → „Als [System] markieren" direkt in der Tabelle
- **User Value:** Schnelle Korrektur ohne Umwege
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Override-YAML-System (existiert)
- **MVP-Fit:** Ja
- **Test-Idee:** Override setzen, Scan wiederholen, prüfen ob Override greift

#### F06: Bulk-Override-Wizard
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Mehrere ROMs selektieren → gemeinsamen Override setzen (z.B. „alle als SNES")
- **User Value:** Zeitersparnis bei vielen Fehlzuordnungen
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** F05
- **MVP-Fit:** Ja
- **Test-Idee:** 10 ROMs selektieren, Bulk-Override, alle müssen Override haben

#### F07: Detection-Rule-Tester (Dev-Tool)
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Eingabefeld für Dateinamen/Hash → zeigt welche Regel greifen würde
- **User Value:** Power-User/Entwickler können Regeln debuggen
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Detection-Handler
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Bekannte Muster eingeben, erwartete Matches prüfen

#### F08: Fingerprint-Erweiterung (Magic Bytes)
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Zusätzliche Header-Signatur-Prüfung für Formate ohne eindeutige Extension
- **User Value:** Weniger False Positives bei generischen Extensions (.bin, .rom)
- **Komplexität:** M
- **Risiko:** Mittel (False-Positive-Gefahr bei schlechten Signaturen)
- **Abhängigkeiten:** Detector-Base
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** .bin-Dateien mit verschiedenen Headers, prüfen ob korrekt erkannt

#### F09: DAT-Coverage-Report
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Zeigt welche Systeme durch geladene DATs abgedeckt sind und wo Lücken sind
- **User Value:** User weiß, welche DATs noch fehlen
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** DAT-Index
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Index mit 3 DATs, Report zeigt exakt 3 Systeme

#### F10: Fuzzy-Name-Matching
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Findet ähnliche Einträge in DAT wenn exakter Hash fehlt (Levenshtein/Token-Match)
- **User Value:** Bessere Kandidaten-Vorschläge bei Unknown
- **Komplexität:** M
- **Risiko:** Mittel (Performance, False-Positive-Gefahr)
- **Abhängigkeiten:** DAT-Index
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** ROM mit leicht abweichendem Namen, prüfen ob Kandidat vorgeschlagen wird

#### F11: Conflict-Resolver-Dialog
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Bei Zielkonflikt (2 ROMs → gleicher Pfad): Dialog mit Optionen (Rename, Skip, Prefer-By-Region)
- **User Value:** Keine versehentlichen Überschreibungen
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Plan-Validation
- **MVP-Fit:** Ja
- **Test-Idee:** 2 ROMs mit gleichem Ziel, Dialog muss erscheinen

#### F12: Preferred-Region-Chain
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Konfigurierbare Region-Priorität (z.B. EUR > USA > JPN) für Auto-Dedupe
- **User Value:** Automatisch „beste" Version behalten
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Filter-System (existiert)
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** 3 ROMs (EUR/USA/JPN), nur EUR soll im Plan sein

#### F13: Bad-Dump-Marker
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** ROMs die in DAT als [b] (bad dump) markiert sind, visuell kennzeichnen
- **User Value:** User weiß, welche ROMs problematisch sind
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** DAT-Parser muss [b]-Flag extrahieren
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** ROM mit [b] im DAT, Icon/Badge muss erscheinen

#### F14: Revision/Version-Comparator
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Bei mehreren Revisionen (v1.0, v1.1, Rev A) die neueste priorisieren
- **User Value:** Automatisch beste Version behalten
- **Komplexität:** M
- **Risiko:** Mittel (Parsing-Edge-Cases)
- **Abhängigkeiten:** Naming-Helpers
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** 3 ROMs mit v1.0/v1.1/v1.2, nur v1.2 im Plan

#### F15: Learning-Override-Suggestions
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Wenn User Override setzt, ähnliche Dateien vorschlagen („Diese 5 auch?")
- **User Value:** Schnellere Korrektur bei Pattern-basierten Fehlern
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** F05, Pattern-Matching
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Override für „Game (Europe)*.zip", ähnliche Dateien müssen vorgeschlagen werden

---

### B.2 Sorting / Planning / Preview (10 Features)

#### F16: Plan-Diff-View
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Zeigt Unterschied zwischen altem und neuem Sortierplan (hinzugefügt/entfernt/geändert)
- **User Value:** Nachvollziehbar was sich ändert bei Re-Scan
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Plan-Serialisierung
- **MVP-Fit:** Ja
- **Test-Idee:** 2 Pläne vergleichen, Diff-Count prüfen

#### F17: Plan-Export (JSON/CSV)
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Sortierplan als JSON/CSV exportieren für externe Analyse
- **User Value:** Integration mit anderen Tools, Dokumentation
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Plan-Model
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Export, Reimport, Daten identisch

#### F18: Plan-Template-System
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Wiederverwendbare Sortier-Templates (z.B. „Retro-Konsolen", „Handhelds", „Arcade")
- **User Value:** Schneller Wechsel zwischen Sortier-Strategien
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Config-System
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Template speichern, laden, Einstellungen identisch

#### F19: Folder-Structure-Preview (Tree)
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Zeigt geplante Zielstruktur als Baum-Ansicht
- **User Value:** Visuell klar, wie das Ergebnis aussehen wird
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Plan-Model
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Plan mit 3 Systemen, Baum zeigt 3 Hauptordner

#### F20: Rename-Pattern-Builder
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Visueller Editor für Dateinamens-Pattern ({title} - {region}.{ext})
- **User Value:** Keine Syntax-Fehler, sofortige Vorschau
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Naming-Helpers
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Pattern eingeben, Preview für Beispiel-ROM prüfen

#### F21: Copy-First-Staging (Safe Mode)
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Kopiert erst in Staging-Ordner, dann atomic move ins Ziel
- **User Value:** Rollback bei Fehler trivial
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Execute-Helpers
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Execute mit Fehler in der Mitte, Staging muss aufräumbar sein

#### F22: Partial-Execute (Selected Only)
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Nur ausgewählte Zeilen aus dem Plan ausführen
- **User Value:** Schrittweise Sortierung, Kontrolle
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Plan-Selection-State
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** 10 Items, 3 selektiert, nur 3 werden ausgeführt

#### F23: Action-Override-per-Item
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Pro ROM-Zeile: Action ändern (Move/Copy/Skip) ohne globale Einstellung
- **User Value:** Granulare Kontrolle
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Plan-Model
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** 3 Items, unterschiedliche Actions, Execute prüft alle

#### F24: Estimated-Time-Display
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Zeigt geschätzte Dauer basierend auf Dateigröße und IO-Speed
- **User Value:** Erwartungsmanagement bei großen Libraries
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Performance-Metrics
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Plan mit 10 GB, Schätzung plausibel (±30%)

#### F25: Plan-History (Undo-Stack)
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Letzte 5 Pläne im Speicher, Undo/Redo möglich
- **User Value:** Versehentliche Änderungen rückgängig machen
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Plan-State-Management
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Plan ändern, Undo, alter Zustand wiederhergestellt

---

### B.3 Safety / Security (6 Features)

#### F26: Full-Rollback-System
- **Kategorie:** Safety / Security
- **Kurzbeschreibung:** Nach Execute: vollständiges Manifest für Undo (alle Moves rückgängig)
- **User Value:** Fehler sind reversibel
- **Komplexität:** M
- **Risiko:** Mittel (Edge-Cases bei Overwrites)
- **Abhängigkeiten:** Rollback-Controller (existiert)
- **MVP-Fit:** Ja (existiert, UI-Integration)
- **Test-Idee:** Execute, Rollback, Dateien am Ursprungsort

#### F27: Pre-Execute-Checksum-Validation
- **Kategorie:** Safety / Security
- **Kurzbeschreibung:** Vor Move/Copy: Hash prüfen, ob Datei unverändert seit Scan
- **User Value:** Keine korrupten Kopien
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Hash-Cache
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Datei zwischen Scan und Execute ändern, Warnung muss erscheinen

#### F28: Disk-Space-Check
- **Kategorie:** Safety / Security
- **Kurzbeschreibung:** Vor Execute: prüfen ob Ziel genug Platz hat
- **User Value:** Kein Abbruch mitten im Kopiervorgang
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Plan-Size-Calculation
- **MVP-Fit:** Ja
- **Test-Idee:** Plan mit 100 GB, Ziel hat 50 GB frei, Warnung erscheint

#### F29: Review-Gate-Enhancement
- **Kategorie:** Safety / Security
- **Kurzbeschreibung:** Pflicht-Review bei >1000 Dateien oder >10 GB
- **User Value:** Schutz vor versehentlichen Massen-Aktionen
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Review-Gate (existiert)
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Plan mit 2000 Dateien, Review-Dialog erscheint

#### F30: Symlink-Detection-Warning
- **Kategorie:** Safety / Security
- **Kurzbeschreibung:** Warnung wenn Quelle/Ziel Symlinks enthält
- **User Value:** Verhindert unbeabsichtigte Traversals
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Security-Helpers (existiert)
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Ordner mit Symlink als Quelle, Warnung erscheint

#### F31: Backup-Before-Overwrite
- **Kategorie:** Safety / Security
- **Kurzbeschreibung:** Bei Konflikt mit existierender Datei: automatisches Backup anlegen
- **User Value:** Keine Datenverluste
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Backup-Controller
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Ziel existiert, nach Execute: Backup vorhanden

---

### B.4 Performance / Scale (5 Features)

#### F32: Incremental-Scan
- **Kategorie:** Performance / Scale
- **Kurzbeschreibung:** Nur neue/geänderte Dateien scannen (basierend auf mtime/size)
- **User Value:** Dramatisch schnellere Re-Scans
- **Komplexität:** M
- **Risiko:** Mittel (Cache-Invalidierung)
- **Abhängigkeiten:** Hash-Cache
- **MVP-Fit:** Ja
- **Test-Idee:** 1000 Dateien scannen, 1 ändern, nur 1 wird re-gescannt

#### F33: Parallel-Hashing
- **Kategorie:** Performance / Scale
- **Kurzbeschreibung:** Mehrere Dateien gleichzeitig hashen (Thread-Pool)
- **User Value:** Schnellere Scans bei SSDs
- **Komplexität:** M
- **Risiko:** Mittel (IO-Contention bei HDDs)
- **Abhängigkeiten:** Hash-Utils
- **MVP-Fit:** Ja (IO-aware existiert, Erweiterung)
- **Test-Idee:** 100 Dateien hashen, Parallelität messbar schneller

#### F34: Index-Sharding
- **Kategorie:** Performance / Scale
- **Kurzbeschreibung:** DAT-Index auf mehrere SQLite-Dateien verteilen
- **User Value:** Schnellere Lookups bei sehr großen Indices
- **Komplexität:** L
- **Risiko:** Hoch
- **Abhängigkeiten:** DAT-Index-SQLite
- **MVP-Fit:** Nein
- **Test-Idee:** 1M Einträge, Lookup < 100ms

#### F35: Lazy-Archive-Extraction
- **Kategorie:** Performance / Scale
- **Kurzbeschreibung:** Archive nur bei Bedarf extrahieren, nicht immer komplett
- **User Value:** Weniger temp-Speicher, schneller bei großen Archives
- **Komplexität:** M
- **Risiko:** Mittel
- **Abhängigkeiten:** Archive-Detector
- **MVP-Fit:** Nein
- **Test-Idee:** 5 GB ZIP, nur Header wird gelesen wenn möglich

#### F36: Background-Index-Update
- **Kategorie:** Performance / Scale
- **Kurzbeschreibung:** DAT-Index im Hintergrund aktualisieren ohne UI-Block
- **User Value:** Keine Wartezeit beim Start
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Threading, Index-Controller
- **MVP-Fit:** Ja
- **Test-Idee:** Start, Index-Update läuft, UI sofort bedienbar

---

### B.5 UX / Self-explaining UI (10 Features)

#### F37: Guided-First-Run-Wizard
- **Kategorie:** UX / Self-explaining UI
- **Kurzbeschreibung:** Bei erstem Start: Assistent für Quelle, Ziel, DAT-Download, erste Sortierung
- **User Value:** Einsteiger finden sofort den Einstieg
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Config, DAT-Manager
- **MVP-Fit:** Ja
- **Test-Idee:** Fresh-Config, Wizard erscheint, nach Abschluss Config vollständig

#### F38: Contextual-Help-Tooltips
- **Kategorie:** UX / Self-explaining UI
- **Kurzbeschreibung:** Jede wichtige Option hat Info-Icon mit Erklärung
- **User Value:** Keine externe Doku nötig
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** I18n-System
- **MVP-Fit:** Ja
- **Test-Idee:** Tooltip für „Confidence Threshold" enthält sinnvollen Text

#### F39: Status-Bar-Summary
- **Kategorie:** UX / Self-explaining UI
- **Kurzbeschreibung:** Permanente Statuszeile: „X ROMs | Y erkannt | Z Unknown | Bereit für Execute"
- **User Value:** Sofortiger Überblick ohne Tab-Wechsel
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** State-Machine
- **MVP-Fit:** Ja
- **Test-Idee:** Nach Scan: Zahlen korrekt

#### F40: Empty-State-Guidance
- **Kategorie:** UX / Self-explaining UI
- **Kurzbeschreibung:** Leere Tabelle zeigt „Wähle Quelle und starte Scan" statt leere Fläche
- **User Value:** Klare Handlungsanweisung
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** UI-Components
- **MVP-Fit:** Ja
- **Test-Idee:** Frischer Start, Empty-State-Text sichtbar

#### F41: Keyboard-Shortcuts-Overlay
- **Kategorie:** UX / Self-explaining UI
- **Kurzbeschreibung:** ? oder F1 zeigt Shortcut-Übersicht als Overlay
- **User Value:** Power-User arbeiten schneller
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Shortcut-Definitionen
- **MVP-Fit:** Ja
- **Test-Idee:** F1 drücken, Overlay erscheint mit korrekten Shortcuts

#### F42: Compact-Mode
- **Kategorie:** UX / Self-explaining UI
- **Kurzbeschreibung:** Reduzierte UI für kleine Bildschirme / Einsteiger (weniger Optionen sichtbar)
- **User Value:** Weniger Überforderung
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Layout-System
- **MVP-Fit:** Ja
- **Test-Idee:** Compact-Mode aktivieren, nur Kern-Controls sichtbar

#### F43: Pro-Mode-Toggle
- **Kategorie:** UX / Self-explaining UI
- **Kurzbeschreibung:** Erweiterte Optionen nur für Power-User (versteckt im Standard-Modus)
- **User Value:** Einsteiger sehen weniger, Profis alles
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** F42
- **MVP-Fit:** Ja
- **Test-Idee:** Pro-Mode aktivieren, erweiterte Filter erscheinen

#### F44: Recent-Paths-Dropdown
- **Kategorie:** UX / Self-explaining UI
- **Kurzbeschreibung:** Letzte 10 Quell-/Zielpfade als Dropdown
- **User Value:** Schneller Zugriff auf häufige Ordner
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Config (existiert)
- **MVP-Fit:** Ja
- **Test-Idee:** 3 Pfade verwendet, Dropdown zeigt alle 3

#### F45: Action-Undo-Toast
- **Kategorie:** UX / Self-explaining UI
- **Kurzbeschreibung:** Nach Execute: Toast-Notification mit „Undo"-Link (5 Sekunden)
- **User Value:** Schnelles Rückgängigmachen
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Rollback-System
- **MVP-Fit:** Ja
- **Test-Idee:** Execute, Toast erscheint, Undo-Klick führt Rollback aus

#### F46: Log-Search-and-Filter
- **Kategorie:** UX / Self-explaining UI
- **Kurzbeschreibung:** Textsuche im Log + Severity-Filter (Error/Warn/Info)
- **User Value:** Schnelles Debugging
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Log-Viewer (existiert)
- **MVP-Fit:** Ja (existiert, Erweiterung)
- **Test-Idee:** Log mit 100 Zeilen, Suche findet korrekte Zeile

---

### B.6 Visual / Themes (6 Features)

#### F47: Dark-Mode-Theme
- **Kategorie:** Visual / Themes
- **Kurzbeschreibung:** Vollständiger Dark-Mode mit angepassten Icons
- **User Value:** Augenschonend bei Nachtarbeit
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Theme-Manager (existiert)
- **MVP-Fit:** Ja
- **Test-Idee:** Dark-Mode aktivieren, alle Controls lesbar

#### F48: Retro/CRT-Theme (Optional)
- **Kategorie:** Visual / Themes
- **Kurzbeschreibung:** Pixelschrift + Scanlines + Phosphor-Glow als Fun-Theme
- **User Value:** Nostalgie-Faktor für Retro-Community
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Theme-Manager
- **MVP-Fit:** Nein (Fun-Feature)
- **Test-Idee:** Theme aktivieren, Font ist pixelig, Scanlines sichtbar

#### F49: Accent-Color-Picker
- **Kategorie:** Visual / Themes
- **Kurzbeschreibung:** Akzentfarbe wählbar (Header, Buttons, Selection)
- **User Value:** Personalisierung
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Theme-Manager
- **MVP-Fit:** Ja
- **Test-Idee:** Farbe ändern, Header-Farbe ändert sich

#### F50: Console-Badges/Icons
- **Kategorie:** Visual / Themes
- **Kurzbeschreibung:** Kleine Icons neben Konsolen-Namen (SNES, NES, PSX, etc.)
- **User Value:** Schnellere visuelle Orientierung
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Asset-Bundle
- **MVP-Fit:** Ja
- **Test-Idee:** ROM als SNES erkannt, SNES-Icon erscheint

#### F51: Layout-Presets
- **Kategorie:** Visual / Themes
- **Kurzbeschreibung:** Vordefinierte Fenster-Layouts (Sidebar links/rechts, Tabs oben/unten)
- **User Value:** Anpassung an Workflow
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Layout-System (existiert)
- **MVP-Fit:** Ja
- **Test-Idee:** Layout wechseln, Sidebar-Position ändert sich

#### F52: High-Contrast-Mode
- **Kategorie:** Visual / Themes
- **Kurzbeschreibung:** Barrierefreies Theme mit hohem Kontrast
- **User Value:** Zugänglichkeit
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Theme-Manager
- **MVP-Fit:** Ja
- **Test-Idee:** Theme aktivieren, WCAG-Kontrast-Ratio > 7:1

---

### B.7 Integrations / Frontends (4 Features)

#### F53: EmulationStation-Gamelist-Export (Enhanced)
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Generiert gamelist.xml mit Metadaten, Pfaden, Regionen
- **User Value:** Direkter Import in ES
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Frontend-Exporter (existiert)
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Export, XML valide, Pfade korrekt

#### F54: LaunchBox-Import-Export
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Bidirektionaler Sync mit LaunchBox-DB
- **User Value:** Keine doppelte Pflege
- **Komplexität:** L
- **Risiko:** Mittel
- **Abhängigkeiten:** LaunchBox-XML-Schema
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Export, Import in LaunchBox, ROMs erscheinen

#### F55: RetroArch-Playlist-Generator
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Generiert .lpl-Dateien für RetroArch
- **User Value:** Schneller Einstieg in RetroArch
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Plan-Model
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Export, .lpl valide JSON, Pfade korrekt

#### F56: CLI-Batch-Mode
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Headless-Modus für Scripting (scan → plan → execute ohne GUI)
- **User Value:** Automatisierung, CI-Integration
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Controller-API
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** CLI-Aufruf, JSON-Output, Exit-Code korrekt

---

### B.8 Data / DB / DAT Management (4 Features)

#### F57: DAT-Auto-Updater
- **Kategorie:** Data / DB / DAT Management
- **Kurzbeschreibung:** Prüft auf DAT-Updates (No-Intro, Redump), lädt neue Versionen
- **User Value:** Immer aktuelle DATs
- **Komplexität:** M
- **Risiko:** Mittel (Netzwerk-Abhängigkeit)
- **Abhängigkeiten:** DAT-Sources (existiert)
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Mock-Server mit neuer DAT, Update wird erkannt

#### F58: Custom-DAT-Builder
- **Kategorie:** Data / DB / DAT Management
- **Kurzbeschreibung:** Eigene DATs aus Scan-Ergebnissen erstellen
- **User Value:** Eigene Sammlungen dokumentieren
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** DAT-Writer
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Scan, DAT exportieren, DAT valide

#### F59: Hash-Cache-Inspector
- **Kategorie:** Data / DB / DAT Management
- **Kurzbeschreibung:** UI zum Anzeigen/Löschen von Cache-Einträgen
- **User Value:** Debugging, Cache-Kontrolle
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Hash-Cache
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Cache mit 100 Einträgen, UI zeigt alle, Löschen funktioniert

#### F60: Database-Integrity-Check
- **Kategorie:** Data / DB / DAT Management
- **Kurzbeschreibung:** SQLite-VACUUM + Integrity-Check mit UI-Feedback
- **User Value:** Datenbank-Pflege
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** DB-Manager
- **MVP-Fit:** Ja (umgesetzt)
- **Test-Idee:** Korrupte DB erkennen, Warnung anzeigen

---

### B.9 Zusätzliche Feature-Ideen (F61-F70) – Neu 2026-01-31

#### F61: Smart-Queue-Priority-Reordering
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Drag-and-Drop Neuordnung der Sortier-Queue mit Auto-Priorität (kleine Dateien zuerst, Fehler ans Ende)
- **User Value:** Bessere Kontrolle über Sortierreihenfolge, schnelles Feedback bei kleinen Jobs
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Job-Queue-System
- **MVP-Fit:** Nein
- **Test-Idee:** Queue mit 10 Items, Drag Item 5 nach oben, Reihenfolge ändert sich

#### F62: Detection-Confidence-Tuner (Slider)
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Globaler Slider für Mindest-Confidence (50%-99%), unter Schwelle → automatisch Unknown
- **User Value:** Balance zwischen Recall und Precision einstellen
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Controller-Config
- **MVP-Fit:** Ja
- **Test-Idee:** Slider auf 90%, ROM mit 85% Confidence → Unknown

#### F63: Multi-Library-Workspace ✅
- **Kategorie:** Performance / Scale
- **Kurzbeschreibung:** Mehrere Quell-Libraries parallel verwalten (Tabs oder Tree-View)
- **User Value:** Power-User mit mehreren Sammlungen können alles in einem Tool verwalten
- **Komplexität:** L
- **Risiko:** Mittel (State-Management-Komplexität)
- **Abhängigkeiten:** Neue Architecture
- **MVP-Fit:** Nein
- **Status:** ✅ Implementiert in `src/core/multi_library.py`
- **Test-Idee:** 2 Libraries hinzufügen, beide scannen, beide sortieren, keine Konflikte

#### F64: AI-Assisted-Name-Normalizer (Optional) ✅
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** LLM-basierte Korrektur von Dateinamen (Typos, fehlende Region-Tags) – rein optional, offline-fähig
- **User Value:** Automatische Cleanup von schlecht benannten ROM-Dumps
- **Komplexität:** L
- **Risiko:** Hoch (False Positives, Dependency-Bloat)
- **Abhängigkeiten:** Optional ML-Package
- **MVP-Fit:** Nein
- **Status:** ✅ Implementiert in `src/detectors/ai_normalizer.py`
- **Test-Idee:** "Super_Maro_Wrld.sfc" → Vorschlag "Super Mario World (USA).sfc"

#### F65: Watchfolder-Auto-Sort ✅
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Überwacht Ordner, neue Dateien werden automatisch gescannt und sortiert
- **User Value:** Hands-off Workflow für kontinuierliche Downloads
- **Komplexität:** M
- **Risiko:** Mittel (Background-Service-Stabilität)
- **Abhängigkeiten:** File-System-Watcher
- **MVP-Fit:** Nein
- **Status:** ✅ Implementiert in `src/core/watchfolder.py`
- **Test-Idee:** Datei in Watchfolder legen, nach 5s automatisch sortiert

#### F66: Collection-Completeness-Tracker ✅
- **Kategorie:** Data / DB / DAT Management
- **Kurzbeschreibung:** Zeigt pro System: X% komplett laut DAT, fehlende ROMs als Liste
- **User Value:** Sammler sehen ihren Fortschritt, Motivation zum Vervollständigen
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** DAT-Index, Scan-Results
- **MVP-Fit:** Ja
- **Status:** ✅ Implementiert in `src/analytics/completeness_tracker.py`
- **Test-Idee:** Scan mit 50 SNES-ROMs, DAT hat 100 → zeigt "50% komplett"

#### F67: Screenshot-/Boxart-Preview (Optional) ✅
- **Kategorie:** Visual / Themes
- **Kurzbeschreibung:** Zeigt Boxart/Screenshot neben ROM-Info (aus libretro-thumbnails oder lokal)
- **User Value:** Visuelle Identifikation, Eye-Candy
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Optional Thumbnail-Cache
- **MVP-Fit:** Nein
- **Status:** ✅ Implementiert in `src/ui/preview/boxart_preview.py`
- **Test-Idee:** ROM selektieren, Thumbnail erscheint in Sidebar (oder Platzhalter)

#### F68: Gamification-Progress-Badges ✅
- **Kategorie:** UX / Self-explaining UI
- **Kurzbeschreibung:** Badges für Meilensteine ("1000 ROMs sortiert", "First Rollback", "DAT-Master")
- **User Value:** Motivation, Fun-Faktor
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Local Metrics
- **Status:** ✅ Implementiert in `src/gamification/badges.py`
- **MVP-Fit:** Nein
- **Test-Idee:** 1000 ROMs sortieren, Badge erscheint mit Animation

#### F69: Export-to-MiSTer-SD
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Direkte Ausgabe im MiSTer-FPGA-Ordnerformat (mit Core-Mapping)
- **User Value:** MiSTer-Nutzer können sofort loslegen
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** MiSTer-Folder-Spec
- **MVP-Fit:** Ja
- **Test-Idee:** Export für SNES, Ordnerstruktur entspricht MiSTer-Konvention

#### F70: Portable-Mode (USB-Stick)
- **Kategorie:** Safety / Security
- **Kurzbeschreibung:** Alle Config/Cache/Logs relativ zum Programm, kein Schreiben in AppData
- **User Value:** Tool auf USB-Stick mitnehmen, auf fremden Rechnern nutzen
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Config-Pfad-Refactoring
- **MVP-Fit:** Ja
- **Test-Idee:** Portable-Flag setzen, Config liegt neben .exe

---

### B.10 ROM-Verifizierung & Audit (F71-F74)

#### F71: Bad-Dump-Scanner ✅
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Erkennt korrupte/unvollständige ROMs anhand von DAT-Flags `[b]`, `[!]`, `[o]`, `[h]`
- **User Value:** Qualitätskontrolle der Sammlung, nur verifizierte ROMs behalten
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** DAT-Parser (existiert)
- **MVP-Fit:** Ja
- **Status:** ✅ Implementiert in `src/verification/rom_verifier.py`
- **Test-Idee:** ROM mit [b]-Flag im DAT, Scanner markiert als Bad-Dump

#### F72: Intro/Trainer-Erkennung ✅
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Findet ROMs mit Crack-Intros oder Trainern `[t]`, `[f]`, `[a]`, `[p]`, `[T]`, `[I]` (fixed)
- **User Value:** Saubere Sammlung ohne modifizierte ROMs
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** DAT-Parser, Naming-Parser
- **MVP-Fit:** Ja
- **Status:** ✅ Implementiert in `src/verification/rom_verifier.py`
- **Test-Idee:** ROM mit [t1] im Namen, wird als Trainer erkannt

#### F73: Overdump-Erkennung ✅
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Findet ROMs mit überschüssigen Daten (größer als DAT-Eintrag)
- **User Value:** Speicherplatz sparen, korrekte Dumps bevorzugen
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** DAT-Index mit Size-Info
- **MVP-Fit:** Ja
- **Status:** ✅ Implementiert in `src/verification/rom_verifier.py`
- **Test-Idee:** ROM 1MB, DAT sagt 512KB → Overdump-Warnung

#### F74: ROM-Integritäts-Report ✅
- **Kategorie:** Data / DB / DAT Management
- **Kurzbeschreibung:** Vollständiger Audit-Bericht pro System (Good/Bad/Missing/Overdump) mit Health-Score
- **User Value:** Dokumentation der Sammlungsqualität, Export als JSON
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** F71-F73, Report-Generator
- **MVP-Fit:** Ja
- **Status:** ✅ Implementiert in `src/verification/integrity_report.py`
- **Test-Idee:** Audit für SNES, Report zeigt alle Kategorien mit Zahlen

---

### B.11 Duplikat-Management (F75-F78)

#### F75: Hash-basierte Duplikat-Erkennung ✅
- **Kategorie:** Performance / Scale
- **Kurzbeschreibung:** Findet identische Dateien anhand von SHA1/CRC32 Hash (auch bei anderem Namen)
- **User Value:** Speicherplatz sparen, Duplikate entfernen
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Hash-Cache (existiert)
- **MVP-Fit:** Ja
- **Status:** ✅ Implementiert in `src/duplicates/hash_duplicate_finder.py`
- **Test-Idee:** 2 Dateien mit gleichem Hash, unterschiedlicher Name → als Duplikat erkannt

#### F76: Fuzzy-Duplikat-Finder ✅
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Findet ähnliche ROMs (Rev A vs Rev B, verschiedene Regionen) mit Levenshtein-Distanz
- **User Value:** 1G1R-Sets bauen, beste Version behalten
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Naming-Parser, Region-Priorität
- **MVP-Fit:** Ja
- **Status:** ✅ Implementiert in `src/duplicates/fuzzy_duplicate_finder.py`
- **Test-Idee:** "Game (USA)" und "Game (Europe)" → als Fuzzy-Duplikate erkannt

#### F77: Duplikat-Merge-Wizard ✅
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Intelligentes Zusammenführen von Duplikaten mit Preview und konfigurierbaren Strategien
- **User Value:** Aufgeräumte Sammlung, kontrollierter Merge
- **Komplexität:** M
- **Risiko:** Mittel (Datenverlust bei falscher Wahl)
- **Abhängigkeiten:** F75, F76, Rollback-System
- **MVP-Fit:** Ja
- **Status:** ✅ Implementiert in `src/duplicates/merge_wizard.py`
- **Test-Idee:** 5 Duplikat-Gruppen, Wizard zeigt alle, Merge ausführen, nur Gewinner bleiben

#### F78: Parent/Clone-Verwaltung (MAME-Style) ✅
- **Kategorie:** Data / DB / DAT Management
- **Kurzbeschreibung:** MAME-Style Parent-Clone-Beziehungen verwalten und anzeigen
- **User Value:** Arcade-Sammlungen professionell organisieren, Hierarchie-Ansicht
- **Komplexität:** L
- **Risiko:** Mittel
- **Abhängigkeiten:** MAME-DAT-Parser
- **MVP-Fit:** Ja
- **Status:** ✅ Implementiert in `src/duplicates/parent_clone.py`
- **Test-Idee:** MAME-Set laden, Parent/Clone-Tree korrekt aufgebaut

---

### B.12 Patch-Management (F79-F82)

#### F79: IPS/BPS/UPS-Patcher
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Patches (Übersetzungen, Hacks) direkt auf ROMs anwenden
- **User Value:** Fan-Translations nutzen, keine externen Tools nötig
- **Komplexität:** M
- **Risiko:** Mittel (ROM-Modifikation)
- **Abhängigkeiten:** Patch-Library (python-ips oder eigene Impl.)
- **MVP-Fit:** Ja
- **Test-Idee:** IPS-Patch auf ROM anwenden, Hash ändert sich korrekt

#### F80: Patch-Bibliothek-Manager
- **Kategorie:** Data / DB / DAT Management
- **Kurzbeschreibung:** Verwaltet Patches pro ROM/System, zeigt kompatible Patches
- **User Value:** Übersicht über verfügbare Patches
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Patch-Ordner-Struktur
- **MVP-Fit:** Nein
- **Test-Idee:** Patch-Ordner scannen, Patches korrekt ROMs zugeordnet

#### F81: Auto-Patch-Matching
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Findet automatisch passende Patches für ROMs (anhand Hash/Name)
- **User Value:** Kein manuelles Suchen nach dem richtigen Patch
- **Komplexität:** M
- **Risiko:** Mittel (False Matches)
- **Abhängigkeiten:** F80, Patch-DB
- **MVP-Fit:** Nein
- **Test-Idee:** ROM scannen, passender Patch aus Library wird vorgeschlagen

#### F82: Soft-Patching-Support
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Patch zur Laufzeit anwenden (ohne Original-ROM zu ändern)
- **User Value:** Original bleibt unverändert, Sicherheit
- **Komplexität:** L
- **Risiko:** Hoch (Emulator-spezifisch)
- **Abhängigkeiten:** Emulator-Integration
- **MVP-Fit:** Nein
- **Test-Idee:** ROM + Patch → Emulator startet mit gepatchter Version

---

### B.13 Emulator-Integration (F83-F86)

#### F83: ROM-Direkt-Start
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** ROM mit passendem Emulator öffnen (Doppelklick oder Button)
- **User Value:** Quick-Test ohne Frontend-Wechsel
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Emulator-Pfad-Config
- **MVP-Fit:** Ja
- **Test-Idee:** SNES-ROM doppelklicken, konfigurierter Emulator startet

#### F84: Core-Zuordnung (RetroArch)
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** RetroArch-Core pro System definieren
- **User Value:** Power-User können bevorzugten Core festlegen
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** RetroArch-Config-Parser
- **MVP-Fit:** Ja
- **Test-Idee:** SNES → bsnes-Core setzen, Start nutzt diesen Core

#### F85: Save-State-Manager
- **Kategorie:** Data / DB / DAT Management
- **Kurzbeschreibung:** Speicherstände organisieren, sichern, zwischen Emulatoren migrieren
- **User Value:** Spielstände nicht verlieren beim Wechsel
- **Komplexität:** L
- **Risiko:** Hoch (Format-Unterschiede)
- **Abhängigkeiten:** Emulator-spezifische Pfade
- **MVP-Fit:** Nein
- **Test-Idee:** Save-State von Emulator A nach B kopieren, funktioniert

#### F86: Per-Game-Settings
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Individuelle Emulator-Einstellungen pro ROM speichern
- **User Value:** Problematische ROMs mit speziellen Settings starten
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Config-per-ROM-System
- **MVP-Fit:** Nein
- **Test-Idee:** ROM mit Custom-Settings speichern, beim Start werden sie geladen

---

### B.14 Hardware-Exporte (F87-F90)

#### F87: Flash-Cart-Export (EverDrive/SD2SNES)
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Export im EverDrive/SD2SNES-Ordnerformat
- **User Value:** Hardware-Nutzer können direkt auf SD-Karte kopieren
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Flash-Cart-Folder-Specs
- **MVP-Fit:** Ja
- **Test-Idee:** Export für SD2SNES, Ordnerstruktur entspricht Konvention

#### F88: Analogue-Pocket-Export
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Export im OpenFPGA-Ordnerformat für Analogue Pocket
- **User Value:** Analogue-Pocket-User können direkt loslegen
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** OpenFPGA-Folder-Spec
- **MVP-Fit:** Ja
- **Test-Idee:** Export für Pocket, Assets/common/ korrekt strukturiert

#### F89: Batocera/RetroPie-Export
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Direkt bootfähige SD-Card-Struktur für Batocera/RetroPie
- **User Value:** Raspberry Pi / PC-Setup in Minuten
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** ES-Folder-Specs (existiert teilweise)
- **MVP-Fit:** Ja
- **Test-Idee:** Export, SD-Karte in Pi, System bootet mit ROMs

#### F90: Steam-ROM-Manager-Integration
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** ROMs zu Steam hinzufügen (für Steam Deck)
- **User Value:** Steam-Deck-User haben ROMs in Steam-Library
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Steam-Shortcuts-Format
- **MVP-Fit:** Ja
- **Test-Idee:** Export, Steam zeigt ROMs als Non-Steam-Games

---

### B.15 Collection-Analytics & Backup (F91-F95)

#### F91: Sammlungs-Statistiken-Dashboard
- **Kategorie:** Data / DB / DAT Management
- **Kurzbeschreibung:** Größe, Anzahl, Verteilung pro System als Diagramme
- **User Value:** Übersicht über die gesamte Sammlung
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Scan-Results, Chart-Library
- **MVP-Fit:** Ja
- **Test-Idee:** Dashboard zeigt Pie-Chart mit System-Verteilung

#### F92: Wunschlisten-Manager
- **Kategorie:** Data / DB / DAT Management
- **Kurzbeschreibung:** Fehlende ROMs tracken, Wunschliste exportieren
- **User Value:** Sammler-Ziele dokumentieren und teilen
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** F66 (Collection-Completeness)
- **MVP-Fit:** Ja
- **Test-Idee:** Fehlende ROMs zur Wunschliste hinzufügen, Export als TXT

#### F93: Timeline-View
- **Kategorie:** Visual / Themes
- **Kurzbeschreibung:** ROMs nach Release-Jahr visualisieren (Timeline)
- **User Value:** Historischer Kontext, Sammlung chronologisch erkunden
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Release-Year aus DAT/Metadaten
- **MVP-Fit:** Nein
- **Test-Idee:** Timeline zeigt ROMs von 1985-2000 korrekt verteilt

#### F94: Inkrementelles Backup
- **Kategorie:** Safety / Security
- **Kurzbeschreibung:** Nur geänderte Dateien seit letztem Backup sichern
- **User Value:** Schnelle Backups, weniger Speicherverbrauch
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Hash-Cache, Backup-Manifest
- **MVP-Fit:** Ja
- **Test-Idee:** Erstes Backup 10GB, 1 ROM hinzufügen, zweites Backup nur 50MB

#### F95: Cloud-Sync-Support
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Sync zu OneDrive/Dropbox/NAS (nur Metadaten oder auch ROMs)
- **User Value:** Redundanz, Zugriff von mehreren Geräten
- **Komplexität:** L
- **Risiko:** Hoch (Netzwerk, Datenschutz)
- **Abhängigkeiten:** Cloud-Provider-APIs
- **MVP-Fit:** Nein
- **Test-Idee:** Sync zu OneDrive, Änderungen werden hochgeladen

---

## C) Top 20 Roadmap (Priorisiert) – Aktualisiert 2026-01-31

> **Status-Legende:** ✅ Implementiert | 🟡 In Arbeit | ⬜ Offen

| Prio | Feature | Warum jetzt? | Aufwand | Risiko | Status |
|------|---------|--------------|---------|--------|--------|
| **P0** | F02 Confidence-Score-Visualisierung | Sofort sichtbar, welche Ergebnisse unsicher sind | S | Niedrig | ✅ |
| **P0** | F05 Quick-Override-Dialog | Schnelle Korrektur = zufriedene User | S | Niedrig | ✅ |
| **P0** | F26 Full-Rollback-System (UI) | Sicherheitsnetz für alle Aktionen | M | Mittel | ✅ |
| **P0** | F28 Disk-Space-Check | Verhindert Abbrüche | S | Niedrig | ✅ |
| **P0** | F40 Empty-State-Guidance | Einsteiger-Onboarding | S | Niedrig | ✅ |
| **P1** | F11 Conflict-Resolver-Dialog | Keine versehentlichen Überschreibungen | M | Niedrig | ✅ |
| **P1** | F16 Plan-Diff-View | Nachvollziehbarkeit | M | Niedrig | ✅ |
| **P1** | F19 Folder-Structure-Preview | Visuelle Klarheit | M | Niedrig | ✅ |
| **P1** | F32 Incremental-Scan | Performance-Boost | M | Mittel | ✅ |
| **P1** | F37 Guided-First-Run-Wizard | Einsteiger-Erlebnis | M | Niedrig | ✅ |
| **P1** | F47 Dark-Mode-Theme | Standard bei modernen Apps | M | Niedrig | ✅ |
| **P1** | F71 Bad-Dump-Scanner | Qualität = Kernkompetenz | S | Niedrig | ✅ |
| **P1** | F75 Hash-Duplikat-Finder | Häufiger Pain Point | S | Niedrig | ✅ |
| **P2** | F66 Collection-Completeness-Tracker | Sammler-Motivation | M | Niedrig | ⬜ |
| **P2** | F79 IPS/BPS-Patcher | Fan-Translation-Community | M | Mittel | ✅ |
| **P2** | F87 Flash-Cart-Export | Hardware-Boom | M | Niedrig | ⬜ |
| **P2** | F83 ROM-Direkt-Start | Quick-Test-Workflow | S | Niedrig | ✅ |
| **P2** | F69 Export-to-MiSTer-SD | Wachsende MiSTer-Community | M | Niedrig | ⬜ |
| **P2** | F70 Portable-Mode | Flexibilität | S | Niedrig | ⬜ |
| **P2** | F91 Sammlungs-Dashboard | Übersicht & Eye-Candy | M | Niedrig | ⬜ |
| **P1** | F37 Guided-First-Run-Wizard | Einsteiger-Erlebnis | M | Niedrig | ✅ |
| **P1** | F47 Dark-Mode-Theme | Standard bei modernen Apps | M | Niedrig | ✅ |
| **P2** | F66 Collection-Completeness-Tracker | Sammler-Motivation | M | Niedrig | ⬜ |
| **P2** | F62 Detection-Confidence-Tuner | Precision/Recall Balance | S | Niedrig | ⬜ |
| **P2** | F69 Export-to-MiSTer-SD | Wachsende MiSTer-Community | M | Niedrig | ⬜ |
| **P2** | F70 Portable-Mode | Flexibilität | S | Niedrig | ⬜ |

---

## D) UI/Flows (Text-Mockups)

### D.1 Confidence-Score-Visualisierung (F02)

```
┌─────────────────────────────────────────────────────────────────┐
│ Ergebnisse                                                      │
├──────┬──────────────────────┬──────────┬──────────┬─────────────┤
│ Conf │ Datei                │ System   │ Ziel     │ Aktion      │
├──────┼──────────────────────┼──────────┼──────────┼─────────────┤
│ 🟢   │ Mario Kart (EUR).sfc │ SNES     │ SNES/... │ Move        │
│ 🟡   │ Unknown Game.bin     │ Genesis? │ Genesis/ │ Move        │
│ 🔴   │ random.dat           │ Unknown  │ Unknown/ │ Skip        │
└──────┴──────────────────────┴──────────┴──────────┴─────────────┘

Legende: 🟢 >95% | 🟡 70-95% | 🔴 <70% oder Unknown
```

**States:**
- Nach Scan: Tabelle gefüllt, Ampeln sichtbar
- Hover über Ampel: Tooltip mit exaktem % und Quelle

**Error UX:**
- Wenn keine Scan-Daten: Empty-State „Führe zuerst einen Scan durch"

---

### D.2 Quick-Override-Dialog (F05)

```
┌─────────────────────────────────────────────────────────────┐
│ Override für: random_game.bin                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Aktuell erkannt: Unknown (0%)                               │
│                                                             │
│ Korrigieren zu:  [▼ System wählen _______________]          │
│                                                             │
│ Kandidaten (ähnliche Namen in DATs):                        │
│ ○ "Random Game (USA)" - Genesis                             │
│ ○ "Random Game (Europe)" - Mega Drive                       │
│ ○ Anderes System eingeben...                                │
│                                                             │
│ [ ] Auch auf ähnliche Dateien anwenden (5 gefunden)         │
│                                                             │
│           [Abbrechen]  [Override speichern]                 │
└─────────────────────────────────────────────────────────────┘
```

**Flow:**
1. Rechtsklick auf Zeile → Kontextmenü → „System überschreiben..."
2. Dialog öffnet
3. System wählen oder Kandidat klicken
4. Optional: „ähnliche Dateien" aktivieren
5. Speichern → Zeile aktualisiert sich, Override-Badge erscheint

---

### D.3 Conflict-Resolver-Dialog (F11)

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ Zielkonflikt erkannt                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Zwei Dateien haben das gleiche Ziel:                        │
│ → SNES/Super Mario World.sfc                                │
│                                                             │
│ ┌──────────────────────────────────────────────────────┐    │
│ │ Datei 1: Super Mario World (USA).sfc                 │    │
│ │ Region: USA | Version: Rev 1 | Größe: 512 KB        │    │
│ │ Confidence: 98%                                      │    │
│ └──────────────────────────────────────────────────────┘    │
│                                                             │
│ ┌──────────────────────────────────────────────────────┐    │
│ │ Datei 2: Super Mario World (Europe).sfc              │    │
│ │ Region: EUR | Version: Rev 0 | Größe: 512 KB        │    │
│ │ Confidence: 97%                                      │    │
│ └──────────────────────────────────────────────────────┘    │
│                                                             │
│ Lösung:                                                     │
│ ○ Datei 1 behalten (Datei 2 → Unknown/)                    │
│ ○ Datei 2 behalten (Datei 1 → Unknown/)                    │
│ ○ Beide behalten mit Suffix (_USA, _EUR)                   │
│ ○ Beide überspringen                                        │
│                                                             │
│ [ ] Diese Entscheidung für alle ähnlichen Konflikte        │
│                                                             │
│              [Abbrechen]  [Anwenden]                        │
└─────────────────────────────────────────────────────────────┘
```

---

### D.4 Folder-Structure-Preview (F19)

```
┌─────────────────────────────────────────────────────────────┐
│ Geplante Zielstruktur                        [🔄] [📋]      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 📁 D:\Sorted-ROMs\                                          │
│ ├── 📁 Nintendo - SNES (23 Dateien, 45 MB)                 │
│ │   ├── Super Mario World.sfc                              │
│ │   ├── Zelda - A Link to the Past.sfc                     │
│ │   └── ... (21 weitere)                                   │
│ ├── 📁 Sega - Genesis (15 Dateien, 32 MB)                  │
│ │   ├── Sonic the Hedgehog.md                              │
│ │   └── ... (14 weitere)                                   │
│ ├── 📁 Sony - PlayStation (8 Dateien, 4.2 GB)              │
│ │   └── ...                                                 │
│ └── 📁 Unknown (12 Dateien, 89 MB)                         │
│     └── ...                                                 │
│                                                             │
│ Gesamt: 58 Dateien | 4.4 GB | 4 Systeme                    │
└─────────────────────────────────────────────────────────────┘
```

**Buttons:**
- 🔄 Refresh (nach Filter-Änderung)
- 📋 Pfadliste kopieren

---

### D.5 Guided-First-Run-Wizard (F37)

```
┌─────────────────────────────────────────────────────────────┐
│ 🎮 Willkommen bei ROM-Sorter-Pro!                           │
│                                                             │
│ Schritt 1 von 4: Quellordner                                │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                             │
│ Wo liegen deine unsortierten ROMs?                          │
│                                                             │
│ [📁 Ordner wählen...]  C:\Users\Max\Downloads\ROMs          │
│                                                             │
│ ℹ️ Wir scannen nur, es wird nichts verändert.               │
│                                                             │
│                                [Zurück]  [Weiter →]         │
└─────────────────────────────────────────────────────────────┘

Schritt 2: Zielordner
Schritt 3: DAT-Quellen (mit „Empfohlene DATs laden"-Button)
Schritt 4: Erster Scan + Vorschau
```

---

### D.6 Dark-Mode-Theme (F47)

```
Farbschema:
- Background: #1E1E2E (Dunkelblau-Grau)
- Surface: #313244 (Etwas heller)
- Primary: #89B4FA (Hellblau)
- Text: #CDD6F4 (Helles Grau)
- Error: #F38BA8 (Rot-Pink)
- Success: #A6E3A1 (Grün)
- Warning: #F9E2AF (Gelb)

Aktivierung:
- Einstellungen → Darstellung → Theme: [Light | Dark | System]
- Shortcut: Ctrl+Shift+T zum Wechseln
```

---

## E) Messbarkeit (Qualitätsmetriken)

### E.1 Detection-Qualität

| Metrik | Beschreibung | Zielwert | Messung |
|--------|--------------|----------|---------|
| **Unknown-Rate** | Anteil nicht erkannter ROMs | < 5% | `count(Unknown) / total_scanned` |
| **False-Positive-Rate** | Falsch zugeordnete ROMs (manuell validiert) | < 1% | Stichproben-Review nach Sortierung |
| **Override-Rate** | Anteil manuell korrigierter Zuordnungen | < 2% | `count(overrides) / total_scanned` |
| **Avg-Confidence** | Durchschnittliche Detection-Confidence | > 90% | `sum(confidence) / total_scanned` |
| **DAT-Coverage** | Anteil Systeme mit geladenen DATs | > 80% | `systems_with_dat / detected_systems` |

### E.2 Performance

| Metrik | Beschreibung | Zielwert | Messung |
|--------|--------------|----------|---------|
| **Scan-Throughput** | Dateien pro Sekunde | > 500 files/s | `files / scan_duration` |
| **Hash-Throughput** | MB pro Sekunde beim Hashen | > 200 MB/s (SSD) | `bytes_hashed / hash_duration` |
| **Cancel-Latency** | Zeit bis Job nach Cancel stoppt | < 500ms | Timestamp-Diff |
| **UI-Responsiveness** | Main-Thread-Blockade | < 50ms | Frame-Drop-Counter |
| **Memory-Peak** | Max RAM während Scan | < 500 MB (100k Dateien) | Process-Monitor |

### E.3 Safety

| Metrik | Beschreibung | Zielwert | Messung |
|--------|--------------|----------|---------|
| **Rollback-Success** | Erfolgreiche Rollbacks | 100% | Automatisierter Test |
| **Conflict-Resolution** | Konflikte ohne Datenverlust gelöst | 100% | E2E-Test |
| **Dry-Run-Writes** | Schreibzugriffe im Preview | 0 | File-System-Monitor |

### E.4 UX

| Metrik | Beschreibung | Zielwert | Messung |
|--------|--------------|----------|---------|
| **First-Task-Completion** | Einsteiger schafft ersten Sort | > 90% | Usability-Test |
| **Time-to-First-Sort** | Zeit von Start bis Execute | < 5 min | Session-Timer |
| **Error-Dialog-Rate** | Anteil Sessions mit Fehler-Dialog | < 10% | Log-Analyse |

### E.5 Telemetry (lokal, datenschutzfreundlich)

Alle Metriken werden **nur lokal** gespeichert (`cache/metrics.json`):

```json
{
  "session_id": "uuid-local-only",
  "scans": [
    {
      "timestamp": "2026-01-30T10:00:00",
      "files_scanned": 1523,
      "unknown_count": 45,
      "avg_confidence": 0.92,
      "duration_ms": 3200
    }
  ],
  "executes": [
    {
      "timestamp": "2026-01-30T10:05:00",
      "files_moved": 1478,
      "conflicts_resolved": 3,
      "rollback_used": false
    }
  ]
}
```

**Opt-in Report:** Button in Einstellungen „Anonyme Statistik exportieren" für Bug-Reports.

---

## F) Markdown-Backlog mit Checkboxen

### Top 15 (Priorisiert) – Status 2026-01-31

#### P0 – Kritisch für Release-Qualität ✅ COMPLETE
- [x] **F02** Confidence-Score-Visualisierung – Ampel/Prozent in Ergebnistabelle
- [x] **F05** Quick-Override-Dialog – Rechtsklick → System überschreiben
- [x] **F26** Full-Rollback-System (UI) – Button „Letzte Sortierung rückgängig"
- [x] **F28** Disk-Space-Check – Warnung vor Execute wenn Platz fehlt
- [x] **F40** Empty-State-Guidance – Leere Tabelle zeigt Handlungsanweisung

#### P1 – Wichtig für User Experience ✅ COMPLETE
- [x] **F11** Conflict-Resolver-Dialog – Dialog bei Zielkonflikten
- [x] **F16** Plan-Diff-View – Vergleich alter/neuer Plan
- [x] **F19** Folder-Structure-Preview – Baum-Ansicht der Zielstruktur
- [x] **F32** Incremental-Scan – Nur geänderte Dateien scannen
- [x] **F37** Guided-First-Run-Wizard – Einsteiger-Assistent
- [x] **F47** Dark-Mode-Theme – Vollständiger Dark-Mode

#### P2 – Nice-to-have für Power-User ✅ COMPLETE
- [x] **F03** Hash-Cross-Check – Multi-DAT-Validierung
- [x] **F06** Bulk-Override-Wizard – Mehrfach-Override
- [x] **F22** Partial-Execute – Nur ausgewählte Zeilen ausführen
- [x] **F50** Console-Badges/Icons – System-Icons in Tabelle

---

### Nächste Iteration (F61-F70) – Neue Features ✅ COMPLETE

#### High Value / Low Effort ✅ COMPLETE
- [x] **F62** Detection-Confidence-Tuner – Globaler Slider für Mindest-Confidence → `src/config/confidence_tuner.py`
- [x] **F66** Collection-Completeness-Tracker – X% komplett pro System → `src/analytics/completeness_tracker.py`
- [x] **F70** Portable-Mode – Config relativ zum Programm für USB-Stick → `src/config/portable_mode.py`

#### Medium Effort / High Value ✅ COMPLETE
- [x] **F69** Export-to-MiSTer-SD – MiSTer-FPGA-Ordnerformat → `src/exports/mister_exporter.py`
- [x] **F61** Smart-Queue-Priority-Reordering – Drag-and-Drop Queue-Verwaltung → `src/core/queue_manager.py`
- [x] **F65** Watchfolder-Auto-Sort – Automatische Sortierung bei neuen Dateien → `src/core/watchfolder.py`

#### Nice-to-have (später)
- [ ] **F63** Multi-Library-Workspace – Mehrere Sammlungen parallel
- [ ] **F64** AI-Assisted-Name-Normalizer – LLM-basierte Namenskorrektur (optional)
- [ ] **F67** Screenshot-/Boxart-Preview – Visuelle Identifikation
- [ ] **F68** Gamification-Progress-Badges – Meilenstein-Badges

---

### Weitere Features (nach Kategorie) – MVP Status

#### Detection Accuracy ✅ COMPLETE
- [x] **F01** Why-Unknown-Analyzer Enhanced
- [x] **F04** Heuristik-Pipeline-Visualizer
- [x] **F07** Detection-Rule-Tester
- [x] **F08** Fingerprint-Erweiterung (Magic Bytes)
- [x] **F09** DAT-Coverage-Report
- [x] **F10** Fuzzy-Name-Matching
- [x] **F12** Preferred-Region-Chain
- [x] **F13** Bad-Dump-Marker
- [x] **F14** Revision/Version-Comparator
- [x] **F15** Learning-Override-Suggestions

#### Sorting / Planning ✅ COMPLETE
- [x] **F17** Plan-Export (JSON/CSV)
- [x] **F18** Plan-Template-System
- [x] **F20** Rename-Pattern-Builder
- [x] **F21** Copy-First-Staging (Safe Mode)
- [x] **F23** Action-Override-per-Item
- [x] **F24** Estimated-Time-Display
- [x] **F25** Plan-History (Undo-Stack)

#### Safety / Security ✅ COMPLETE
- [x] **F27** Pre-Execute-Checksum-Validation
- [x] **F29** Review-Gate-Enhancement
- [x] **F30** Symlink-Detection-Warning
- [x] **F31** Backup-Before-Overwrite

#### Performance ✅ COMPLETE
- [x] **F33** Parallel-Hashing
- [x] **F34** Index-Sharding
- [x] **F35** Lazy-Archive-Extraction
- [x] **F36** Background-Index-Update

#### UX ✅ COMPLETE
- [x] **F38** Contextual-Help-Tooltips
- [x] **F39** Status-Bar-Summary
- [x] **F41** Keyboard-Shortcuts-Overlay
- [x] **F42** Compact-Mode
- [x] **F43** Pro-Mode-Toggle
- [x] **F44** Recent-Paths-Dropdown
- [x] **F45** Action-Undo-Toast
- [x] **F46** Log-Search-and-Filter Enhanced

#### Visual / Themes ✅ COMPLETE
- [x] **F48** Retro/CRT-Theme
- [x] **F49** Accent-Color-Picker
- [x] **F51** Layout-Presets
- [x] **F52** High-Contrast-Mode

#### Integrations ✅ COMPLETE
- [x] **F53** EmulationStation-Gamelist-Export Enhanced
- [x] **F54** LaunchBox-Import-Export
- [x] **F55** RetroArch-Playlist-Generator
- [x] **F56** CLI-Batch-Mode

#### Data / DB ✅ COMPLETE
- [x] **F57** DAT-Auto-Updater
- [x] **F58** Custom-DAT-Builder
- [x] **F59** Hash-Cache-Inspector
- [x] **F60** Database-Integrity-Check

---

### Neue Feature-Kategorien (F71-F95) – v1.1+ Backlog

#### ROM-Verifizierung & Audit (HIGH PRIORITY) ✅ COMPLETE
- [x] **F71** Bad-Dump-Scanner – Erkennt [b], [!], [o], [h] Flags → `src/verification/rom_verifier.py`
- [x] **F72** Intro/Trainer-Erkennung – Findet [t], [f], [a], [p] modifizierte ROMs → `src/verification/rom_verifier.py`
- [x] **F73** Overdump-Erkennung – Größer als DAT-Eintrag → `src/verification/rom_verifier.py`
- [x] **F74** ROM-Integritäts-Report – Vollständiger Audit pro System → `src/verification/integrity_report.py`

#### Duplikat-Management (HIGH PRIORITY) ✅ COMPLETE
- [x] **F75** Hash-Duplikat-Finder – Identische Dateien finden → `src/duplicates/hash_duplicate_finder.py`
- [x] **F76** Fuzzy-Duplikat-Finder – Rev A vs Rev B, Regionen → `src/duplicates/fuzzy_duplicate_finder.py`
- [x] **F77** Duplikat-Merge-Wizard – Intelligentes Zusammenführen → `src/duplicates/merge_wizard.py`
- [x] **F78** Parent/Clone-Verwaltung – MAME-Style Beziehungen → `src/duplicates/parent_clone.py`

#### Patch-Management (MEDIUM PRIORITY) ✅ COMPLETE
- [x] **F79** IPS/BPS/UPS-Patcher – Patches direkt anwenden → `src/patching/patcher.py`
- [x] **F80** Patch-Bibliothek-Manager – Patches pro ROM verwalten → `src/patching/patch_library.py`
- [x] **F81** Auto-Patch-Matching – Passende Patches finden → `src/patching/auto_matcher.py`
- [x] **F82** Soft-Patching-Support – Patch zur Laufzeit → `src/patching/soft_patcher.py`

#### Emulator-Integration (MEDIUM PRIORITY) ✅ COMPLETE
- [x] **F83** ROM-Direkt-Start – Doppelklick → Emulator → `src/emulator/emulator_launcher.py`
- [x] **F84** Core-Zuordnung – RetroArch-Core pro System → `src/emulator/core_mapping.py`
- [x] **F85** Save-State-Manager – Speicherstände organisieren → `src/emulator/save_state_manager.py`
- [x] **F86** Per-Game-Settings – Individuelle Einstellungen → `src/emulator/game_settings.py`

#### Hardware-Exporte (HIGH PRIORITY) ✅ COMPLETE
- [x] **F87** Flash-Cart-Export – EverDrive/SD2SNES Format → `src/exports/flash_cart_exporter.py`
- [x] **F88** Analogue-Pocket-Export – OpenFPGA Format → `src/exports/analogue_pocket_exporter.py`
- [x] **F89** Batocera/RetroPie-Export – Bootfähige SD-Struktur → `src/exports/batocera_exporter.py`
- [x] **F90** Steam-ROM-Manager – ROMs zu Steam hinzufügen → `src/exports/steam_rom_manager.py`

#### Collection-Analytics & Backup (MEDIUM PRIORITY) ✅ COMPLETE
- [x] **F91** Sammlungs-Dashboard – Statistiken & Diagramme → `src/analytics/collection_dashboard.py`
- [x] **F92** Wunschlisten-Manager – Fehlende ROMs tracken → `src/analytics/wishlist_manager.py`
- [x] **F93** Timeline-View – ROMs nach Release-Jahr → `src/analytics/timeline_view.py`
- [x] **F94** Inkrementelles Backup – Nur geänderte sichern → `src/backup/incremental_backup.py`
- [x] **F95** Cloud-Sync-Support – OneDrive/Dropbox/NAS → `src/backup/cloud_sync.py`

---

## G) UI-Mockups für neue Features

### G.1 Collection-Completeness-Tracker (F66)

```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Sammlungs-Fortschritt                     [🔄 Refresh]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Nintendo - SNES                                             │
│ ████████████████████░░░░░░░░░░░░  67% (1.542 / 2.300)      │
│ [Fehlende anzeigen]                                         │
│                                                             │
│ Sega - Genesis                                              │
│ ██████████████████████████████░░  89% (1.870 / 2.100)      │
│ [Fehlende anzeigen]                                         │
│                                                             │
│ Sony - PlayStation                                          │
│ ████████░░░░░░░░░░░░░░░░░░░░░░░░  23% (680 / 2.900)        │
│ [Fehlende anzeigen]                                         │
│                                                             │
│ Nintendo - NES                                              │
│ ██████████████████████████████░░  92% (1.150 / 1.250)      │
│ [Fehlende anzeigen]                                         │
│                                                             │
│ ─────────────────────────────────────────────────────────── │
│ Gesamt: 5.242 ROMs | 4 Systeme | Durchschnitt: 68%         │
└─────────────────────────────────────────────────────────────┘
```

**Dialog "Fehlende anzeigen":**
```
┌─────────────────────────────────────────────────────────────┐
│ Fehlende ROMs: Nintendo - SNES (758)                        │
├─────────────────────────────────────────────────────────────┤
│ 🔍 [Suchen...________________________]  [📋 Liste kopieren] │
│                                                             │
│ [ ] Chrono Trigger (USA)                                    │
│ [ ] Earthbound (USA)                                        │
│ [ ] Final Fantasy VI (USA)                                  │
│ [ ] Secret of Mana (Europe)                                 │
│ ... (754 weitere)                                           │
│                                                             │
│              [Schließen]  [Als Wunschliste exportieren]     │
└─────────────────────────────────────────────────────────────┘
```

---

### G.2 Detection-Confidence-Tuner (F62)

```
┌─────────────────────────────────────────────────────────────┐
│ ⚙️ Erkennungs-Einstellungen                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Mindest-Confidence für Zuordnung:                           │
│                                                             │
│ Vorsichtig ◀━━━━━━━━━━━●━━━━━━━━━▶ Aggressiv                │
│              50%      [85%]      99%                        │
│                                                             │
│ ℹ️ Dateien unter 85% werden als "Unknown" markiert.         │
│                                                             │
│ Vorschau mit aktueller Einstellung:                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Erkannt: 1.423 (94%) | Unknown: 89 (6%)                │ │
│ │ Bei 70%: Erkannt: 1.498 (99%) | Unknown: 14 (1%)       │ │
│ │ Bei 95%: Erkannt: 1.201 (80%) | Unknown: 311 (20%)     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│                 [Abbrechen]  [Übernehmen]                   │
└─────────────────────────────────────────────────────────────┘
```

---

### G.3 MiSTer-Export (F69)

```
┌─────────────────────────────────────────────────────────────┐
│ 🎮 Export für MiSTer FPGA                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Ziel-SD-Karte / Ordner:                                     │
│ [📁 E:\]  [Wählen...]                                       │
│                                                             │
│ Core-Mapping:                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ SNES     → games/SNES/              ✅ 23 ROMs         │ │
│ │ Genesis  → games/Genesis/           ✅ 15 ROMs         │ │
│ │ NES      → games/NES/               ✅ 8 ROMs          │ │
│ │ PSX      → games/PSX/ (CHD only)    ⚠️ 2 von 8 kompatibel│ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Optionen:                                                   │
│ [x] Ordnerstruktur nach MiSTer-Standard                     │
│ [x] Nicht-kompatible Formate überspringen                   │
│ [ ] Bestehende Dateien überschreiben                        │
│                                                             │
│ ⚠️ 6 PSX-ROMs sind nicht im CHD-Format (nicht kompatibel)   │
│                                                             │
│              [Abbrechen]  [Export starten (46 ROMs)]        │
└─────────────────────────────────────────────────────────────┘
```

---

### G.4 Portable-Mode (F70)

```
┌─────────────────────────────────────────────────────────────┐
│ ⚙️ Portable-Modus                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ○ Standard-Modus (AppData)                                  │
│   Config: C:\Users\Max\AppData\Local\ROM-Sorter-Pro\       │
│                                                             │
│ ● Portable-Modus (neben Programm)                           │
│   Config: D:\USB\ROM-Sorter-Pro\config\                     │
│   Cache:  D:\USB\ROM-Sorter-Pro\cache\                      │
│   Logs:   D:\USB\ROM-Sorter-Pro\logs\                       │
│                                                             │
│ ℹ️ Im Portable-Modus werden alle Daten relativ zum          │
│   Programmverzeichnis gespeichert. Ideal für USB-Sticks.   │
│                                                             │
│ [ ] Bestehende Einstellungen migrieren                      │
│                                                             │
│                 [Abbrechen]  [Aktivieren]                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Assumptions

1. **DAT-Index-SQLite ist performant genug** für Multi-DAT-Lookups (F03) – falls nicht, Index-Sharding (F34) priorisieren.
2. **Theme-Manager existiert** und unterstützt CSS/QSS-basierte Themes – Dark-Mode (F47) nutzt diesen.
3. **Override-YAML-System ist stabil** – Quick-Override (F05) schreibt in `config/identify_overrides.yaml`.
4. **Rollback-Controller speichert Move-Manifeste** – Full-Rollback-UI (F26) liest diese.
5. **Qt ist primäres Backend** – alle UI-Mockups sind Qt-first, Tk erhält Subset.
6. **Keine Netzwerk-Features im MVP-Core** – DAT-Auto-Updater (F57) ist optional und darf fehlen.
7. **Einsteiger sind Hauptzielgruppe für UX-Features** – Pro-Mode (F43) versteckt Komplexität.
8. **Retro-Ästhetik ist erwünscht** – CRT-Theme (F48) ist Fun-Feature, keine Priorität.
9. **MiSTer-Community wächst** – Export-Feature (F69) hat hohes Nutzerpotenzial.
10. **Portable-Modus ist Standard bei Tools** – Kein komplexer Installer nötig.

---

## H) Release-Zusammenfassung

### MVP Status: ✅ FEATURE-COMPLETE

**60 von 60 MVP-Features implementiert:**
- Detection Accuracy: 15/15 ✅
- Sorting/Planning: 10/10 ✅
- Safety/Security: 6/6 ✅
- Performance: 5/5 ✅
- UX: 10/10 ✅
- Visual/Themes: 6/6 ✅
- Integrations: 4/4 ✅
- Data/DB: 4/4 ✅

### Nächste Iteration (v1.1) – Empfohlene Features

#### Tier 1: Quick Wins (Low Effort / High Value)
| Feature | Beschreibung | Aufwand |
|---------|--------------|---------|
| **F71** Bad-Dump-Scanner | Qualitätskontrolle | S |
| **F75** Hash-Duplikat-Finder | Speicher sparen | S |
| **F83** ROM-Direkt-Start | Quick-Test-Workflow | S |
| **F70** Portable-Mode | USB-Stick-Support | S |

#### Tier 2: High Impact (Medium Effort)
| Feature | Beschreibung | Aufwand |
|---------|--------------|---------|
| **F79** IPS/BPS-Patcher | Fan-Translation-Community | M |
| **F87** Flash-Cart-Export | EverDrive/SD2SNES | M |
| **F69** MiSTer-Export | FPGA-Community | M |
| **F66** Collection-Completeness | Sammler-Motivation | M |
| **F91** Sammlungs-Dashboard | Übersicht & Eye-Candy | M |
| **F88** Analogue-Pocket-Export | Wachsende Community | M |

#### Tier 3: Nice-to-have (v1.2+)
| Feature | Beschreibung | Aufwand |
|---------|--------------|---------|
| **F77** Duplikat-Merge-Wizard | Aufgeräumte Sammlung | M |
| **F90** Steam-ROM-Manager | Steam Deck | M |
| **F92** Wunschlisten-Manager | Sammler-Ziele | S |
| **F94** Inkrementelles Backup | Schnelle Backups | M |

### Langfristig (v2.0)
- Multi-Library-Workspace (F63)
- Watchfolder-Auto-Sort (F65)
- Save-State-Manager (F85)
- AI-Assisted Features (F64) – nur wenn klar nützlich
- Cloud-Sync (F95) – Privacy-Bedenken abwägen

---

## I) Feature-Übersicht nach Kategorie (95 Features)

| Kategorie | MVP (F01-F60) | v1.1 (F61-F70) | v1.2+ (F71-F95) | Gesamt |
|-----------|---------------|----------------|-----------------|--------|
| Detection Accuracy | 15 ✅ | 2 | 4 | 21 |
| Sorting/Planning | 10 ✅ | 2 | 1 | 13 |
| Safety/Security | 6 ✅ | 1 | 1 | 8 |
| Performance | 5 ✅ | 1 | 0 | 6 |
| UX | 10 ✅ | 2 | 0 | 12 |
| Visual/Themes | 6 ✅ | 1 | 1 | 8 |
| Integrations | 4 ✅ | 2 | 8 | 14 |
| Data/DB | 4 ✅ | 1 | 5 | 10 |
| **Gesamt** | **60** | **12** | **20** | **92** |
