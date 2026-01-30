# ROM-Sorter-Pro – Feature-Backlog & Produkt-Roadmap

> **Erstellt:** 2026-01-30  
> **Scope:** GUI-first Desktop-Tool (Qt/Tk-Fallback)  
> **Fokus:** Stabilität, Detection Accuracy, Power-User Workflows

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
- **MVP-Fit:** Ja (bereits implementiert, Erweiterung)
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
- **MVP-Fit:** Nein (Nice-to-have)
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
- **MVP-Fit:** Nein
- **Test-Idee:** Bekannte Muster eingeben, erwartete Matches prüfen

#### F08: Fingerprint-Erweiterung (Magic Bytes)
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Zusätzliche Header-Signatur-Prüfung für Formate ohne eindeutige Extension
- **User Value:** Weniger False Positives bei generischen Extensions (.bin, .rom)
- **Komplexität:** M
- **Risiko:** Mittel (False-Positive-Gefahr bei schlechten Signaturen)
- **Abhängigkeiten:** Detector-Base
- **MVP-Fit:** Ja
- **Test-Idee:** .bin-Dateien mit verschiedenen Headers, prüfen ob korrekt erkannt

#### F09: DAT-Coverage-Report
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Zeigt welche Systeme durch geladene DATs abgedeckt sind und wo Lücken sind
- **User Value:** User weiß, welche DATs noch fehlen
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** DAT-Index
- **MVP-Fit:** Ja
- **Test-Idee:** Index mit 3 DATs, Report zeigt exakt 3 Systeme

#### F10: Fuzzy-Name-Matching
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Findet ähnliche Einträge in DAT wenn exakter Hash fehlt (Levenshtein/Token-Match)
- **User Value:** Bessere Kandidaten-Vorschläge bei Unknown
- **Komplexität:** M
- **Risiko:** Mittel (Performance, False-Positive-Gefahr)
- **Abhängigkeiten:** DAT-Index
- **MVP-Fit:** Nein
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
- **MVP-Fit:** Ja (existiert, UI-Verbesserung)
- **Test-Idee:** 3 ROMs (EUR/USA/JPN), nur EUR soll im Plan sein

#### F13: Bad-Dump-Marker
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** ROMs die in DAT als [b] (bad dump) markiert sind, visuell kennzeichnen
- **User Value:** User weiß, welche ROMs problematisch sind
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** DAT-Parser muss [b]-Flag extrahieren
- **MVP-Fit:** Ja
- **Test-Idee:** ROM mit [b] im DAT, Icon/Badge muss erscheinen

#### F14: Revision/Version-Comparator
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Bei mehreren Revisionen (v1.0, v1.1, Rev A) die neueste priorisieren
- **User Value:** Automatisch beste Version behalten
- **Komplexität:** M
- **Risiko:** Mittel (Parsing-Edge-Cases)
- **Abhängigkeiten:** Naming-Helpers
- **MVP-Fit:** Ja
- **Test-Idee:** 3 ROMs mit v1.0/v1.1/v1.2, nur v1.2 im Plan

