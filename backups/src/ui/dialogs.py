"""
ROM Sorter Pro v2.1.8 - Dialog Modules

This module provides specialized dialog classes for the ROM Sorter application.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple

from .base import STYLE, BaseApp, center_window, create_tooltip
from .widgets import ProgressDialog, FileListBox


class AboutDialog(tk.Toplevel):
    """Dialog for displaying information about the application."""

    def __init__(self, parent, app_version="2.1.8", app_year="2025"):
        """
        Initialize the About dialog.

        Args:
            parent: The parent window
            app_version: The version number of the application
            app_year: The creation year of the application
        """
        super().__init__(parent)
        self.title("Über ROM Sorter Pro")
        self.geometry("500x400")
        self.resizable(False, False)
        self.transient(parent)  # Dialogue belongs to the overarching window
        self.grab_set()  # Modaler Dialog

# Central positioning
        center_window(self, 500, 400)

# Main frame with padding
        main_frame = tk.Frame(self, bg=STYLE.colors.bg_primary, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

# App logo (placeholder)
        logo_frame = tk.Frame(main_frame, bg=STYLE.colors.accent_primary, width=100, height=100)
        logo_frame.pack(pady=(0, 20))
        logo_frame.pack_propagate(False)  # Prevents the frame from shrinking

        logo_text = tk.Label(
            logo_frame,
            text="ROM\nSorter",
            font=STYLE.fonts.title,
            bg=STYLE.colors.accent_primary,
            fg="#ffffff"
        )
        logo_text.pack(fill="both", expand=True)

# App name
        app_name = tk.Label(
            main_frame,
            text="ROM Sorter Pro",
            font=STYLE.fonts.title,
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.fg_primary
        )
        app_name.pack(pady=(0, 5))

# version
        version_label = tk.Label(
            main_frame,
            text=f"Version {app_version}",
            font=STYLE.fonts.default,
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.fg_primary
        )
        version_label.pack(pady=(0, 20))

# Description
        desc_text = (
            "ROM Sorter Pro ist ein leistungsstarkes Tool zum Organisieren, "
            "Kategorisieren und Verwalten von ROM-Dateien für verschiedene Spielekonsolen."
        )
        desc_label = tk.Label(
            main_frame,
            text=desc_text,
            font=STYLE.fonts.default,
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.fg_primary,
            wraplength=460,
            justify="center"
        )
        desc_label.pack(pady=(0, 20))

# copyright
        copyright_label = tk.Label(
            main_frame,
            text=f"© {app_year} ROM Sorter Team",
            font=STYLE.fonts.small,
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.fg_secondary
        )
        copyright_label.pack(pady=(0, 5))

# Website link
        website_frame = tk.Frame(main_frame, bg=STYLE.colors.bg_primary)
        website_frame.pack(pady=(0, 20))

        website_label = tk.Label(
            website_frame,
            text="Website:",
            font=STYLE.fonts.default,
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.fg_primary
        )
        website_label.pack(side="left", padx=(0, 5))

        website_link = tk.Label(
            website_frame,
            text="rom-sorter.example.org",
            font=STYLE.fonts.default,
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.accent_primary,
            cursor="hand2"
        )
        website_link.pack(side="left")
        website_link.bind("<Button-1>", lambda e: webbrowser.open("https://rom-sorter.example.org"))

# OK button
        ok_button = tk.Button(
            main_frame,
            text="OK",
            command=self.destroy,
            bg=STYLE.colors.bg_primary,
            padx=20
        )
        ok_button.pack(pady=(10, 0))


class SettingsDialog(tk.Toplevel):
    """Dialogue for the application settings."""

    def __init__(self, parent, config=None, on_save=None):
        """Initialize the settings dialog. Args: Parent: The overarching window Config: The configuration object or dictionary On_save: Callback function that is called when the settings are saved"""
        super().__init__(parent)
        self.title("Einstellungen")
        self.geometry("600x500")
        self.resizable(True, True)
        self.transient(parent)  # Dialogue belongs to the overarching window
        self.grab_set()  # Modaler Dialog

# Configuration and callback
        self.config = config or {}
        self.on_save = on_save

# Central positioning
        center_window(self, 600, 500)

# Create the UI
        self._create_ui()

    def _create_ui(self):
        """Create the UI components."""
# Main frame with padding
        main_frame = tk.Frame(self, bg=STYLE.colors.bg_primary)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

# Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

# Create the tab content
        self._create_general_tab()
        self._create_scanner_tab()
        self._create_appearance_tab()
        self._create_advanced_tab()

        # Buttons
        button_frame = tk.Frame(main_frame, bg=STYLE.colors.bg_primary)
        button_frame.pack(fill="x", pady=(10, 0))

# Save button
        save_button = tk.Button(
            button_frame,
            text="Speichern",
            command=self._save_settings,
            bg=STYLE.colors.bg_primary,
            padx=10
        )
        save_button.pack(side="right", padx=5)

# Cancel button
        cancel_button = tk.Button(
            button_frame,
            text="Abbrechen",
            command=self.destroy,
            bg=STYLE.colors.bg_primary,
            padx=10
        )
        cancel_button.pack(side="right", padx=5)

    def _create_general_tab(self):
        """Create the tab for general settings."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Allgemein")

# In a complete implementation, the general settings would be added here
        label = tk.Label(
            tab,
            text="Allgemeine Einstellungen",
            font=STYLE.fonts.header
        )
        label.pack(pady=10)

    def _create_scanner_tab(self):
        """Create the tab for scanner settings."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Scanner")

# In a complete implementation, the scanner settings would be added here
        label = tk.Label(
            tab,
            text="Scanner-Einstellungen",
            font=STYLE.fonts.header
        )
        label.pack(pady=10)

    def _create_appearance_tab(self):
        """Create the Tab for appearance settings."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Erscheinungsbild")

