# ROM-Sorter-Pro v2.1.7

Ein universelles Tool zum Organisieren und Sortieren von ROM-Dateien für verschiedene Spielkonsolen.

## 🚀 Schnellstart

### Startoptionen
- **GUI-Version**: `python start_rom_sorter.py` oder `start_rom_sorter.bat`
- **Vereinfachte Version**: `python simple_rom_sorter.py`
- **Installation**: `python install_dependencies.py`

### Systemanforderungen
- Python 3.8+
- Windows, macOS oder Linux
- Mindestens 2GB RAM
- 100MB freier Festplattenspeicher

## 📁 Projektstruktur

```
rom-sorter-pro/
│
├── 📦 src/                          # Hauptquellcode
│   ├── cli/                         # Kommandozeilen-Interface
│   ├── config/                      # Konfigurationsmanagement
│   ├── core/                        # Kern-Funktionalität
│   ├── database/                    # Datenbankintegration
│   ├── detectors/                   # ROM-Erkennungsmodule
│   ├── reporting/                   # Berichterstattung
│   ├── scanning/                    # ROM-Scanmodule
│   ├── security/                    # Sicherheitsfunktionen
│   ├── ui/                          # Benutzeroberflächen
│   ├── utils/                       # Hilfsfunktionen
│   └── web/                         # Webschnittstelle
│
├── 🔧 dev/                          # Entwicklungsressourcen (nicht im Release)
│   ├── tools/                       # Entwicklungswerkzeuge
│   │   ├── repo_guard.py           # Code-Qualitätsprüfung
│   │   ├── translate_comments.py   # Kommentarübersetzung
│   │   └── ...
│   ├── scripts/                     # Hilfsskripte
│   │   ├── cleanup_project.py      # Projektbereinigung
│   │   └── ...
│   ├── tests/                       # Testdateien
│   │   ├── test_console_*.py       # Konsolen-Tests
│   │   └── ...
│   ├── docs/                        # Entwicklerdokumentation
│   └── backups/                     # Backup-Dateien
│
├── 📊 data/                         # Anwendungsdaten
│   └── rom_databases/               # ROM-Datenbanken
│
├── 📚 docs/                         # Benutzerdokumentation
│   ├── CHANGELOG.md                 # Änderungsprotokoll
│   ├── CONSOLE_MAPPING.md           # Konsolen-Zuordnungen
│   └── ROADMAP.md                   # Entwicklungsplan
│
├── 📦 dist/                         # Distributionspakete
├── 📝 logs/                         # Logdateien
└── 🗂️ temp/                         # Temporäre Dateien
```

## 🎮 Unterstützte Konsolen

- Nintendo (NES, SNES, N64, GameCube, Wii, Switch)
- Sony (PlayStation 1-5, PSP, PS Vita)
- Microsoft (Xbox, Xbox 360, Xbox One, Xbox Series)
- Sega (Genesis, Saturn, Dreamcast)
- Atari (2600, 7800, Lynx, Jaguar)
- Und viele mehr...

## ⚙️ Features

- 🔍 **Automatische ROM-Erkennung** mit KI-Unterstützung
- 📂 **Intelligente Ordnerstruktur** nach Konsolen sortiert
- 🎨 **Moderne GUI** mit Drag & Drop-Funktionalität
- 🌐 **Web-Interface** für Fernzugriff
- 🔒 **Sicherheitsvalidierung** aller ROM-Dateien
- 📊 **Detaillierte Berichte** über Ihre Sammlung
- 🚀 **Hochleistungsscanning** großer Sammlungen

## 🛠️ Entwicklung

### Für Entwickler
Alle Entwicklungstools befinden sich im `dev/` Verzeichnis:

```bash
# Code-Qualität prüfen
python dev/tools/repo_guard.py all

# Kommentare übersetzen
python dev/tools/translate_comments.py

# Tests ausführen
python dev/tests/test_console_integration.py
```

### Projektstruktur-Richtlinien
- **Produktionscode**: Nur in `src/` Verzeichnis
- **Entwicklungstools**: In `dev/tools/`
- **Tests**: In `dev/tests/`
- **Dokumentation**: Benutzer in `docs/`, Entwickler in `dev/docs/`
- **Neue Dateien**: Direkt in passende Unterverzeichnisse

## 📋 Changelog

Siehe [CHANGELOG.md](docs/CHANGELOG.md) für detaillierte Änderungen.

## 📄 Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe LICENSE-Datei für Details.

## 🤝 Beitragen

1. Repository forken
2. Feature-Branch erstellen (`git checkout -b feature/AmazingFeature`)
3. Änderungen committen (`git commit -m 'Add AmazingFeature'`)
4. Branch pushen (`git push origin feature/AmazingFeature`)
5. Pull Request erstellen

## 📞 Support

Bei Fragen oder Problemen:
- 📧 E-Mail: support@rom-sorter-pro.de
- 🐛 Issues: GitHub Issues verwenden
- 📚 Dokumentation: `docs/` Verzeichnis

---

**ROM-Sorter-Pro v2.1.7** - Organisieren Sie Ihre ROM-Sammlung professionell! 🎮✨