#### F15: Learning-Override-Suggestions
- **Kategorie:** Reliability / Detection Accuracy
- **Kurzbeschreibung:** Wenn User Override setzt, ähnliche Dateien vorschlagen („Diese 5 auch?")
- **User Value:** Schnellere Korrektur bei Pattern-basierten Fehlern
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** F05, Pattern-Matching
- **MVP-Fit:** Nein
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
- **MVP-Fit:** Ja
- **Test-Idee:** Export, Reimport, Daten identisch

#### F18: Plan-Template-System
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Wiederverwendbare Sortier-Templates (z.B. „Retro-Konsolen", „Handhelds", „Arcade")
- **User Value:** Schneller Wechsel zwischen Sortier-Strategien
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Config-System
- **MVP-Fit:** Ja (Presets existieren, Erweiterung)
- **Test-Idee:** Template speichern, laden, Einstellungen identisch

#### F19: Folder-Structure-Preview (Tree)
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Zeigt geplante Zielstruktur als Baum-Ansicht
- **User Value:** Visuell klar, wie das Ergebnis aussehen wird
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Plan-Model
- **MVP-Fit:** Ja
- **Test-Idee:** Plan mit 3 Systemen, Baum zeigt 3 Hauptordner

#### F20: Rename-Pattern-Builder
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Visueller Editor für Dateinamens-Pattern ({title} - {region}.{ext})
- **User Value:** Keine Syntax-Fehler, sofortige Vorschau
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Naming-Helpers
- **MVP-Fit:** Ja
- **Test-Idee:** Pattern eingeben, Preview für Beispiel-ROM prüfen

#### F21: Copy-First-Staging (Safe Mode)
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Kopiert erst in Staging-Ordner, dann atomic move ins Ziel
- **User Value:** Rollback bei Fehler trivial
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Execute-Helpers
- **MVP-Fit:** Ja (IGIR hat Copy-first, generalisieren)
- **Test-Idee:** Execute mit Fehler in der Mitte, Staging muss aufräumbar sein

#### F22: Partial-Execute (Selected Only)
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Nur ausgewählte Zeilen aus dem Plan ausführen
- **User Value:** Schrittweise Sortierung, Kontrolle
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Plan-Selection-State
- **MVP-Fit:** Ja
- **Test-Idee:** 10 Items, 3 selektiert, nur 3 werden ausgeführt

#### F23: Action-Override-per-Item
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Pro ROM-Zeile: Action ändern (Move/Copy/Skip) ohne globale Einstellung
- **User Value:** Granulare Kontrolle
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Plan-Model
- **MVP-Fit:** Ja
- **Test-Idee:** 3 Items, unterschiedliche Actions, Execute prüft alle

#### F24: Estimated-Time-Display
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Zeigt geschätzte Dauer basierend auf Dateigröße und IO-Speed
- **User Value:** Erwartungsmanagement bei großen Libraries
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Performance-Metrics
- **MVP-Fit:** Nein
- **Test-Idee:** Plan mit 10 GB, Schätzung plausibel (±30%)

#### F25: Plan-History (Undo-Stack)
- **Kategorie:** Sorting / Planning / Preview
- **Kurzbeschreibung:** Letzte 5 Pläne im Speicher, Undo/Redo möglich
- **User Value:** Versehentliche Änderungen rückgängig machen
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Plan-State-Management
- **MVP-Fit:** Nein
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
- **MVP-Fit:** Ja
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
- **MVP-Fit:** Ja
- **Test-Idee:** Plan mit 2000 Dateien, Review-Dialog erscheint

#### F30: Symlink-Detection-Warning
- **Kategorie:** Safety / Security
- **Kurzbeschreibung:** Warnung wenn Quelle/Ziel Symlinks enthält
- **User Value:** Verhindert unbeabsichtigte Traversals
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Security-Helpers (existiert)
- **MVP-Fit:** Ja
- **Test-Idee:** Ordner mit Symlink als Quelle, Warnung erscheint

#### F31: Backup-Before-Overwrite
- **Kategorie:** Safety / Security
- **Kurzbeschreibung:** Bei Konflikt mit existierender Datei: automatisches Backup anlegen
- **User Value:** Keine Datenverluste
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Backup-Controller
- **MVP-Fit:** Ja
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
- **MVP-Fit:** Ja
- **Test-Idee:** Export, XML valide, Pfade korrekt

#### F54: LaunchBox-Import-Export
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Bidirektionaler Sync mit LaunchBox-DB
- **User Value:** Keine doppelte Pflege
- **Komplexität:** L
- **Risiko:** Mittel
- **Abhängigkeiten:** LaunchBox-XML-Schema
- **MVP-Fit:** Nein
- **Test-Idee:** Export, Import in LaunchBox, ROMs erscheinen

#### F55: RetroArch-Playlist-Generator
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Generiert .lpl-Dateien für RetroArch
- **User Value:** Schneller Einstieg in RetroArch
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Plan-Model
- **MVP-Fit:** Ja
- **Test-Idee:** Export, .lpl valide JSON, Pfade korrekt

#### F56: CLI-Batch-Mode
- **Kategorie:** Integrations / Frontends
- **Kurzbeschreibung:** Headless-Modus für Scripting (scan → plan → execute ohne GUI)
- **User Value:** Automatisierung, CI-Integration
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** Controller-API
- **MVP-Fit:** Ja
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
- **MVP-Fit:** Ja
- **Test-Idee:** Mock-Server mit neuer DAT, Update wird erkannt

#### F58: Custom-DAT-Builder
- **Kategorie:** Data / DB / DAT Management
- **Kurzbeschreibung:** Eigene DATs aus Scan-Ergebnissen erstellen
- **User Value:** Eigene Sammlungen dokumentieren
- **Komplexität:** M
- **Risiko:** Niedrig
- **Abhängigkeiten:** DAT-Writer
- **MVP-Fit:** Nein
- **Test-Idee:** Scan, DAT exportieren, DAT valide

#### F59: Hash-Cache-Inspector
- **Kategorie:** Data / DB / DAT Management
- **Kurzbeschreibung:** UI zum Anzeigen/Löschen von Cache-Einträgen
- **User Value:** Debugging, Cache-Kontrolle
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** Hash-Cache
- **MVP-Fit:** Ja
- **Test-Idee:** Cache mit 100 Einträgen, UI zeigt alle, Löschen funktioniert

#### F60: Database-Integrity-Check
- **Kategorie:** Data / DB / DAT Management
- **Kurzbeschreibung:** SQLite-VACUUM + Integrity-Check mit UI-Feedback
- **User Value:** Datenbank-Pflege
- **Komplexität:** S
- **Risiko:** Niedrig
- **Abhängigkeiten:** DB-Manager
- **MVP-Fit:** Ja
- **Test-Idee:** Korrupte DB erkennen, Warnung anzeigen

---

## C) Top 15 Roadmap (Priorisiert)

| Prio | Feature | Warum jetzt? | Aufwand | Risiko | Abhängigkeiten |
|------|---------|--------------|---------|--------|----------------|
| **P0** | F02 Confidence-Score-Visualisierung | Sofort sichtbar, welche Ergebnisse unsicher sind → weniger False Positives | S | Niedrig | Keine |
| **P0** | F05 Quick-Override-Dialog | Schnelle Korrektur = zufriedene User, weniger Frust | S | Niedrig | Override-System ✓ |
| **P0** | F26 Full-Rollback-System (UI) | Sicherheitsnetz für alle Aktionen → Vertrauen | M | Mittel | Rollback-Controller ✓ |
| **P0** | F28 Disk-Space-Check | Verhindert Abbrüche mitten im Kopieren | S | Niedrig | Keine |
| **P0** | F40 Empty-State-Guidance | Einsteiger-Onboarding dramatisch verbessert | S | Niedrig | Keine |
| **P1** | F11 Conflict-Resolver-Dialog | Keine versehentlichen Überschreibungen | M | Niedrig | Plan-Validation |
| **P1** | F16 Plan-Diff-View | Nachvollziehbarkeit bei Re-Scans | M | Niedrig | Plan-Serialisierung |
| **P1** | F19 Folder-Structure-Preview | Visuelle Klarheit vor Execute | M | Niedrig | Keine |
| **P1** | F32 Incremental-Scan | Performance-Boost für Power-User | M | Mittel | Hash-Cache ✓ |
| **P1** | F37 Guided-First-Run-Wizard | Einsteiger-Erlebnis entscheidend für Retention | M | Niedrig | Keine |
| **P1** | F47 Dark-Mode-Theme | Stark nachgefragt, Standard bei modernen Apps | M | Niedrig | Theme-Manager ✓ |
| **P2** | F03 Hash-Cross-Check | Detection-Qualität verbessern | M | Mittel | DAT-Index ✓ |
| **P2** | F06 Bulk-Override-Wizard | Zeitersparnis bei vielen Korrekturen | S | Niedrig | F05 |
| **P2** | F22 Partial-Execute | Granulare Kontrolle für Power-User | S | Niedrig | Keine |
| **P2** | F50 Console-Badges/Icons | Visuelle Aufwertung, schnellere Orientierung | S | Niedrig | Asset-Bundle |

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

### Top 15 (Priorisiert)

#### P0 – Kritisch für Release-Qualität
- [x] **F02** Confidence-Score-Visualisierung – Ampel/Prozent in Ergebnistabelle
- [x] **F05** Quick-Override-Dialog – Rechtsklick → System überschreiben
- [x] **F26** Full-Rollback-System (UI) – Button „Letzte Sortierung rückgängig"
- [x] **F28** Disk-Space-Check – Warnung vor Execute wenn Platz fehlt
- [x] **F40** Empty-State-Guidance – Leere Tabelle zeigt Handlungsanweisung

#### P1 – Wichtig für User Experience
- [ ] **F11** Conflict-Resolver-Dialog – Dialog bei Zielkonflikten
- [ ] **F16** Plan-Diff-View – Vergleich alter/neuer Plan
- [ ] **F19** Folder-Structure-Preview – Baum-Ansicht der Zielstruktur
- [ ] **F32** Incremental-Scan – Nur geänderte Dateien scannen
- [ ] **F37** Guided-First-Run-Wizard – Einsteiger-Assistent
- [ ] **F47** Dark-Mode-Theme – Vollständiger Dark-Mode

#### P2 – Nice-to-have für Power-User
- [ ] **F03** Hash-Cross-Check – Multi-DAT-Validierung
- [ ] **F06** Bulk-Override-Wizard – Mehrfach-Override
- [ ] **F22** Partial-Execute – Nur ausgewählte Zeilen ausführen
- [ ] **F50** Console-Badges/Icons – System-Icons in Tabelle

---

### Weitere Features (nach Kategorie)

#### Detection Accuracy
- [ ] **F01** Why-Unknown-Analyzer Enhanced
- [ ] **F04** Heuristik-Pipeline-Visualizer
- [ ] **F07** Detection-Rule-Tester
- [ ] **F08** Fingerprint-Erweiterung (Magic Bytes)
- [ ] **F09** DAT-Coverage-Report
- [ ] **F10** Fuzzy-Name-Matching
- [ ] **F12** Preferred-Region-Chain
- [ ] **F13** Bad-Dump-Marker
- [ ] **F14** Revision/Version-Comparator
- [ ] **F15** Learning-Override-Suggestions

#### Sorting / Planning
- [ ] **F17** Plan-Export (JSON/CSV)
- [ ] **F18** Plan-Template-System
- [ ] **F20** Rename-Pattern-Builder
- [ ] **F21** Copy-First-Staging (Safe Mode)
- [ ] **F23** Action-Override-per-Item
- [ ] **F24** Estimated-Time-Display
- [ ] **F25** Plan-History (Undo-Stack)

#### Safety / Security
- [ ] **F27** Pre-Execute-Checksum-Validation
- [ ] **F29** Review-Gate-Enhancement
- [ ] **F30** Symlink-Detection-Warning
- [ ] **F31** Backup-Before-Overwrite

#### Performance
- [ ] **F33** Parallel-Hashing
- [ ] **F34** Index-Sharding
- [ ] **F35** Lazy-Archive-Extraction
- [ ] **F36** Background-Index-Update

#### UX
- [ ] **F38** Contextual-Help-Tooltips
- [ ] **F39** Status-Bar-Summary
- [ ] **F41** Keyboard-Shortcuts-Overlay
- [ ] **F42** Compact-Mode
- [ ] **F43** Pro-Mode-Toggle
- [ ] **F44** Recent-Paths-Dropdown
- [ ] **F45** Action-Undo-Toast
- [ ] **F46** Log-Search-and-Filter Enhanced

#### Visual / Themes
- [ ] **F48** Retro/CRT-Theme
- [ ] **F49** Accent-Color-Picker
- [ ] **F51** Layout-Presets
- [ ] **F52** High-Contrast-Mode

#### Integrations
- [ ] **F53** EmulationStation-Gamelist-Export Enhanced
- [ ] **F54** LaunchBox-Import-Export
- [ ] **F55** RetroArch-Playlist-Generator
- [ ] **F56** CLI-Batch-Mode

#### Data / DB
- [ ] **F57** DAT-Auto-Updater
- [ ] **F58** Custom-DAT-Builder
- [ ] **F59** Hash-Cache-Inspector
- [ ] **F60** Database-Integrity-Check

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
