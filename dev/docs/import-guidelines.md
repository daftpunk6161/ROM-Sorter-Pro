# Import-Struktur Standardisierung für ROM Sorter Pro

## Übersicht

Dieses Dokument definiert die standardisierte Import-Struktur für das ROM Sorter Pro-Projekt. Die Einhaltung dieser Standards verbessert die Lesbarkeit des Codes, reduziert potenzielle Importfehler und erleichtert die Wartbarkeit.

## Grundsätze

1. **Konsequente Gruppierung**: Importe werden in logische Gruppen unterteilt
2. **Klare Hierarchie**: Standardbibliotheken vor Drittanbieterbibliotheken vor eigenen Modulen
3. **Vermeidung von zirkulären Abhängigkeiten**: Keine gegenseitigen Imports zwischen Modulen
4. **Keine dynamischen Imports**: Imports gehören an den Anfang der Datei, nicht in Funktionen
5. **Einfachheit über Cleverness**: Bevorzugung von expliziten, klaren Imports

## Standard-Import-Struktur

Jede Python-Datei sollte die folgenden Import-Gruppen in der angegebenen Reihenfolge enthalten:

```python
# Gruppe 1: Standard-Bibliotheken
import os
import sys
import logging
# weitere Standard-Bibliotheken...

# Gruppe 2: Drittanbieterbibliotheken (z.B. PyQt5, numpy, etc.)
import numpy as np
from PyQt5 import QtCore

# Gruppe 3: Projektspezifische absolute Imports
from src.core.file_utils import create_directory_if_not_exists
from src.database.rom_database import ROMDatabase

# Gruppe 4: Relative Imports (nur innerhalb des gleichen Pakets)
from .theme_manager import ThemeManager
```

## Spezifische Regeln

### Absolute vs. Relative Imports

- **Absolute Imports** (`from src.utils import x`) für:
  - Moduleübergreifende Imports (z.B. zwischen verschiedenen Paketen)
  - Top-Level-Module

- **Relative Imports** (`from .submodule import x`) für:
  - Importe innerhalb desselben Pakets
  - Eng verwandte Funktionalitäten

### Dynamische Imports vermeiden

Folgendes sollte vermieden werden:

```python
def some_function():
    # FALSCH: Import gehört an den Anfang der Datei
    from src.database.console_db import get_console_for_extension
    # ...
```

Stattdessen:

```python
# RICHTIG: Import am Anfang der Datei
from src.database.console_db import get_console_for_extension

def some_function():
    # Verwende die importierte Funktion
    # ...
```

### Import-Aliase

Import-Aliase sollten sparsam und nur bei Namenskonflikten oder für standardisierte Abkürzungen verwendet werden:

```python
# Akzeptable Verwendung von Aliasing
import numpy as np
from src.utils.performance_enhanced import PerformanceMonitor as perf_mon
```

### Wildcard-Imports vermeiden

Verwende keine Wildcard-Imports (`from module import *`), da diese die Lesbarkeit verschlechtern und zu unerwarteten Namenskonflikten führen können.

## Implementierungsschritte

Bei der Standardisierung der Import-Struktur in bestehenden Dateien:

1. **Gruppieren** der Imports nach dem oben beschriebenen Schema
2. **Entfernen** von ungenutzten oder doppelten Imports
3. **Ersetzen** von dynamischen Imports innerhalb von Funktionen
4. **Vereinheitlichen** der Import-Stile (absolute/relative) gemäß den Regeln

## Beispiele

### Vorher (problematisch)

```python
import os
from src.ui.theme_manager import ThemeManager
import sys, logging
from pathlib import Path
import threading
# Füge das Hauptverzeichnis des Projekts zum Python-Suchpfad hinzu
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def process_file(filename):
    from src.database.console_db import get_console_for_extension  # Problematisch
```

### Nachher (standardisiert)

```python
# Standard-Bibliotheken
import os
import sys
import logging
import threading
from pathlib import Path

# Projektspezifische Importe
from src.database.console_db import get_console_for_extension
from src.ui.theme_manager import ThemeManager

def process_file(filename):
    # Verwendet die bereits importierte Funktion
    console = get_console_for_extension(filename)
```

## Abschließende Hinweise

- Import-Optimierung sollte schrittweise erfolgen, beginnend mit den am häufigsten verwendeten Modulen
- Nach jeder Änderung Tests durchführen, um sicherzustellen, dass keine Funktionalität beeinträchtigt wurde
- Bei Unsicherheit im konkreten Fall, immer Lesbarkeit und Wartbarkeit priorisieren
