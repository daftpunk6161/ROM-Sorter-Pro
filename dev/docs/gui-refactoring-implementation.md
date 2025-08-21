# GUI-Refactoring: Implementierungsleitfaden

Dieser Leitfaden bietet konkrete Schritte und Beispiele für die Implementierung des GUI-Refactorings.

## Vorgehensweise

### Schritt 1: Vorbereitung des Projekts

```bash
# Erstellen eines neuen Feature-Branches für das Refactoring
git checkout -b feature/gui-refactoring

# Sicherstellen, dass alle Tests bestehen
python -m unittest discover tests
```

### Schritt 2: Erstellen der neuen Modulstruktur

```bash
# Erstellen der neuen Moduldateien
touch src/ui/gui_core.py
touch src/ui/gui_components.py
touch src/ui/gui_handlers.py
touch src/ui/gui_scanner.py
touch src/ui/gui_dnd.py
```

### Schritt 3: Extrahieren der Komponenten

Folgen Sie diesen Schritten für jedes Modul:

1. Identifizieren Sie die zu extrahierenden Klassen und Funktionen
2. Kopieren Sie den relevanten Code in die neue Datei
3. Passen Sie die Imports in der neuen Datei an
4. Ersetzen Sie den Code in `gui.py` durch Imports aus der neuen Datei
5. Testen Sie die Funktionalität nach jeder Extraktion

## Detaillierte Implementierungsbeispiele

### 1. gui_components.py

Diese Datei enthält wiederverwendbare UI-Komponenten:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - GUI-Komponenten

Wiederverwendbare UI-Komponenten für die ROM Sorter Pro-Anwendung.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import gc
import weakref
from typing import Dict, List, Optional, Any, Callable

class MemoryEfficientProgressBar(ttk.Progressbar):
    """Eine speichereffiziente Progressbar-Implementierung."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_update = 0
        self._update_interval = kwargs.get('update_interval', 250)  # ms

    def smart_update(self, value):
        """Aktualisiert die Progressbar nur wenn nötig."""
        import time
        current_time = time.time() * 1000

        if current_time - self._last_update > self._update_interval:
            self['value'] = value
            self.update_idletasks()
            self._last_update = current_time

class OptimizedDragDropFrame(tk.Frame):
    """Ein optimierter Frame für Drag-and-Drop-Operationen."""

    def __init__(self, parent, drop_callback=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.drop_callback = drop_callback

        # Registriere DnD-Events
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self._on_drop)

    def _on_drop(self, event):
        """Verarbeitet Drop-Events."""
        if self.drop_callback:
            self.drop_callback(event.data)

class EfficientLogWidget(tk.Frame):
    """Ein speichereffizientes Log-Widget."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.log_text = scrolledtext.ScrolledText(self, wrap=tk.WORD)
        self.log_text.pack(expand=True, fill=tk.BOTH)

        # Begrenzte Anzahl an Zeilen für Speichereffizienz
        self.max_lines = kwargs.get('max_lines', 1000)
        self.lines_count = 0

    def log(self, message):
        """Fügt eine Nachricht zum Log hinzu."""
        self.log_text.configure(state=tk.NORMAL)

        if self.lines_count >= self.max_lines:
            # Entferne die ältesten Zeilen
            self.log_text.delete(1.0, 2.0)
        else:
            self.lines_count += 1

        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

class OptimizedStatsWidget(tk.Frame):
    """Widget zur Anzeige von Statistiken."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.stats = {}
        self._create_widgets()

    def _create_widgets(self):
        """Erstellt die UI-Elemente."""
        self.tree = ttk.Treeview(self, columns=('value'), show='headings')
        self.tree.heading('value', text='Wert')

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def update_stats(self, stats_dict):
        """Aktualisiert die angezeigten Statistiken."""
        # Lösche alte Einträge
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Füge neue Einträge hinzu
        for key, value in stats_dict.items():
            self.tree.insert('', tk.END, text=key, values=(value,))
```

### 2. gui_dnd.py

Diese Datei enthält die Drag-and-Drop-Funktionalität:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - Drag-and-Drop-Funktionalität

Implementierung der Drag-and-Drop-Funktionalität für die ROM Sorter Pro-Anwendung.
"""

import tkinter as tk
from typing import Callable, List, Optional
import os
import sys

# DnD-Konstanten
DND_FILES = 'DND_FILES'

class DragDropManager:
    """Manager für die Drag-and-Drop-Funktionalität."""

    def __init__(self, gui_instance):
        self.gui = gui_instance
        self._setup_dnd()

    def _setup_dnd(self):
        """Richtet die Drag-and-Drop-Funktionalität ein."""
        # Registriere den Drop-Frame
        self.gui.drop_frame.drop_target_register(DND_FILES)
        self.gui.drop_frame.dnd_bind('<<Drop>>', self._on_drop)

    def _on_drop(self, event):
        """Verarbeitet Drop-Events."""
        data = event.data

        if isinstance(data, str):
            # Windows-Format: einzelne Datei mit Anführungszeichen
            if data.startswith('"') and data.endswith('"'):
                data = data[1:-1]

            self._process_dropped_files([data])
        elif isinstance(data, list):
            # Mehrere Dateien
            self._process_dropped_files(data)

    def _process_dropped_files(self, file_paths):
        """Verarbeitet die fallengelassenen Dateien."""
        # Filtere nach existierenden Dateien und Verzeichnissen
        valid_paths = [path for path in file_paths if os.path.exists(path)]

        if not valid_paths:
            self.gui.show_message("Fehler", "Keine gültigen Dateien gefunden.")
            return

        # Starte den Scan-Prozess mit den Dateien
        self.gui.scanner.scan_paths(valid_paths)
```

Weitere Module folgen in den zusätzlichen Dokumenten.
