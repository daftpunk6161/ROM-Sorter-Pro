# ROM-Sorter Pro - Konsolen-Mapping

## Übersicht

ROM-Sorter Pro verfügt über ein umfassendes Dateiendungs-zu-Konsolen-Mapping-System, das ROM-Dateien automatisch erkennen und kategorisieren kann. Dieses System wird im Modul `src/ui/console_mappings.py` implementiert.

## Wichtige Änderungen

Das Mapping-System wurde überarbeitet, um doppelte Dateiendungen zu eliminieren und eine intelligente Erkennung für mehrdeutige Dateiendungen zu implementieren.

### Betroffene Dateiendungen

Die folgenden mehrdeutigen Dateiendungen wurden identifiziert und korrigiert:

1. `.cso` - Kann zu PlayStation_2 oder PlayStation_Portable gehören
2. `.bin` - Kann zu PlayStation oder Atari_2600 gehören
3. `.chd` - Kann zu PlayStation_2 oder Sega_Dreamcast gehören
4. `.sgx` - Kann zu PC_Engine oder SuperGrafx gehören
5. `.dsk` - Kann zu Apple_II, ZX_Spectrum oder Amstrad_CPC gehören

### Lösungsansatz

Für mehrdeutige Endungen haben wir eine intelligente Erkennung implementiert, die:

1. Die Dateiendung in eine Prioritätsliste von möglichen Konsolen umwandelt
2. Den Dateiinhalt oder Dateinamen auf konsolen-spezifische Marker analysiert
3. Die wahrscheinlichste Konsole basierend auf der Analyse zurückgibt

## Verwendung

Die Hauptfunktion für die Konsolenerkennung ist `get_console_for_extension(ext, file_content=None, filename=None)`:

```python
from src.ui.console_mappings import get_console_for_extension

# Einfache Erkennung basierend auf Dateiendung
console = get_console_for_extension('.nes')  # Gibt 'Nintendo_NES' zurück

# Erkennung für mehrdeutige Endungen
# Hier wird für PlayStation vs. Atari entschieden
console = get_console_for_extension('.bin', file_content=file_bytes, filename="Crash_Bandicoot.bin")
# Würde 'PlayStation' zurückgeben, da der Dateiname auf PlayStation hinweist

# Für Archive kann der Inhalt analysiert werden
console = get_console_for_extension('.zip', file_content=zip_file_listing)
```

## Wartung

Bei der Aktualisierung des Konsolen-Mappings beachten Sie bitte:

1. Fügen Sie neue Konsolen-Zuordnungen in die `CONSOLE_MAP` in `console_mappings.py` ein
2. Wenn eine Dateiendung zu mehreren Konsolen gehören kann, fügen Sie sie zu `EXTENSION_PRIORITY_MAP` mit geeigneten Erkennungshinweisen hinzu
3. Halten Sie die Erkennungshinweise aktuell, um die Genauigkeit der Erkennung zu verbessern

## Architektur

Die Konsolen-Mapping-Funktionalität ist in zwei Hauptkomponenten organisiert:

1. **CONSOLE_MAP**: Ein einfaches Dictionary, das Dateierweiterungen direkt auf Konsolennamen abbildet. Dies ist für eindeutige Zuordnungen.

2. **EXTENSION_PRIORITY_MAP**: Ein erweitertes Dictionary für mehrdeutige Dateierweiterungen, die zu mehreren Konsolen gehören können. Jeder Eintrag enthält:
   - `priority`: Eine Liste von möglichen Konsolen in der Reihenfolge ihrer Wahrscheinlichkeit
   - `detection_hints`: Schlüsselwörter für jede Konsole, die helfen, den tatsächlichen Konsolentyp aus dem Dateiinhalt oder Dateinamen zu erkennen

Die Funktion `get_console_for_extension()` implementiert die Logik zur Auswahl der richtigen Konsole basierend auf den verfügbaren Daten.

## Tests

Die Konsolen-Mapping-Funktionalität wurde umfassend getestet, um sicherzustellen, dass:

1. Eindeutige Dateierweiterungen korrekt zugeordnet werden
2. Mehrdeutige Dateierweiterungen standardmäßig auf die Konsole mit der höchsten Priorität zugeordnet werden
3. Bei Vorhandensein von Inhalts- oder Datenamenshinweisen eine intelligente Zuordnung erfolgt

Die Tests können mit dem Skript `test_direct_console_mappings.py` ausgeführt werden, das unitests für alle diese Szenarien enthält.
