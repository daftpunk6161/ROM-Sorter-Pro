# Codebeispiele für das GUI Refactoring

## Aktueller Zustand (gui.py)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter GUI - Optimized interface for ROM organization v2.2.0
...
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
# Weitere Imports...

class MemoryEfficientProgressBar(ttk.Progressbar):
    """Eine speichereffiziente Progressbar-Implementierung."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Implementation...

class SmartThread(threading.Thread):
    """Ein Thread mit verbesserten Fähigkeiten."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Implementation...

class OptimizedDragDropFrame(tk.Frame):
    """Ein optimierter Frame für Drag-and-Drop-Operationen."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Implementation...

class OptimizedROMSorterGUI:
    """Optimized main GUI class with memory management."""

    def __init__(self):
        self._initialize_window()
        self._initialize_variables()
        self._create_menu()
        self._create_interface()
        self._initialize_workers()
        self._initialize_theme_support()

    def _initialize_window(self):
        """Initialize the main window."""
        # Implementation...

    def _initialize_variables(self):
        """Initialize GUI variables."""
        # Implementation...

    # Weitere Methoden...

    def run(self):
        """Run the GUI application."""
        self.root.mainloop()
```

## Zielzustand nach Refactoring

### gui_components.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter GUI Components - Wiederverwendbare UI-Komponenten
"""

import tkinter as tk
from tkinter import ttk

class MemoryEfficientProgressBar(ttk.Progressbar):
    """Eine speichereffiziente Progressbar-Implementierung."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Implementation...

class OptimizedDragDropFrame(tk.Frame):
    """Ein optimierter Frame für Drag-and-Drop-Operationen."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Implementation...

class EfficientLogWidget(tk.Frame):
    """Ein speichereffizientes Log-Widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Implementation...
```

### gui_core.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter GUI Core - Kernfunktionalität der GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox

# Lokale Importe
from .gui_components import MemoryEfficientProgressBar, OptimizedDragDropFrame
from .gui_handlers import ROMSorterGUIHandlers
from .gui_scanner import ScannerIntegration
from .gui_dnd import DragDropManager

class ROMSorterGUICore:
    """Kernklasse der ROM Sorter GUI."""

    def __init__(self):
        self._initialize_window()
        self._initialize_variables()
        self._create_menu()
        self._create_interface()

        # Integration mit anderen Modulen
        self.handlers = ROMSorterGUIHandlers(self)
        self.scanner = ScannerIntegration(self)
        self.dnd = DragDropManager(self)

        self._initialize_theme_support()

    def _initialize_window(self):
        """Initialize the main window."""
        # Implementation...

    def _initialize_variables(self):
        """Initialize GUI variables."""
        # Implementation...

    def _create_menu(self):
        """Create the menu bar."""
        # Implementation...

    def _create_interface(self):
        """Create the main interface."""
        # Implementation...

    def _initialize_theme_support(self):
        """Initialize theme support."""
        # Implementation...

    def run(self):
        """Run the GUI application."""
        self.root.mainloop()

    def _exit_application(self):
        """Exit the application cleanly."""
        # Implementation...
```

### gui.py (Neue Hauptdatei)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter GUI - Hauptmodul für die ROM Sorter Pro Anwendung
"""

from .gui_core import ROMSorterGUICore

def main():
    """Hauptfunktion zum Starten der GUI."""
    app = ROMSorterGUICore()
    app.run()

if __name__ == "__main__":
    main()
```
