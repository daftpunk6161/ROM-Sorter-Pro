# ROM Sorter Pro - Hauptdokumentation

**Version:** 2.1.8 | **Stand:** 21.08.2025

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Installation](#installation)
3. [Konfiguration](#konfiguration)
4. [Konsolen-Unterstützung](#konsolen-unterstützung)
5. [Architektur](#architektur)
6. [Entwicklung](#entwicklung)
7. [Fehlerbehebung](#fehlerbehebung)
8. [Aktuelle Updates](#aktuelle-updates)

## Übersicht

ROM Sorter Pro ist ein leistungsstarkes Tool zum automatischen Erkennen, Sortieren und Organisieren von ROM-Dateien für verschiedene Spielkonsolen. Die Software kann große ROM-Sammlungen analysieren und nach Konsole, Region und anderen Kriterien sortieren.

### Hauptfunktionen

- Automatische Erkennung von über 30 Konsolenformaten
- Intelligente Entdeckung von Duplikaten und Varianten
- Mehrsprachige Unterstützung
- Drag-and-Drop-Oberfläche
- Detaillierte Metadaten-Extraktion
- Archiv-Unterstützung (ZIP, RAR, 7z)
- Einfache Benutzeroberfläche mit fortgeschrittenen Optionen

## Installation

### Systemanforderungen

- **Betriebssystem:** Windows, macOS oder Linux
- **Python:** Version 3.8 oder höher
- **RAM:** Mindestens 2GB, 4GB empfohlen für große Sammlungen
- **Festplattenspeicher:** 100MB für die Anwendung, zusätzlicher Speicher für ROM-Datenbanken

### Installationsschritte

1. Repository klonen oder ZIP-Datei herunterladen
2. Abhängigkeiten installieren:

   ```bash
   python install_dependencies.py
   ```

3. Anwendung starten:

   ```bash
   python start_rom_sorter.py
   ```

Alternativ können Sie auch die Batch-Datei (`start_rom_sorter.bat`) oder das Shell-Skript (`start_rom_sorter.sh`) verwenden.

## Konfiguration

Die Konfiguration erfolgt über mehrere Mechanismen:

1. **Konfigurationsdatei:** `src/config.json` enthält alle Einstellungen
2. **GUI-Einstellungen:** Über das Einstellungsmenü in der Benutzeroberfläche
3. **Kommandozeilenoptionen:** Für fortgeschrittene Benutzer und Automatisierung

### Wichtige Konfigurationsoptionen

- **Konsolenerkennung:** Aktivierung/Deaktivierung spezifischer Konsolen
- **Leistungsoptimierung:** Arbeitsspeicher- und CPU-Nutzung anpassen
- **Sortierungsoptionen:** Ordnerstruktur und Dateinamenformate
- **Regionpriorisierung:** Bevorzugte ROM-Regionen (US, EU, JP, etc.)

Siehe [Konfigurationsdokumentation](topics/konfiguration.md) für Details.

## Konsolen-Unterstützung

ROM Sorter Pro unterstützt eine breite Palette von Konsolen:

| Konsole | Unterstützte Erweiterungen | Erkennung |
|---------|---------------------------|-----------|
| Nintendo Entertainment System | .nes, .zip | ✅ Vollständig |
| Super Nintendo | .sfc, .smc, .zip | ✅ Vollständig |
| Nintendo 64 | .n64, .z64, .v64, .zip | ✅ Vollständig |
| GameBoy / GameBoy Color | .gb, .gbc, .zip | ✅ Vollständig |
| GameBoy Advance | .gba, .zip | ✅ Vollständig |
| Nintendo DS | .nds, .zip | ✅ Vollständig |
| Nintendo 3DS | .3ds, .cia | ✅ Vollständig |
| GameCube | .iso, .gcm, .zip | ✅ Vollständig |
| Wii | .iso, .wbfs | ✅ Vollständig |
| Sega Master System | .sms, .zip | ✅ Vollständig |
| Sega Mega Drive / Genesis | .md, .gen, .bin, .zip | ✅ Vollständig |
| Sega Saturn | .iso, .bin, .zip | ✅ Vollständig |
| Sega Dreamcast | .gdi, .cdi, .chd | ✅ Vollständig |
| PlayStation | .bin, .iso, .img, .chd | ✅ Vollständig |
| PlayStation 2 | .iso, .bin, .chd | ✅ Vollständig |
| PlayStation Portable | .iso, .cso | ✅ Vollständig |
| Atari 2600 | .a26, .bin | ✅ Vollständig |
| Atari 5200 | .a52, .bin | ✅ Vollständig |
| NEC PC-Engine / TurboGrafx-16 | .pce, .sgx | ✅ Vollständig |
| Neo Geo | .neo, .zip | ✅ Vollständig |

Siehe [CONSOLE_MAPPING.md](CONSOLE_MAPPING.md) für eine vollständige Liste.

## Architektur

ROM Sorter Pro verwendet eine modulare Architektur mit klarer Trennung von Zuständigkeiten:

```ascii
rom-sorter-pro/
│
├── src/                          # Hauptquellcode
│   ├── config/                   # Konfigurationsmanagement
│   ├── core/                     # Kernfunktionalität (Dateioperationen, ROM-Modelle)
│   ├── detectors/                # ROM-Erkennungsmodule
│   ├── ui/                       # Benutzeroberfläche
│   └── utils/                    # Hilfsfunktionen
│
├── data/                         # Anwendungsdaten
│   └── rom_databases/            # ROM-Datenbanken
│
├── dev/                          # Entwicklungsressourcen
│   ├── tools/                    # Entwicklungswerkzeuge
│   ├── scripts/                  # Hilfsskripte
│   └── tests/                    # Testdateien
```

### Core-Module

Die `core`-Komponenten bilden die Grundlage der Anwendung:

- **file_utils.py**: Sichere Dateioperationen und Hashberechnung
- **rom_models.py**: Datenmodelle für ROM-Metadaten
- **rom_utils.py**: ROM-spezifische Hilfsfunktionen und Erweiterungserkennung

### Datenfluss

1. **Erkennung:** ROM-Dateien werden gescannt und analysiert
2. **Klassifizierung:** Identifizierung von Konsole, Region, etc.
3. **Verarbeitung:** Entscheidung über Ordnerstruktur und Namensgebung
4. **Organisation:** Verschieben oder Kopieren von Dateien in die Zielstruktur

## Entwicklung

### Entwicklungsumgebung einrichten

1. Klonen des Repositories:

   ```bash
   git clone https://github.com/daftpunk6161/ROM-Sorter-Pro.git
   ```

2. Einrichten der Python-Umgebung:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate.bat  # Windows
   ```

3. Installieren der Entwicklungsabhängigkeiten:

   ```bash
   pip install -r requirements-dev.txt
   ```

### Qualitätssicherung

Das Projekt verwendet die folgenden Tools zur Qualitätssicherung:

- **repo_guard.py:** Codequalitätsprüfung und Konsistenzüberprüfung
- **translate_comments.py:** Übersetzung von Kommentaren ins Englische
- **cleanup_project.py:** Bereinigung temporärer und Backup-Dateien

Vor dem Commit oder Release sollte Folgendes ausgeführt werden:

```bash
python dev/tools/repo_guard.py all
python dev/tools/translate_comments.py
python dev/scripts/cleanup_project.py
```

## Fehlerbehebung

### Häufige Probleme

#### Anwendung startet nicht

- Überprüfen Sie, ob Python 3.8+ installiert ist
- Überprüfen Sie die Abhängigkeiten mit `pip list`
- Prüfen Sie die Logs unter `logs/rom_sorter_startup.log`

#### ROM-Erkennung ungenau

- Aktualisieren Sie die ROM-Datenbanken
- Erhöhen Sie den `confidence_threshold` in den Einstellungen
- Prüfen Sie den konsolenspezifischen Log für Details

#### Leistungsprobleme bei großen Sammlungen

- Reduzieren Sie `batch_size` in der Konfiguration
- Aktivieren Sie `lazy_loading` für großes ROM-Sammlungen
- Erhöhen Sie `cache_size` bei ausreichendem RAM

Weitere Informationen finden Sie in den [Detaillierten Anleitungen](topics/troubleshooting.md).

## Aktuelle Updates

Folgende neue Dokumentationen wurden hinzugefügt:

- [Architektur-Update 2025](topics/architektur_update.md): Überblick der neuesten Architekturänderungen
- [UI-System](topics/ui_system.md): Details zum überarbeiteten UI-System
- [Konfigurationsupdate 2025](topics/konfiguration_update.md): Änderungen am Konfigurationssystem

Diese neuen Dokumente beschreiben die Änderungen und Verbesserungen, die im August 2025 implementiert wurden, um die Anwendung stabiler und wartbarer zu machen.
