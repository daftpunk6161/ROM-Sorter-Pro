# ROM Sorter Pro - Konfigurationsdokumentation

Diese Dokumentation erläutert die verschiedenen Konfigurationsoptionen von ROM Sorter Pro und wie sie angepasst werden können.

## Konfigurationsdatei

Die Hauptkonfigurationsdatei befindet sich unter `src/config.json`. Sie ist im JSON-Format strukturiert und enthält folgende Hauptabschnitte:

### Metadaten

```json
"_metadata": {
    "version": "2.1.8",
    "description": "ROM Sorter Pro - Optimized Configuration",
    "last_updated": "2025-08-21T10:00:00",
    "encoding": "utf-8",
    "config_version": 2,
    "template": "optimized",
    "consolidated": true
}
```

Diese Sektion enthält Informationen über die Konfiguration selbst und sollte nicht manuell bearbeitet werden.

### Dateierkennung

```json
"file_detection": {
    "rom_extensions": [
        ".zip", ".7z", ".rar", ".chd", ".iso", ".bin", ".cue",
        ".gb", ".gbc", ".gba", ".nes", ".snes", ".smc", ".n64"
    ],
    "unwanted_patterns": [
        "\\b(japan|jp|jap)\\b",
        "\\b(demo|beta|alpha|sample)\\b",
        "\\b(hack|hacked|pirate)\\b"
    ],
    "priority_extensions": {
        ".zip": 10, ".7z": 9, ".iso": 8, ".bin": 7, ".rom": 6
    }
}
```

- **rom_extensions**: Liste der Dateierweiterungen, die als ROMs erkannt werden sollen
- **unwanted_patterns**: Reguläre Ausdrücke für unerwünschte ROM-Varianten
- **priority_extensions**: Priorität von Dateitypen bei mehreren Varianten eines ROMs

### Priorisierung

```json
"prioritization": {
    "region_priorities": {
        "World": 10, "Europe": 9, "EU": 9, "USA": 7, "US": 7,
        "Japan": 3, "JP": 3, "Other": 1
    },
    "language_priorities": {
        "EN": 10, "DE": 9, "Multi": 8, "FR": 7, "Other": 1
    }
}
```

- **region_priorities**: Priorisierung von ROM-Regionen (höhere Werte = höhere Priorität)
- **language_priorities**: Priorisierung von ROM-Sprachen

### Leistung

```json
"performance": {
    "caching": {
        "enable_caching": true,
        "cache_size": 5000,
        "lru_cache_size": 3000
    },
    "processing": {
        "parallel_workers": null,
        "batch_size": 300,
        "max_memory_usage": "1GB"
    },
    "optimization": {
        "use_fast_hash": true,
        "enable_progress_batching": true,
        "lazy_loading": true
    }
}
```

- **caching**: Einstellungen für Zwischenspeicherung
  - **enable_caching**: Aktiviert/deaktiviert das Caching
  - **cache_size**: Maximale Anzahl von Einträgen im Cache
  - **lru_cache_size**: Größe des LRU-Caches für Funktionsaufrufe
- **processing**: Verarbeitungseinstellungen
  - **parallel_workers**: Anzahl der parallelen Verarbeitungsthreads (null = automatisch)
  - **batch_size**: Größe der Verarbeitungsbatches
  - **max_memory_usage**: Maximale Speichernutzung
- **optimization**: Weitere Optimierungseinstellungen
  - **use_fast_hash**: Schnelleren Hashalgorithmus verwenden
  - **enable_progress_batching**: Fortschrittsanzeige optimieren
  - **lazy_loading**: Daten nur bei Bedarf laden

### Features

```json
"features": {
    "sorting": {
        "console_sorting_enabled": true,
        "create_console_folders": true
    },
    "duplicate_detection": {
        "enabled": true,
        "smart_detection": true
    },
    "ai_features": {
        "enable_ai_detection": false,
        "confidence_threshold": 0.85
    }
}
```

- **sorting**: Sortierungseinstellungen
  - **console_sorting_enabled**: Aktiviert/deaktiviert die konsolenbasierte Sortierung
  - **create_console_folders**: Erstellt Ordner für jede Konsole
- **duplicate_detection**: Einstellungen zur Duplikaterkennung
  - **enabled**: Aktiviert/deaktiviert die Duplikaterkennung
  - **smart_detection**: Aktiviert erweiterte Erkennung von Duplikaten
- **ai_features**: KI-basierte Erkennungsfeatures
  - **enable_ai_detection**: Aktiviert/deaktiviert KI-Erkennung
  - **confidence_threshold**: Minimaler Konfidenzwert für KI-Erkennung (0.0-1.0)

### Sicherheit

```json
"security": {
    "validate_paths": true,
    "allowed_base_dirs": [],
    "safe_mode": true
}
```

- **validate_paths**: Aktiviert/deaktiviert die Pfadvalidierung
- **allowed_base_dirs**: Zusätzlich erlaubte Basisverzeichnisse
- **safe_mode**: Aktiviert/deaktiviert den abgesicherten Modus

## Konfiguration über die GUI

Die meisten Konfigurationsoptionen können auch über die grafische Benutzeroberfläche eingestellt werden:

1. Starten Sie ROM Sorter Pro
2. Klicken Sie auf "Einstellungen" in der oberen Menüleiste
3. Navigieren Sie durch die Registerkarten für verschiedene Einstellungskategorien

## Kommandozeilen-Konfiguration

ROM Sorter Pro unterstützt auch Konfiguration über Kommandozeilenparameter:

```bash
python start_rom_sorter.py --config=custom_config.json --workers=4 --batch-size=500
```

Verwenden Sie `python start_rom_sorter.py --help` für eine vollständige Liste der Optionen.