# In A Complete Implementation, The Appearance Settings would be added here
        label = tk.Label(
            tab,
            text="Erscheinungsbild-Einstellungen",
            font=STYLE.fonts.header
        )
        label.pack(pady=10)

    def _create_advanced_tab(self):
        """Create the tab for extended settings."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Erweitert")

# In A Complete Implementation, The Extended Settings would be added here
        label = tk.Label(
            tab,
            text="Erweiterte Einstellungen",
            font=STYLE.fonts.header
        )
        label.pack(pady=10)

    def _save_settings(self):
        """Save the settings."""
# In a complete implementation, The Settings from the Ui would be read here
# and saved in self.config

        if self.on_save:
            self.on_save(self.config)

        self.destroy()


class ErrorDialog(tk.Toplevel):
    """Dialog for displaying error information with detailed options."""

    def __init__(
        self,
        parent,
        title: str = "Fehler",
        message: str = "Ein Fehler ist aufgetreten.",
        details: Optional[str] = None,
        exception: Optional[Exception] = None
    ):
        """Initialize the error dialog. Args: Parent: The overarching window Title: The title of the dialogue Message: the error message Details: Optional detailed information on the error Exception: Optional exception that caused the error"""
        super().__init__(parent)
        self.title(title)
        self.geometry("500x300")
        self.resizable(True, True)
        self.transient(parent)  # Dialogue belongs to the overarching window
        self.grab_set()  # Modaler Dialog

# Save the parameters
        self.message = message
        self.details = details
        self.exception = exception

# Generate detailed information from the exception, if available
        if exception and not details:
            import traceback
            self.details = ''.join(traceback.format_exception(
                type(exception), exception, exception.__traceback__
            ))

# Central positioning
        center_window(self, 500, 300)

# Create the UI
        self._create_ui()

    def _create_ui(self):
        """Create the UI components."""
# Main frame with padding
        main_frame = tk.Frame(self, bg=STYLE.colors.bg_primary)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

# Icon and message above
        top_frame = tk.Frame(main_frame, bg=STYLE.colors.bg_primary)
        top_frame.pack(fill="x", pady=(0, 10))

# Error symbol (placeholder for a real icon)
        icon_frame = tk.Frame(top_frame, bg=STYLE.colors.accent_error, width=32, height=32)
        icon_frame.pack(side="left", padx=(0, 10))
        icon_frame.pack_propagate(False)

# News
        message_label = tk.Label(
            top_frame,
            text=self.message,
            font=STYLE.fonts.default,
            bg=STYLE.colors.bg_primary,
            fg=STYLE.colors.fg_primary,
            wraplength=400,
            justify="left",
            anchor="w"
        )
        message_label.pack(side="left", fill="both", expand=True)

# Show details if available
        if self.details:
# Frame for detailed view
            details_frame = tk.LabelFrame(
                main_frame,
                text="Details",
                bg=STYLE.colors.bg_primary,
                fg=STYLE.colors.fg_primary
            )
            details_frame.pack(fill="both", expand=True, pady=(0, 10))

# Text field with scroll bar for details
            text_frame = tk.Frame(details_frame, bg=STYLE.colors.bg_primary)
            text_frame.pack(fill="both", expand=True, padx=5, pady=5)

            self.details_text = tk.Text(
                text_frame,
                wrap="word",
                font=STYLE.fonts.monospace,
                bg=STYLE.colors.bg_secondary,
                fg=STYLE.colors.fg_primary
            )
            self.details_text.pack(side="left", fill="both", expand=True)

            scrollbar = ttk.Scrollbar(text_frame, command=self.details_text.yview)
            scrollbar.pack(side="right", fill="y")
            self.details_text.configure(yscrollcommand=scrollbar.set)

# Enter details and put on writing -protected
            self.details_text.insert("1.0", self.details)
            self.details_text.configure(state="disabled")

# Buttons below
        button_frame = tk.Frame(main_frame, bg=STYLE.colors.bg_primary)
        button_frame.pack(fill="x")

# OK button
        ok_button = tk.Button(
            button_frame,
            text="OK",
            command=self.destroy,
            bg=STYLE.colors.bg_primary,
            padx=20
        )
        ok_button.pack(side="right", padx=5)

# Copy button (if there is details)
        if self.details:
            copy_button = tk.Button(
                button_frame,
                text="In Zwischenablage kopieren",
                command=self._copy_to_clipboard,
                bg=STYLE.colors.bg_primary
            )
            copy_button.pack(side="left", padx=5)

    def _copy_to_clipboard(self):
        """Copy the details into the clipboard."""
        if self.details:
            self.clipboard_clear()
            self.clipboard_append(self.details)

# Show brief confirmation
            messagebox.showinfo(
                "Information",
                "Fehlerdaten wurden in die Zwischenablage kopiert."
            )


def show_error_dialog(parent, title, message, details=None, exception=None):
    """Show an error dialog. Args: Parent: The overarching window Title: The title of the dialogue Message: the error message Details: Optional detailed information on the error Exception: Optional exception that caused the error"""
    ErrorDialog(parent, title, message, details, exception)


def show_about_dialog(parent):
    """Show the About dialog. Args: Parent: The overarching window"""
    AboutDialog(parent)


def show_settings_dialog(parent, config=None, on_save=None):
    """Show the settings dialog. Args: Parent: The overarching window Config: The configuration object or dictionary On_save: Callback function that is called when the settings are saved"""
    SettingsDialog(parent, config, on_save)
