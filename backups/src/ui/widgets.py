from typing import Dict, List, Optional, Any, Callable
import tkinter as tk
from tkinter import ttk, filedialog
import os
import re
import threading

from .base import STYLE, BaseApp, create_tooltip

class FolderSelector(tk.Frame):
    """Widget zur Auswahl eines Ordners mit Label und Button."""

    def __init__(
        self,
        parent: tk.Widget,
        label_text: str,
        button_text: str = "Durchsuchen...",
        var: Optional[tk.StringVar] = None,
        command: Optional[Callable] = None,
        tooltip: Optional[str] = None
    ):
        """
        Initialisiere den Ordnerauswahl-Widget.

        Args:
            parent: Das übergeordnete Widget
            label_text: Der anzuzeigende Label-Text
            button_text: Der Text auf dem Durchsuchen-Button
            var: Die StringVar für den Pfadwert (wird erstellt, wenn None)
            command: Optionale Callback-Funktion für Änderungen
            tooltip: Optionaler Tooltip-Text
        """
        super().__init__(parent, bg=STYLE.colors.bg_primary)

        # Variablen
        self.var = var if var is not None else tk.StringVar()
        self.callback = command

        # Label
        self.label = tk.Label(
            self,
            text=label_text,
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.text_primary,
            font=STYLE.fonts.default,
            anchor='w'
        )
        self.label.pack(fill='x', pady=(0, 2))

        # Frame for Entry and Button
        input_frame = tk.Frame(self, bg=STYLE.colors.bg_primary)
        input_frame.pack(fill='x', pady=(0, 5))

        # Entry for the path
        self.entry = tk.Entry(
            input_frame,
            textvariable=self.var,
            bg="#ffffff",
            fg=STYLE.colors.text_primary,
            font=STYLE.fonts.default,
            relief=tk.SUNKEN,
            borderwidth=1
        )
        self.entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

        # Button for the folder selection
        self.button = tk.Button(
            input_frame,
            text=button_text,
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.text_primary,
            font=STYLE.fonts.default,
            command=self._select_folder
        )
        self.button.pack(side='right')

        # Add tooltip when specified
        if tooltip:
            create_tooltip(self.label, tooltip)
            create_tooltip(self.entry, tooltip)

    def _select_folder(self):
        """Öffne den Ordnerauswahldialog."""
        folder = filedialog.askdirectory(
            title="Ordner auswählen",
            initialdir=self.var.get() if self.var.get() else os.path.expanduser("~")
        )

        if folder:
            self.var.set(folder)
            if self.callback:
                self.callback()

    def get(self) -> str:
        """Gib den aktuellen Pfadwert zurück."""
        return self.var.get()

    def set(self, value: str) -> None:
        """Setze den Pfadwert."""
        self.var.set(value)


