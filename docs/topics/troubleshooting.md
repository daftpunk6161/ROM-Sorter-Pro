# Fehlerbehebung für ROM Sorter Pro

Diese Anleitung hilft bei der Lösung häufiger Probleme mit ROM Sorter Pro.

## Diagnosewerkzeuge

ROM Sorter Pro bietet verschiedene Diagnosewerkzeuge:

### Log-Dateien

Die wichtigsten Log-Dateien befinden sich im `logs/` Verzeichnis:

- `rom_sorter.log`: Allgemeines Anwendungslog
- `rom_sorter_startup.log`: Log des Startvorgangs
- `rom_sorter_errors.log`: Fehlerprotokoll
- `rom_sorter_YYYYMMDD.log`: Tägliche Logs

Verwenden Sie diese Dateien als ersten Schritt bei der Fehlersuche.

### Debug-Modus

Aktivieren Sie den Debug-Modus für detailliertere Logs:

1. Öffnen Sie `src/config.json`
2. Ändern Sie in der `logging`-Sektion:

   ```json
   "log_level": "DEBUG"
   ```

3. Starten Sie die Anwendung neu

## Häufige Probleme und Lösungen

### Anwendung startet nicht

#### Symptome

- Schwarzes Fenster blinkt kurz auf und verschwindet
- Fehlermeldung "Python wurde nicht gefunden"
- GUI öffnet sich nicht

#### Lösungen

1. **Python-Installation überprüfen**

   ```bash
   python --version
   ```

   Stellen Sie sicher, dass Python 3.8 oder höher angezeigt wird.

2. **Abhängigkeiten überprüfen**

   ```bash
   pip list
   ```

   Vergleichen Sie die installierten Pakete mit `requirements.txt`.

3. **Virtuelle Umgebung aktivieren**

   ```bash
   # Windows
   .venv\Scripts\activate.bat

   # Linux/macOS
   source .venv/bin/activate
   ```

4. **Abhängigkeiten neu installieren**

   ```bash
   python install_dependencies.py
   ```

### ROM-Erkennung ist ungenau

#### Symptome

- ROMs werden falsch kategorisiert
- Viele "Unknown"-ROMs
- Falsche Konsolen werden erkannt

#### Lösungen

1. **ROM-Datenbanken aktualisieren**

   ```bash
   python start_rom_sorter.py --update-db
   ```

2. **Erkennungsparameter anpassen**
   Erhöhen Sie den `confidence_threshold` in den Einstellungen auf 0.9 oder höher.

3. **Dateinamen verbessern**
   Stellen Sie sicher, dass ROM-Dateinamen standardisierte Informationen enthalten:
   - Spieltitel
   - Region in Klammern, z.B. (USA), (Europe)
   - Versionsnummer falls vorhanden

4. **Manuelle Mapping-Datei erstellen**
   Erstellen Sie eine benutzerdefinierte Mapping-Datei unter `data/custom_mappings.json`.

### Leistungsprobleme bei großen Sammlungen

#### Symptome

- Langsame Verarbeitung
- Hohe CPU-Auslastung
- Speicherprobleme (out of memory)

#### Lösungen

1. **Batch-Größe reduzieren**
   Ändern Sie `batch_size` in den Leistungseinstellungen auf 100-200.

2. **Parallele Verarbeitung optimieren**
   Setzen Sie `parallel_workers` auf einen Wert, der kleiner ist als die Anzahl der CPU-Kerne.

3. **Lazy Loading aktivieren**
   Aktivieren Sie `lazy_loading` in den Leistungseinstellungen.

4. **Cache-Größe optimieren**
   - Bei mehr als 8GB RAM: Erhöhen Sie `cache_size` auf 10000
   - Bei weniger als 4GB RAM: Verringern Sie `cache_size` auf 2000

5. **Archive optimieren**
   Verwenden Sie ZIP-Archive anstelle von 7z oder RAR für bessere Leistung.

### GUI-Probleme

#### Symptome

- Fehlende Elemente in der Benutzeroberfläche
- Abstürze beim Öffnen bestimmter Dialoge
- Drag & Drop funktioniert nicht

#### Lösungen

1. **GUI-Toolkit überprüfen**

   ```bash
   pip install --upgrade tkinter
   pip install --upgrade pillow
   ```

2. **Cache löschen**
   Löschen Sie den Inhalt des `cache/` Verzeichnisses.

3. **Theme-Probleme beheben**
   Wechseln Sie zum Standard-Theme in den Einstellungen.

4. **DND-Integration überprüfen**

   ```bash
   pip install --upgrade tkinterdnd2
   ```

## Backup und Wiederherstellung

### Konfiguration sichern

Sichern Sie Ihre Konfiguration regelmäßig:

```bash
cp src/config.json backups/config_backup_$(date +%Y%m%d).json
```

### Anwendung zurücksetzen

Bei schwerwiegenden Problemen können Sie die Anwendung zurücksetzen:

1. Konfigurationsdateien sichern
2. Cache und temporäre Dateien löschen:

   ```bash
   python dev/scripts/cleanup_project.py --deep-clean
   ```

3. Anwendung neu installieren:

   ```bash
   python install_dependencies.py
   ```

## Support und Community-Hilfe

Wenn Sie weitere Hilfe benötigen:

1. Überprüfen Sie die [GitHub Issues](https://github.com/daftpunk6161/ROM-Sorter-Pro/issues)
2. Erstellen Sie eine detaillierte Fehlerbeschreibung mit Log-Dateien
3. Kontaktieren Sie den Support unter <support@romsorter.example.com>
