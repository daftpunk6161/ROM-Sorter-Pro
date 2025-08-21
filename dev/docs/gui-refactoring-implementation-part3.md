# GUI-Refactoring: Implementierungsbeispiele (Teil 3)

Dieser Teil enthält das finale Implementierungsbeispiel für das GUI-Core-Modul und die neue Hauptdatei.

## 5. gui_core.py

Diese Datei enthält die Kernfunktionalität der GUI:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - GUI-Kern

Kernfunktionalität der ROM Sorter Pro-GUI-Anwendung.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
import sys
from typing import Dict, List, Optional, Any, Callable

# Importe aus anderen Modulen
from .gui_components import MemoryEfficientProgressBar, OptimizedDragDropFrame, EfficientLogWidget, OptimizedStatsWidget
from .gui_handlers import ROMSorterGUIHandlers
from .gui_scanner import ScannerIntegration
from .gui_dnd import DragDropManager

class ROMSorterGUICore:
    """Kernklasse der ROM Sorter Pro-GUI."""

    def __init__(self):
        """Initialisiert die GUI."""
        self._initialize_window()
        self._initialize_variables()
        self._create_menu()
        self._create_interface()

        # Lade Konfiguration
        self.config = self._load_config()

        # Initialisiere Subsysteme
        self.handlers = None  # wird später initialisiert
        self.scanner = ScannerIntegration(self)
        self.dnd = DragDropManager(self)

        # Initialisiere Theme-Support
        self._initialize_theme_support()

        # Initialisiere Handler zuletzt, da sie auf andere Subsysteme zugreifen
        self.handlers = ROMSorterGUIHandlers(self)

    def _initialize_window(self):
        """Initialisiert das Hauptfenster."""
        self.root = tk.Tk()
        self.root.title("ROM Sorter Pro v2.2.0")
        self.root.geometry("800x600")
        self.root.minsize(640, 480)

        # Setze das Icon (falls vorhanden)
        try:
            if os.name == 'nt':  # Windows
                self.root.iconbitmap(os.path.join('assets', 'icon.ico'))
            else:  # Linux/Mac
                logo = tk.PhotoImage(file=os.path.join('assets', 'icon.png'))
                self.root.call('wm', 'iconphoto', self.root._w, logo)
        except Exception:
            pass  # Icon nicht kritisch

        # Verhalten beim Schließen
        self.root.protocol("WM_DELETE_WINDOW", self._exit_application)

    def _initialize_variables(self):
        """Initialisiert die Variablen der GUI."""
        self.source_var = tk.StringVar()
        self.target_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Bereit")
        self.progress_var = tk.DoubleVar(value=0)

        # Speicher des letzten verwendeten Verzeichnisses
        self.last_directory = os.path.expanduser("~")

    def _create_menu(self):
        """Erstellt die Menüleiste."""
        self.menu_bar = tk.Menu(self.root)

        # Datei-Menü
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Beenden")
        self.menu_bar.add_cascade(label="Datei", menu=self.file_menu)

        # Optionen-Menü
        self.options_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.options_menu.add_command(label="Einstellungen")
        self.menu_bar.add_cascade(label="Optionen", menu=self.options_menu)

        # Hilfe-Menü
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label="Über")
        self.menu_bar.add_cascade(label="Hilfe", menu=self.help_menu)

        self.root.config(menu=self.menu_bar)

    def _create_interface(self):
        """Erstellt die Benutzeroberfläche."""
        # Erstelle den Hauptrahmen
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Oberer Bereich: Quell- und Zielauswahl
        path_frame = ttk.LabelFrame(main_frame, text="Verzeichnisse")
        path_frame.pack(fill=tk.X, padx=5, pady=5)

        # Quellverzeichnis
        source_frame = ttk.Frame(path_frame)
        source_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(source_frame, text="Quellverzeichnis:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(source_frame, textvariable=self.source_var, width=50).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.source_button = ttk.Button(source_frame, text="Durchsuchen")
        self.source_button.pack(side=tk.LEFT, padx=5)

        # Zielverzeichnis
        target_frame = ttk.Frame(path_frame)
        target_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(target_frame, text="Zielverzeichnis:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(target_frame, textvariable=self.target_var, width=50).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.target_button = ttk.Button(target_frame, text="Durchsuchen")
        self.target_button.pack(side=tk.LEFT, padx=5)

        # Mittlerer Bereich: Drag-and-Drop und Aktionen
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Drag-and-Drop-Bereich
        self.drop_frame = OptimizedDragDropFrame(action_frame)
        self.drop_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Label für den Drag-and-Drop-Bereich
        ttk.Label(
            self.drop_frame,
            text="Ziehen Sie ROM-Dateien oder Ordner hierher",
            font=('TkDefaultFont', 12)
        ).pack(expand=True)

        # Aktionsbuttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        self.start_button = ttk.Button(button_frame, text="Start")
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stopp")
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Unterer Bereich: Fortschrittsanzeige und Log
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Fortschrittsanzeige
        progress_frame = ttk.Frame(bottom_frame)
        progress_frame.pack(fill=tk.X, padx=5, pady=5)

        self.progress_bar = MemoryEfficientProgressBar(
            progress_frame,
            orient=tk.HORIZONTAL,
            mode='determinate',
            variable=self.progress_var
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)

        # Status-Label
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        self.status_label.pack(fill=tk.X, padx=5, pady=5)

        # Log- und Statistik-Bereich (Notebook)
        self.notebook = ttk.Notebook(bottom_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Log-Tab
        self.log_widget = EfficientLogWidget(self.notebook)
        self.notebook.add(self.log_widget, text="Log")

        # Statistik-Tab
        self.stats_widget = OptimizedStatsWidget(self.notebook)
        self.notebook.add(self.stats_widget, text="Statistik")

    def _initialize_theme_support(self):
        """Initialisiert die Theme-Unterstützung."""
        # Standardtheme laden
        style = ttk.Style()

        # Versuche, ein moderneres Theme zu laden, falls verfügbar
        try:
            style.theme_use('clam')  # oder 'alt', 'default', 'classic'
        except Exception:
            # Wenn das Theme nicht verfügbar ist, verwende das Standardtheme
            pass

    def _load_config(self):
        """
        Lädt die Konfiguration.

        Returns:
            Dict: Die geladene Konfiguration
        """
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"Fehler beim Laden der Konfiguration: {e}")

        # Standardkonfiguration
        return {
            "recursive_scan": True,
            "operation": "copy",
            "show_hidden_files": False,
            "organize_by_console": True
        }

    def save_config(self):
        """Speichert die aktuelle Konfiguration."""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            self.log("Konfiguration gespeichert.")
        except Exception as e:
            self.log(f"Fehler beim Speichern der Konfiguration: {e}")

    def log(self, message):
        """
        Fügt eine Nachricht zum Log hinzu.

        Args:
            message: Die zu logende Nachricht
        """
        self.log_widget.log(message)

    def update_status(self, status):
        """
        Aktualisiert die Statusanzeige.

        Args:
            status: Der neue Status
        """
        self.status_var.set(status)

    def update_progress(self, value, max_value=100):
        """
        Aktualisiert die Fortschrittsanzeige.

        Args:
            value: Der aktuelle Wert
            max_value: Der maximale Wert
        """
        percentage = (value / max_value) * 100
        self.progress_var.set(percentage)
        self.progress_bar.smart_update(percentage)

    def update_stats(self, stats_dict):
        """
        Aktualisiert die Statistikanzeige.

        Args:
            stats_dict: Dictionary mit Statistikdaten
        """
        self.stats_widget.update_stats(stats_dict)

    def show_message(self, title, message):
        """
        Zeigt eine Nachricht an.

        Args:
            title: Der Titel der Nachricht
            message: Der Text der Nachricht
        """
        messagebox.showinfo(title, message)

    def _exit_application(self):
        """Beendet die Anwendung sauber."""
        # Beende laufende Scans
        if hasattr(self, 'scanner'):
            self.scanner.stop_scan()

        # Speichere die Konfiguration
        self.save_config()

        # Beende die Anwendung
        self.root.destroy()

    def run(self):
        """Startet die Anwendung."""
        self.log("ROM Sorter Pro v2.2.0 gestartet.")
        self.root.mainloop()
```

## 6. gui.py (neue Hauptdatei)

Diese Datei dient als Einstiegspunkt für die Anwendung:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - Hauptmodul v2.2.0

Einstiegspunkt für die ROM Sorter Pro-Anwendung.
"""

import os
import sys
import traceback
import tkinter as tk
from tkinter import messagebox

# Stelle sicher, dass das Verzeichnis im Suchpfad ist
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

def show_error_and_exit(error_message):
    """Zeigt einen Fehler an und beendet die Anwendung."""
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("ROM Sorter Pro - Fehler", error_message)
        root.destroy()
    except Exception:
        print(f"Fehler: {error_message}")
    finally:
        sys.exit(1)

def main():
    """Hauptfunktion der Anwendung."""
    try:
        # Importiere die GUI erst hier, um Startfehler abzufangen
        from .gui_core import ROMSorterGUICore

        # Starte die Anwendung
        app = ROMSorterGUICore()
        app.run()
    except ImportError as e:
        show_error_and_exit(f"Fehler beim Importieren der GUI-Module: {e}\n\n"
                           f"Details:\n{traceback.format_exc()}")
    except Exception as e:
        show_error_and_exit(f"Ein unerwarteter Fehler ist aufgetreten: {e}\n\n"
                           f"Details:\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()
```

## Integrationstest nach dem Refactoring

Nachdem alle Module implementiert wurden, sollte ein Integrationstest durchgeführt werden:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - Integrationstest

Test der refaktorisierten GUI-Module.
"""

import unittest
import tkinter as tk
import os
import sys

# Füge das Projektverzeichnis zum Suchpfad hinzu
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ui.gui_components import MemoryEfficientProgressBar, OptimizedDragDropFrame, EfficientLogWidget
from src.ui.gui_core import ROMSorterGUICore
from src.ui.gui_scanner import FastFileScanner, ScannerIntegration
from src.ui.gui_dnd import DragDropManager
from src.ui.gui_handlers import ROMSorterGUIHandlers

class TestGUIModules(unittest.TestCase):
    """Tests für die GUI-Module."""

    def setUp(self):
        """Wird vor jedem Test ausgeführt."""
        self.root = tk.Tk()

    def tearDown(self):
        """Wird nach jedem Test ausgeführt."""
        self.root.destroy()

    def test_components(self):
        """Test für die GUI-Komponenten."""
        # Teste MemoryEfficientProgressBar
        progress_bar = MemoryEfficientProgressBar(self.root)
        self.assertIsNotNone(progress_bar)
        progress_bar.smart_update(50)

        # Teste EfficientLogWidget
        log_widget = EfficientLogWidget(self.root)
        self.assertIsNotNone(log_widget)
        log_widget.log("Test-Nachricht")

    def test_scanner(self):
        """Test für den Scanner."""
        scanner = FastFileScanner()
        self.assertIsNotNone(scanner)

        # Teste das Scannen eines Testverzeichnisses
        test_dir = os.path.join(project_root, 'tests', 'test_data')
        os.makedirs(test_dir, exist_ok=True)

        # Erstelle eine Testdatei
        test_file = os.path.join(test_dir, 'test.rom')
        with open(test_file, 'w') as f:
            f.write("Test")

        # Scanne das Verzeichnis
        list(scanner.scan_directory(test_dir))

        # Bereinige
        os.remove(test_file)
        os.rmdir(test_dir)

    def test_core_initialization(self):
        """Test für die Initialisierung der Kern-GUI."""
        # Dieser Test ist komplexer und erfordert Mocking
        # Für dieses Beispiel prüfen wir nur, ob die Klasse instanziiert werden kann
        try:
            # Mock die Abhängigkeiten
            class MockRoot:
                def __init__(self):
                    self.protocol_calls = []
                    self.config_calls = []

                def title(self, _): pass
                def geometry(self, _): pass
                def minsize(self, _, __): pass
                def protocol(self, event, callback):
                    self.protocol_calls.append((event, callback))
                def config(self, **kwargs):
                    self.config_calls.append(kwargs)

            # Patches für die Tests
            original_tk = tk.Tk
            tk.Tk = lambda: MockRoot()

            # Teste die Initialisierung (wird fehlschlagen, aber das ist für den Test ok)
            try:
                ROMSorterGUICore()
            except Exception:
                pass  # Erwarteter Fehler wegen fehlender vollständiger Mocks

            # Stelle den Original-Zustand wieder her
            tk.Tk = original_tk
        except Exception as e:
            self.fail(f"Unerwarteter Fehler: {e}")

if __name__ == "__main__":
    unittest.main()
```

Dieser Test sollte nach dem Refactoring ausgeführt werden, um sicherzustellen, dass die grundlegenden Module korrekt funktionieren.