class ToggleSwitch(tk.Frame):
    """Ein umschaltbarer Schalter (Toggle Switch) für Ja/Nein-Optionen."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str,
        var: Optional[tk.BooleanVar] = None,
        command: Optional[Callable] = None,
        tooltip: Optional[str] = None
    ):
        """
        Initialisiere den Toggle-Switch.

        Args:
            parent: Das übergeordnete Widget
            text: Der anzuzeigende Text
            var: Die BooleanVar für den Wert (wird erstellt, wenn None)
            command: Optionale Callback-Funktion für Änderungen
            tooltip: Optionaler Tooltip-Text
        """
        super().__init__(parent, bg=STYLE.colors.bg_primary)

        # Variablen
        self.var = var if var is not None else tk.BooleanVar(value=False)
        self.callback = command

        # Change the status when the variable changes
        self.var.trace_add("write", lambda *args: self._update_appearance())

        # The frame for the actual switch
        self.switch_frame = tk.Frame(
            self,
            width=40,
            height=20,
            bg=STYLE.colors.bg_primary,
            highlightthickness=1,
            highlightbackground=STYLE.colors.separator
        )
        self.switch_frame.pack(side='left', padx=(0, 5))
        self.switch_frame.pack_propagate(False)  # Prevents size change

        # The displaceable button
        self.button = tk.Frame(
            self.switch_frame,
            width=16,
            height=16,
            bg=STYLE.colors.text_secondary,
            relief=tk.RAISED,
            borderwidth=1
        )

        # Label for the text
        self.label = tk.Label(
            self,
            text=text,
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.text_primary,
            font=STYLE.fonts.default
        )
        self.label.pack(side='left')

        # Add tooltip when specified
        if tooltip:
            create_tooltip(self, tooltip)

        # Event binding for the click
        self.switch_frame.bind("<Button-1>", self._on_click)
        self.label.bind("<Button-1>", self._on_click)

        # Initialize the appearance
        self._update_appearance()

    def _on_click(self, event=None):
        """Handle den Klick auf den Switch."""
        self.var.set(not self.var.get())
        if self.callback:
            self.callback()

    def _update_appearance(self):
        """Aktualisiere das Erscheinungsbild basierend auf dem aktuellen Wert."""
        self.button.place_forget()

        if self.var.get():
            # Ein-Zustand
            self.switch_frame.configure(bg=STYLE.colors.accent_success)
            self.button.configure(bg="#ffffff")
            self.button.place(x=21, y=1)  # Rechts positionieren
        else:
            # Aus-Zustand
            self.switch_frame.configure(bg=STYLE.colors.bg_secondary)
            self.button.configure(bg=STYLE.colors.text_secondary)
            self.button.place(x=1, y=1)  # Links positionieren

    def toggle(self) -> None:
        """Schalte den Zustand um."""
        self.var.set(not self.var.get())

    def get(self) -> bool:
        """Gib den aktuellen Value zurück."""
        return self.var.get()

    def set(self, value: bool) -> None:
        """Setze den Wert."""
        self.var.set(value)


class FileListBox(tk.Frame):
    """Ein erweitertes Listbox-Widget zur Anzeige von Dateien mit Sortierung und Filterung."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        height: int = 10,
        width: int = 40,
        tooltip: Optional[str] = None
    ):
        """
        Initialisiere die Dateiliste.

        Args:
            parent: Das übergeordnete Widget
            title: Der Titel für die Liste
            height: Die Höhe der Liste in Zeilen
            width: Die Breite der Liste in Zeichen
            tooltip: Optionaler Tooltip-Text
        """
        super().__init__(parent, bg=STYLE.colors.bg_primary)

        # Variablen
        self.items = []  # List of all entries
        self.filtered_items = []  # Filtered entries
        self.filter_text = ""  # Aktueller Filtertext
        self.selected_items = []  # Currently selected entries

        # Titel
        self.title_label = tk.Label(
            self,
            text=title,
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.text_primary,
            font=STYLE.fonts.default,
            anchor='w'
        )
        self.title_label.pack(fill='x', pady=(0, 2))

        # Filterzeile (Entry + Clear-Button)
        filter_frame = tk.Frame(self, bg=STYLE.colors.bg_primary)
        filter_frame.pack(fill='x', pady=(0, 2))

        self.filter_entry = tk.Entry(
            filter_frame,
            bg="#ffffff",
            fg=STYLE.colors.text_primary,
            font=STYLE.fonts.small,
            relief=tk.SUNKEN,
            borderwidth=1
        )
        self.filter_entry.pack(side='left', fill='x', expand=True, padx=(0, 2))
        self.filter_entry.bind("<KeyRelease>", self._on_filter_changed)

        # Clear button for the filter
        self.clear_button = tk.Button(
            filter_frame,
            text="×",
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.text_primary,
            font=STYLE.fonts.default,
            command=self._clear_filter,
            width=2,
            height=1
        )
        self.clear_button.pack(side='right')

        # Frame for list box and scrollbar
        list_frame = tk.Frame(self, bg=STYLE.colors.bg_primary)
        list_frame.pack(fill='both', expand=True)

        # The actual list box
        self.listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,  # Mehrfachauswahl erlauben
            bg="#ffffff",
            fg=STYLE.colors.text_primary,
            font=STYLE.fonts.monospace,
            height=height,
            width=width,
            relief=tk.SUNKEN,
            borderwidth=1
        )
        self.listbox.pack(side='left', fill='both', expand=True)
        self.listbox.bind('<<ListboxSelect>>', self._on_selection_changed)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.listbox.configure(yscrollcommand=scrollbar.set)

        # Add tooltip when specified
        if tooltip:
            create_tooltip(self.title_label, tooltip)

    def _on_filter_changed(self, event=None):
        """Handle Änderungen am Filtertext."""
        self.filter_text = self.filter_entry.get().lower()
        self._apply_filter()

    def _clear_filter(self):
        """Lösche den Filter."""
        self.filter_entry.delete(0, tk.END)
        self.filter_text = ""
        self._apply_filter()

    def _apply_filter(self):
        """Wende den Filter auf die Elemente an."""
        self.filtered_items = [
            item for item in self.items
            if self.filter_text in item.lower()
        ]

        # Update the list box
        self.listbox.delete(0, tk.END)
        for item in self.filtered_items:
            self.listbox.insert(tk.END, item)

    def _on_selection_changed(self, event=None):
        """Handle Änderungen an der Auswahl."""
        selected_indices = self.listbox.curselection()
        self.selected_items = [self.filtered_items[i] for i in selected_indices]

    def add_item(self, item: str) -> None:
        """
        Füge ein Element zur Liste hinzu.

        Args:
            item: Das hinzuzufügende Element
        """
        if item not in self.items:
            self.items.append(item)
            self._apply_filter()

    def add_items(self, items: List[str]) -> None:
        """
        Füge mehrere Elemente zur Liste hinzu.

        Args:
            items: Die hinzuzufügenden Elemente
        """
        for item in items:
            if item not in self.items:
                self.items.append(item)
        self._apply_filter()

    def remove_item(self, item: str) -> None:
        """
        Entferne ein Element aus der Liste.

        Args:
            item: Das zu entfernende Element
        """
        if item in self.items:
            self.items.remove(item)
            self._apply_filter()

    def clear(self) -> None:
        """Leere die Liste."""
        self.items = []
        self.filtered_items = []
        self.listbox.delete(0, tk.END)

    def get_selected(self) -> List[str]:
        """Gib die ausgewählten Elemente zurück."""
        return self.selected_items


