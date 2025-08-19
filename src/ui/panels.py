from typing import Dict, List, Optional, Any, Callable
import tkinter as tk
from tkinter import ttk

from .base import STYLE, BaseApp

class TabPanel:
    """Basis für alle Tab-Panels in der Anwendung."""

    def __init__(self, parent: ttk.Notebook, title: str):
        """
        Initialisiere ein Tab-Panel.

        Args:
            parent: Das übergeordnete Notebook-Widget
            title: Der Titel des Tabs
        """
        self.parent = parent
        self.title = title

        # Create the main frame for this tab panel
        self.frame = tk.Frame(
            parent,
            bg=STYLE.colors.bg_primary,
            padx=10,
            pady=10
        )

        # Add the tab to the notebook
        parent.add(self.frame, text=title)

        # Create the components of the tab
        self._create_widgets()

    def _create_widgets(self):
        """Erstelle die Widgets für dieses Tab. Diese Methode wird von Unterklassen überschrieben."""
        pass


class OptionsPanel(TabPanel):
    """Panel für die Konfigurationsoptionen."""

    def __init__(self, parent: ttk.Notebook):
        """Initialisiere das Optionen-Panel."""
        super().__init__(parent, "Optionen")

    def _create_widgets(self):
        """Erstelle die Widgets für das Optionen-Panel."""
        # Main container with padding
        main_frame = tk.Frame(self.frame, bg=STYLE.colors.bg_primary)
        main_frame.pack(fill='both', expand=True)

        # Create groups for different option types
        self._create_operation_options(main_frame)
        self._create_scanning_options(main_frame)
        self._create_advanced_options(main_frame)

    def _create_operation_options(self, parent):
        """Erstelle die Bereichsoptionen für Operationen."""
        # Frame for surgical options
        section_frame = tk.LabelFrame(
            parent,
            text="Operationseinstellungen",
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.text_primary,
            font=STYLE.fonts.default
        )
        section_frame.pack(fill='x', pady=5, padx=5, anchor='n')

        # Various surgical options such as copying/moving etc. would be added here
        # Placeholder for the actual implementation

    def _create_scanning_options(self, parent):
        """Erstelle die Bereichsoptionen für das Scannen."""
        # Frame for scan options
        section_frame = tk.LabelFrame(
            parent,
            text="Scan-Einstellungen",
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.text_primary,
            font=STYLE.fonts.default
        )
        section_frame.pack(fill='x', pady=5, padx=5, anchor='n')

        # Various scan options would be added here
        # Placeholder for the actual implementation

    def _create_advanced_options(self, parent):
        """Erstelle die Bereichsoptionen für erweiterte Einstellungen."""
        # Frame for extended options
        section_frame = tk.LabelFrame(
            parent,
            text="Erweiterte Einstellungen",
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.text_primary,
            font=STYLE.fonts.default
        )
        section_frame.pack(fill='x', pady=5, padx=5, anchor='n')

        # Various extended options would be added here
        # Placeholder for the actual implementation


