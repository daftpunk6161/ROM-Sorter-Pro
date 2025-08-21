# GUI-Refactoring: Implementierungsbeispiele (Teil 2)

Dieser Teil enthält weitere Implementierungsbeispiele für die restlichen Module des GUI-Refactorings.

## 3. gui_scanner.py

Diese Datei enthält die Scanner-Funktionalität:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - Scanner-Integration

Integration der Scanner-Funktionalität in die GUI.
"""

import os
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
import time
from typing import Dict, List, Optional, Any, Callable, Set, Tuple

# Import der Konsolen-Mappings
from .console_mappings import CONSOLE_MAP, get_console_for_extension

class FastFileScanner:
    """Effizienter Datei-Scanner für ROM-Dateien."""

    def __init__(self, extensions=None):
        """
        Initialisiert den Scanner.

        Args:
            extensions: Liste der zu suchenden Dateiendungen
        """
        self.extensions = set(extensions) if extensions else set()
        self.should_stop = threading.Event()
        self._results_queue = queue.Queue()

    def scan_directory(self, directory_path, recursive=True):
        """
        Durchsucht ein Verzeichnis nach ROM-Dateien.

        Args:
            directory_path: Das zu durchsuchende Verzeichnis
            recursive: Wenn True, werden auch Unterverzeichnisse durchsucht

        Yields:
            Pfade zu gefundenen ROM-Dateien
        """
        if self.should_stop.is_set():
            return

        try:
            for entry in os.scandir(directory_path):
                if self.should_stop.is_set():
                    break

                if entry.is_file():
                    # Prüfe, ob die Datei eine der gesuchten Endungen hat
                    ext = os.path.splitext(entry.name)[1].lower()
                    if not self.extensions or ext in self.extensions:
                        yield entry.path

                elif entry.is_dir() and recursive:
                    # Durchsuche Unterverzeichnisse rekursiv
                    yield from self.scan_directory(entry.path, recursive)
        except (PermissionError, FileNotFoundError) as e:
            # Ignoriere Fehler und setze den Scan fort
            pass

    def scan_paths(self, paths, recursive=True):
        """
        Durchsucht mehrere Pfade nach ROM-Dateien.

        Args:
            paths: Liste von Pfaden (Dateien oder Verzeichnisse)
            recursive: Wenn True, werden auch Unterverzeichnisse durchsucht
        """
        for path in paths:
            if self.should_stop.is_set():
                break

            if os.path.isfile(path):
                # Einzelne Datei
                ext = os.path.splitext(path)[1].lower()
                if not self.extensions or ext in self.extensions:
                    self._results_queue.put(path)

            elif os.path.isdir(path):
                # Verzeichnis
                for file_path in self.scan_directory(path, recursive):
                    self._results_queue.put(file_path)

    def stop(self):
        """Stoppt den Scan."""
        self.should_stop.set()

    def get_results(self):
        """
        Gibt die gefundenen Ergebnisse zurück.

        Returns:
            Liste der gefundenen Dateipfade
        """
        results = []
        while not self._results_queue.empty():
            results.append(self._results_queue.get())
        return results

class ScannerIntegration:
    """Integration der Scanner-Funktionalität in die GUI."""

    def __init__(self, gui_instance):
        """
        Initialisiert die Scanner-Integration.

        Args:
            gui_instance: Die GUI-Instanz
        """
        self.gui = gui_instance
        self.scanner = FastFileScanner(extensions=CONSOLE_MAP.keys())
        self.worker_threads = []
        self.scan_active = False
        self.scan_results = {}

        # Thread-Pool für parallele Verarbeitung
        self.thread_pool = ThreadPoolExecutor(
            max_workers=os.cpu_count() or 4,
            thread_name_prefix="GUI"
        )

    def scan_paths(self, paths):
        """
        Startet einen Scan für die angegebenen Pfade.

        Args:
            paths: Liste von Pfaden zum Scannen
        """
        if self.scan_active:
            self.gui.show_message("Info", "Ein Scan läuft bereits.")
            return

        self.scan_active = True
        self.gui.update_status("Scan gestartet...")

        # Starte den Scan in einem separaten Thread
        worker = threading.Thread(
            target=self._scan_worker,
            args=(paths,),
            daemon=True
        )
        worker.start()
        self.worker_threads.append(worker)

        # Starte den Fortschritts-Update-Thread
        update_thread = threading.Thread(
            target=self._update_progress,
            daemon=True
        )
        update_thread.start()
        self.worker_threads.append(update_thread)

    def _scan_worker(self, paths):
        """
        Worker-Funktion für den Scan.

        Args:
            paths: Liste von Pfaden zum Scannen
        """
        try:
            self.scanner.scan_paths(paths)
            results = self.scanner.get_results()
            self._process_results(results)
        finally:
            self.scan_active = False
            self.gui.update_status("Scan abgeschlossen.")

    def _process_results(self, file_paths):
        """
        Verarbeitet die Scan-Ergebnisse.

        Args:
            file_paths: Liste von gefundenen Dateipfaden
        """
        console_counts = {}

        for file_path in file_paths:
            ext = os.path.splitext(file_path)[1].lower()
            console = get_console_for_extension(ext)

            # Zähle die Treffer pro Konsole
            console_counts[console] = console_counts.get(console, 0) + 1

            # Füge die Datei zu den Ergebnissen hinzu
            if console not in self.scan_results:
                self.scan_results[console] = []
            self.scan_results[console].append(file_path)

        # Aktualisiere die GUI mit den Ergebnissen
        self.gui.update_stats(console_counts)

    def _update_progress(self):
        """Aktualisiert die Fortschrittsanzeige während des Scans."""
        while self.scan_active:
            # Erhalte die aktuellen Ergebnisse ohne sie zu entfernen
            temp_results = self.scanner.get_results()
            count = len(temp_results)

            # Aktualisiere die GUI
            self.gui.update_progress(count)

            # Warte kurz
            time.sleep(0.5)

    def stop_scan(self):
        """Stoppt den aktiven Scan."""
        if self.scan_active:
            self.scanner.stop()
            self.scan_active = False
            self.gui.update_status("Scan abgebrochen.")

    def clear_results(self):
        """Löscht die Scan-Ergebnisse."""
        self.scan_results = {}
        self.gui.update_stats({})
        self.gui.update_status("Ergebnisse gelöscht.")
```

## 4. gui_handlers.py

Diese Datei enthält die Event-Handler und Callbacks:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - GUI-Handler

Event-Handler und Callbacks für die ROM Sorter Pro-Anwendung.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import threading
from typing import Dict, List, Optional, Any, Callable

class ROMSorterGUIHandlers:
    """Handler für die GUI-Events der ROM Sorter-Anwendung."""

    def __init__(self, gui_instance):
        """
        Initialisiert die Handler-Klasse.

        Args:
            gui_instance: Die GUI-Instanz
        """
        self.gui = gui_instance
        self._register_callbacks()

    def _register_callbacks(self):
        """Registriert die Callbacks für die UI-Elemente."""
        # Buttons
        self.gui.source_button.config(command=self._on_source_select)
        self.gui.target_button.config(command=self._on_target_select)
        self.gui.start_button.config(command=self._on_start_clicked)
        self.gui.stop_button.config(command=self._on_stop_clicked)

        # Menü
        self.gui.file_menu.add_command(label="Beenden", command=self._on_exit)
        self.gui.help_menu.add_command(label="Über", command=self._show_about)
        self.gui.options_menu.add_command(label="Einstellungen", command=self._show_settings)

    def _on_source_select(self):
        """Handler für die Quellenauswahl."""
        directory = filedialog.askdirectory(
            title="ROM-Quellverzeichnis auswählen",
            initialdir=self.gui.last_directory
        )

        if directory:
            self.gui.last_directory = directory
            self.gui.source_var.set(directory)
            self.gui.log("Quellverzeichnis ausgewählt: " + directory)

    def _on_target_select(self):
        """Handler für die Zielauswahl."""
        directory = filedialog.askdirectory(
            title="ROM-Zielverzeichnis auswählen",
            initialdir=self.gui.last_directory
        )

        if directory:
            self.gui.last_directory = directory
            self.gui.target_var.set(directory)
            self.gui.log("Zielverzeichnis ausgewählt: " + directory)

    def _on_start_clicked(self):
        """Handler für den Start-Button."""
        source = self.gui.source_var.get()
        target = self.gui.target_var.get()

        if not source or not os.path.isdir(source):
            messagebox.showerror("Fehler", "Bitte wählen Sie ein gültiges Quellverzeichnis.")
            return

        if not target or not os.path.isdir(target):
            messagebox.showerror("Fehler", "Bitte wählen Sie ein gültiges Zielverzeichnis.")
            return

        # Starte den Scan-Prozess
        self.gui.log(f"Starte Scan von {source}...")
        self.gui.scanner.scan_paths([source])
        self.gui.update_status("Scan läuft...")

    def _on_stop_clicked(self):
        """Handler für den Stop-Button."""
        self.gui.scanner.stop_scan()
        self.gui.log("Scan abgebrochen.")

    def _on_exit(self):
        """Handler für den Beenden-Menüpunkt."""
        self.gui._exit_application()

    def _show_about(self):
        """Zeigt den Über-Dialog an."""
        messagebox.showinfo(
            "Über ROM Sorter Pro",
            "ROM Sorter Pro v2.2.0\n\n"
            "Ein Tool zum Organisieren von ROM-Dateien nach Konsole.\n\n"
            "© 2025 ROM Sorter Team"
        )

    def _show_settings(self):
        """Zeigt den Einstellungs-Dialog an."""
        # Erstelle ein Toplevel-Fenster für die Einstellungen
        settings_window = tk.Toplevel(self.gui.root)
        settings_window.title("Einstellungen")
        settings_window.geometry("400x300")
        settings_window.resizable(False, False)

        # Erstelle die UI-Elemente für die Einstellungen
        # (Vereinfachte Implementierung für das Beispiel)
        ttk.Label(settings_window, text="Einstellungen").pack(pady=10)

        # Recursive Scanning
        recursive_var = tk.BooleanVar(value=self.gui.config.get("recursive_scan", True))
        ttk.Checkbutton(
            settings_window,
            text="Unterverzeichnisse durchsuchen",
            variable=recursive_var
        ).pack(anchor=tk.W, padx=20, pady=5)

        # Copy vs Move
        operation_var = tk.StringVar(value=self.gui.config.get("operation", "copy"))
        ttk.Label(settings_window, text="Dateioperation:").pack(anchor=tk.W, padx=20, pady=5)
        ttk.Radiobutton(
            settings_window,
            text="Dateien kopieren",
            variable=operation_var,
            value="copy"
        ).pack(anchor=tk.W, padx=40)
        ttk.Radiobutton(
            settings_window,
            text="Dateien verschieben",
            variable=operation_var,
            value="move"
        ).pack(anchor=tk.W, padx=40)

        # Speichern-Button
        def save_settings():
            self.gui.config["recursive_scan"] = recursive_var.get()
            self.gui.config["operation"] = operation_var.get()
            self.gui.save_config()
            settings_window.destroy()

        ttk.Button(
            settings_window,
            text="Speichern",
            command=save_settings
        ).pack(pady=20)
```

Weitere Details folgen in Teil 3 dieses Dokuments.