class ProgressDialog(tk.Toplevel):
    """Ein Dialog zur Anzeige eines Fortschritts mit der Möglichkeit zum Abbrechen."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str = "Fortschritt",
        message: str = "Bitte warten...",
        max_value: int = 100,
        can_cancel: bool = True,
        on_cancel: Optional[Callable] = None
    ):
        """
        Initialisiere den Fortschrittsdialog.

        Args:
            parent: Das übergeordnete Widget
            title: Der Titel des Dialogs
            message: Die anzuzeigende Nachricht
            max_value: Der maximale Fortschrittswert
            can_cancel: Ob der Dialog abbrechbar ist
            on_cancel: Callback-Funktion für den Abbruch
        """
        super().__init__(parent)
        self.title(title)
        self.geometry("400x150")
        self.resizable(False, False)
        self.transient(parent)  # Dialogue belongs to the overarching window
        self.grab_set()  # Modaler Dialog

        # Fenstereigenschaften
        self.protocol("WM_DELETE_WINDOW", self._on_close)  # Processed closing event

        # Variablen
        self.max_value = max_value
        self.current_value = 0
        self.can_cancel = can_cancel
        self.on_cancel_callback = on_cancel
        self.is_cancelled = False
        self.is_complete = False

        # Zentrale Positionierung
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = 400
        height = 150
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        # UI erstellen
        self._create_ui(message)

    def _create_ui(self, message: str):
        """
        Erstelle die UI-Komponenten.

        Args:
            message: Die anzuzeigende Nachricht
        """
        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)

        # Nachrichtenlabel
        self.message_var = tk.StringVar(value=message)
        self.message_label = tk.Label(
            main_frame,
            textvariable=self.message_var,
            anchor='w',
            justify='left',
            wraplength=360
        )
        self.message_label.pack(fill='x', pady=(0, 10))

        # Fortschrittslabel
        self.progress_text_var = tk.StringVar(value="0%")
        self.progress_label = tk.Label(
            main_frame,
            textvariable=self.progress_text_var,
            anchor='e'
        )
        self.progress_label.pack(fill='x', pady=(0, 5))

        # Fortschrittsbalken
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            main_frame,
            orient='horizontal',
            mode='determinate',
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill='x', pady=(0, 10))

        # Button-Frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill='x')

        # Abbrechen-Button
        if self.can_cancel:
            self.cancel_button = tk.Button(
                button_frame,
                text="Abbrechen",
                command=self._on_cancel,
                padx=10
            )
            self.cancel_button.pack(side='right')

    def _on_close(self):
        """Verarbeite das Schließen-Event."""
        if not self.is_complete and self.can_cancel:
            self._on_cancel()

    def _on_cancel(self):
        """Verarbeite den Abbruch."""
        self.is_cancelled = True
        if self.on_cancel_callback:
            self.on_cancel_callback()
        self.destroy()

    def update_progress(self, value: int, message: Optional[str] = None) -> None:
        """
        Aktualisiere den Fortschritt.

        Args:
            value: Der neue Fortschrittswert
            message: Optionale neue Nachricht
        """
        self.current_value = min(value, self.max_value)
        percent = (self.current_value / self.max_value) * 100

        self.progress_var.set(percent)
        self.progress_text_var.set(f"{percent:.1f}%")

        if message is not None:
            self.message_var.set(message)

        # Update the UI
        self.update_idletasks()

        # Check on the end
        if self.current_value >= self.max_value:
            self.is_complete = True

    def complete(self, message: str = "Abgeschlossen!") -> None:
        """
        Markiere den Fortschritt als abgeschlossen.

        Args:
            message: Die abschließende Nachricht
        """
        self.update_progress(self.max_value, message)

        # Change the cancellation button to an OK button
        if hasattr(self, 'cancel_button'):
            self.cancel_button.configure(text="OK", command=self.destroy)

        self.is_complete = True
