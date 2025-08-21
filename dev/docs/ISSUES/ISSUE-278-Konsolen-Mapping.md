# QA-Testplan: Konsolen-Mapping-Update

## Übersicht

Dieses Issue beschreibt die Änderungen und erforderlichen Tests für das aktualisierte Konsolen-Mapping-System in ROM Sorter Pro. Die Änderungen zielen darauf ab, Probleme mit doppelten Schlüsseln zu beheben und die Erkennung von mehrdeutigen Dateierweiterungen zu verbessern.

## Änderungen

1. **Neue Dateistruktur**:
   - Neue Datei: `src/ui/console_mappings.py` enthält alle Konsolen-Mappings
   - Entfernung des `CONSOLE_MAP` aus `src/ui/gui.py`

2. **Intelligente Erkennung**:
   - Neue Funktion `get_console_for_extension()` für die Konsolenidentifizierung
   - Unterstützung für Inhalts- und Dateinamenanalyse zur präzisen Erkennung

3. **Korrigierte Probleme**:
   - Doppelte Schlüssel für `.cso`, `.bin`, `.chd`, `.sgx` und `.dsk`
   - Verbesserte Erkennung für Dateien, die zu verschiedenen Konsolen gehören können

## Testplan

### Grundlegend

- [ ] Importieren aller Konsolen-Mappings `from src.ui.console_mappings import CONSOLE_MAP, get_console_for_extension`
- [ ] Testen der grundlegenden Zuordnungen für eindeutige Erweiterungen (z.B. `.nes`, `.gba`)

### Mehrdeutige Erweiterungen

- [ ] `.bin`: Testen mit PlayStation- und Atari 2600-Dateien, bestätigen korrekte Erkennung
- [ ] `.cso`: Testen mit PlayStation 2- und PSP-Dateien, bestätigen korrekte Erkennung
- [ ] `.chd`: Testen mit PlayStation 2- und Dreamcast-Dateien
- [ ] `.sgx`: Testen mit PC Engine- und SuperGrafx-Dateien
- [ ] `.dsk`: Testen mit Apple II-, ZX Spectrum- und Amstrad CPC-Dateien

### Inhaltserkennung

- [ ] Testen der Funktion `get_console_for_extension()` mit verschiedenen Dateinamen und Inhalten
- [ ] Verifizieren, dass die Erkennungshinweise wie erwartet funktionieren

### Integrationstests

- [ ] Überprüfen, ob die GUI-Anwendung weiterhin korrekt funktioniert
- [ ] Testen der ROM-Sortierung mit mehrdeutigen Dateierweiterungen
- [ ] Verifizieren, dass die Konsolenerkennung bei der ROM-Organisation korrekt funktioniert

## Sonderhinweise

Bei Problemen mit der Erkennung können die Erkennungshinweise in `EXTENSION_PRIORITY_MAP` erweitert werden. Die Dokumentation zu den Änderungen findet sich in `docs/CONSOLE_MAPPING.md`.

## Definition of Done

- [ ] Alle Tests bestanden
- [ ] Keine Fehler bei der Erkennung von ROMs für verschiedene Konsolen
- [ ] Dokumentation vollständig und aktuell
- [ ] Code in Feature-Branch und bereit für Merge