class StatisticsPanel(TabPanel):
    """Panel für die Anzeige von Statistiken."""

    def __init__(self, parent: ttk.Notebook):
        """Initialisiere das Statistik-Panel."""
        super().__init__(parent, "Statistiken")

        # Statistik-Variablen
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "matched_files": 0,
            "skipped_files": 0,
            "error_files": 0,
            "saved_space": 0
        }

        # Tkinter variables for the advertisement
        self.stat_vars = {k: tk.StringVar(value="0") for k in self.stats}

    def _create_widgets(self):
        """Erstelle die Widgets für das Statistik-Panel."""
        # Main container with padding
        main_frame = tk.Frame(self.frame, bg=STYLE.colors.bg_primary)
        main_frame.pack(fill='both', expand=True)

        # Create a table for the statistics
        self._create_stats_table(main_frame)

    def _create_stats_table(self, parent):
        """Erstelle eine Tabelle für die Statistik-Anzeige."""
        # Frame for the statistics table
        table_frame = tk.Frame(
            parent,
            bg=STYLE.colors.bg_primary,
            padx=10,
            pady=10
        )
        table_frame.pack(fill='both', expand=True)

        # Spaltenbeschriftungen
        header_frame = tk.Frame(table_frame, bg=STYLE.colors.bg_primary)
        header_frame.pack(fill='x', pady=(0, 5))

        tk.Label(
            header_frame,
            text="Metrik",
            font=STYLE.fonts.header,
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.text_primary,
            width=20,
            anchor='w'
        ).pack(side='left')

        tk.Label(
            header_frame,
            text="Wert",
            font=STYLE.fonts.header,
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.text_primary,
            width=15,
            anchor='w'
        ).pack(side='left')

        # Trennlinie
        separator = ttk.Separator(table_frame, orient='horizontal')
        separator.pack(fill='x', pady=5)

        # Statistik-Zeilen
        labels = {
            "total_files": "Gesamte Dateien",
            "processed_files": "Verarbeitete Dateien",
            "matched_files": "Zugeordnete Dateien",
            "skipped_files": "Übersprungene Dateien",
            "error_files": "Dateien mit Fehlern",
            "saved_space": "Eingesparter Speicherplatz"
        }

        for key, label_text in labels.items():
            row_frame = tk.Frame(table_frame, bg=STYLE.colors.bg_primary)
            row_frame.pack(fill='x', pady=2)

            tk.Label(
                row_frame,
                text=label_text,
                bg=STYLE.colors.bg_primary,
                fg=STYLE.colors.text_primary,
                font=STYLE.fonts.default,
                width=20,
                anchor='w'
            ).pack(side='left')

            tk.Label(
                row_frame,
                textvariable=self.stat_vars[key],
                bg=STYLE.colors.bg_primary,
                fg=STYLE.colors.text_primary,
                font=STYLE.fonts.default,
                width=15,
                anchor='w'
            ).pack(side='left')

    def update_stats(self, stats_dict: Dict[str, Any]) -> None:
        """
        Aktualisiere die Statistikanzeige mit neuen Werten.

        Args:
            stats_dict: Ein Dictionary mit den zu aktualisierenden Statistiken
        """
        for key, value in stats_dict.items():
            if key in self.stat_vars:
                if key == "saved_space":
                    # Formatiere bytes in legible size
                    self.stat_vars[key].set(self._format_size(value))
                else:
                    self.stat_vars[key].set(str(value))

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """
        Formatiere eine Bytezahl in eine lesbare Größe.

        Args:
            size_bytes: Die Größe in Bytes

        Returns:
            str: Die formatierte Größe (z.B. "1.23 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0 or unit == 'TB':
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0


class LogPanel(TabPanel):
    """Panel für die Anzeige von Protokollen."""

    def __init__(self, parent: ttk.Notebook):
        """Initialisiere das Log-Panel."""
        super().__init__(parent, "Protokoll")
        self.max_lines = 1000  # Maximum number of lines to be displayed

    def _create_widgets(self):
        """Erstelle die Widgets für das Log-Panel."""
        # Main container with padding
        main_frame = tk.Frame(self.frame, bg=STYLE.colors.bg_primary)
        main_frame.pack(fill='both', expand=True)

        # Text widget for the log display
        self.log_text = tk.Text(
            main_frame,
            wrap=tk.WORD,
            font=STYLE.fonts.monospace,
            bg="#ffffff",
            fg=STYLE.colors.text_primary,
            padx=5,
            pady=5,
            height=20
        )
        self.log_text.pack(fill='both', expand=True)

        # Scroll bar for the text widget
        scrollbar = ttk.Scrollbar(self.log_text, orient='vertical', command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text['yscrollcommand'] = scrollbar.set

        # Make the text field in writing protected
        self.log_text.configure(state='disabled')

        # Define tag configurations for different protocol levels
        self.log_text.tag_configure('INFO', foreground='#000000')
        self.log_text.tag_configure('WARNING', foreground='#ff9800')
        self.log_text.tag_configure('ERROR', foreground='#f44336')
        self.log_text.tag_configure('DEBUG', foreground='#2196f3')

        # Buttons for protocol control
        button_frame = tk.Frame(main_frame, bg=STYLE.colors.bg_primary)
        button_frame.pack(fill='x', pady=5)

        tk.Button(
            button_frame,
            text="Protokoll leeren",
            font=STYLE.fonts.button,
            command=self.clear_log,
            bg=STYLE.colors.bg_primary
        ).pack(side='left', padx=5)

        tk.Button(
            button_frame,
            text="Protokoll speichern",
            font=STYLE.fonts.button,
            command=self.save_log,
            bg=STYLE.colors.bg_primary
        ).pack(side='left', padx=5)

    def add_log(self, message: str, level: str = 'INFO') -> None:
        """
        Füge eine Nachricht zum Protokoll hinzu.

        Args:
            message: Die hinzuzufügende Nachricht
            level: Die Protokollebene (INFO, WARNING, ERROR, DEBUG)
        """
        # Activate processing
        self.log_text.configure(state='normal')

        # Check whether the maximum number of lines is reached
        lines = self.log_text.get('1.0', tk.END).count('\n')
        if lines >= self.max_lines:
            # Remove the first 100 lines
            self.log_text.delete('1.0', '101.0')

        # Add the new message with the corresponding day
        self.log_text.insert(tk.END, f"{message}\n", level)

        # Scrolle zum Ende des Textes
        self.log_text.see(tk.END)

        # Deactivate processing again
        self.log_text.configure(state='disabled')

    def clear_log(self) -> None:
        """Leere das Protokoll."""
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.configure(state='disabled')

    def save_log(self) -> None:
        """Speichere das Protokoll in eine Datei."""
        # In an actual implementation, a file dialog would be opened here and
        # the content of the protocol can be saved in the selected file
        # Placeholder for the actual implementation
        pass
