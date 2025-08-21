#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROM Sorter Pro - GUI Theme Integration

Dieses Modul integriert das Theme-System in die GUI von ROM Sorter Pro.
Es stellt Funktionen bereit, um Themes auf die GUI anzuwenden und
ermöglicht den Benutzern, Themes zu wählen und anzupassen.
"""

import os
import sys
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkfont
import tkinter.colorchooser as colorchooser
from typing import Dict, Any
import platform
import json
import logging
from datetime import datetime

# Import theme settings and utilities
from src.config.theme_settings import THEME_SETTINGS, CUSTOM_THEME_PATH

# Versuche, das erweiterte Logging-System zu importieren
try:
    from src.utils.logging_integration import (
        get_logger, log_context, log_performance, log_exception
    )
    ENHANCED_LOGGING = True
except ImportError:
    ENHANCED_LOGGING = False
    # Fallback zur alten Logger-Implementierung
    from src.utils.logger import setup_logger

# Logger konfigurieren
if ENHANCED_LOGGING:
    logger = get_logger(__name__)
else:
    logger = setup_logger(__name__)

# Import local module with relative imports
from .theme_manager import ThemeManager, Theme, ThemeType, ColorScheme


class ThemeIntegrator:
    """Klasse zur Integration des Theme-Systems in die GUI."""

    def __init__(self, gui_instance):
        """
        Initialisiert den ThemeIntegrator.

        Args:
            gui_instance: Instanz der GUI-Klasse
        """
        self.gui = gui_instance
        self.theme_manager = ThemeManager()
        self.current_theme = self.theme_manager.get_theme()

        # Save the original colors and fonts for recovery
        self.original_styles = self._capture_original_styles()

        # Apply the current theme
        self.apply_theme()

    def _capture_original_styles(self) -> Dict[str, Dict[str, Any]]:
        """
        Erfasst die ursprünglichen Stile der GUI-Elemente.

        Returns:
            Dictionary mit originalen Stileigenschaften
        """
        styles = {}

        try:
            # Erfasse ttk-Stile
            style = ttk.Style()
            for theme_name in style.theme_names():
                if theme_name == style.theme_use():
                    for element in ['TButton', 'TEntry', 'TLabel', 'TFrame', 'TCheckbutton', 'TCombobox',
                                   'TNotebook', 'TNotebook.Tab', 'Treeview', 'Treeview.Heading']:
                        try:
                            styles[element] = {}
                            for key in ['background', 'foreground', 'relief', 'borderwidth', 'font']:
                                try:
                                    value = style.lookup(element, key)
                                    if value:
                                        styles[element][key] = value
                                except Exception:
                                    pass
                        except Exception:
                            pass

            # Erfasse tk-Standardstile vom Root-Fenster
            for key in ['background', 'foreground', 'font']:
                try:
                    if hasattr(self.gui.root, 'cget'):
                        value = self.gui.root.cget(key)
                        if not 'root' in styles:
                            styles['root'] = {}
                        styles['root'][key] = value
                except Exception:
                    pass

            logger.debug("Originale Stile erfasst")
        except Exception as e:
            logger.error(f"Fehler beim Erfassen der originalen Stile: {e}")

        return styles

    @log_performance(operation="apply_theme") if ENHANCED_LOGGING else lambda x: x
    def apply_theme(self) -> bool:
        """
        Wendet das aktuelle Theme auf die GUI an.

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            theme = self.theme_manager.get_theme()
            self.current_theme = theme

            # Use of TTK styles
            self._apply_ttk_styles(theme)

            # Anwendung auf Root-Fenster
            self._apply_to_root(theme)

            # Anwendung auf bestehende Widgets
            self._apply_to_existing_widgets(theme)

            # Erfolgsprotokollierung
            logger.info(f"Theme '{theme.name}' erfolgreich angewendet")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Anwenden des Themes: {e}")
            return False

    def _apply_ttk_styles(self, theme: Theme) -> None:
        """
        Wendet das Theme auf ttk-Stile an.

        Args:
            theme: Anzuwendendes Theme
        """
        style = ttk.Style()
        colors = theme.colors

        # Definiere gemeinsame Stileigenschaften
        bg = colors.background
        fg = colors.text
        primary = colors.primary
        secondary = colors.secondary
        border = colors.border
        accent = colors.accent

        # Definiere Schriftart
        font = (theme.font_family.split(',')[0].strip(), theme.font_size)

        # Anwendung auf verschiedene Widget-Typen
        style.configure('TFrame', background=bg)
        style.configure('TLabel', background=bg, foreground=fg, font=font)
        style.configure('TButton', background=primary, foreground='white', font=font, relief='flat', borderwidth=1, padding=theme.spacing)
        style.map('TButton',
                 background=[('active', self._lighten_or_darken(primary, 0.1, theme))],
                 foreground=[('active', 'white')])

        style.configure('Secondary.TButton', background=secondary)
        style.map('Secondary.TButton',
                 background=[('active', self._lighten_or_darken(secondary, 0.1, theme))])

        style.configure('TEntry', background=self._lighten_or_darken(bg, 0.05, theme), foreground=fg,
                       borderwidth=1, font=font)
        style.map('TEntry',
                 fieldbackground=[('focus', self._lighten_or_darken(bg, 0.05, theme))],
                 bordercolor=[('focus', primary)])

        style.configure('TCheckbutton', background=bg, foreground=fg, font=font)
        style.map('TCheckbutton',
                 indicatorcolor=[('selected', primary)],
                 background=[('active', self._lighten_or_darken(bg, 0.05, theme))])

        style.configure('TCombobox', background=self._lighten_or_darken(bg, 0.05, theme), foreground=fg, font=font)
        style.map('TCombobox',
                 fieldbackground=[('readonly', self._lighten_or_darken(bg, 0.05, theme))],
                 selectbackground=[('focus', primary)],
                 selectforeground=[('focus', 'white')])

        style.configure('TNotebook', background=bg, borderwidth=0)
        style.configure('TNotebook.Tab', background=self._lighten_or_darken(bg, 0.1, theme), foreground=fg,
                       padding=(10, 5), font=font)
        style.map('TNotebook.Tab',
                 background=[('selected', bg)],
                 expand=[('selected', (2, 2, 2, 0))])

        style.configure('Treeview', background=self._lighten_or_darken(bg, 0.03, theme),
                       foreground=fg, font=font, fieldbackground=self._lighten_or_darken(bg, 0.03, theme))
        style.configure('Treeview.Heading', background=self._lighten_or_darken(bg, 0.1, theme),
                       foreground=fg, font=font, relief='flat')
        style.map('Treeview',
                 background=[('selected', primary)],
                 foreground=[('selected', 'white')])

        # Scrollable styles for TTK
        style.configure('Vertical.TScrollbar', background=self._lighten_or_darken(bg, 0.05, theme),
                       troughcolor=self._lighten_or_darken(bg, 0.05, theme), borderwidth=0,
                       arrowcolor=fg)
        style.configure('Horizontal.TScrollbar', background=self._lighten_or_darken(bg, 0.05, theme),
                       troughcolor=self._lighten_or_darken(bg, 0.05, theme), borderwidth=0,
                       arrowcolor=fg)

    def _apply_to_root(self, theme: Theme) -> None:
        """
        Wendet das Theme auf das Root-Fenster an.

        Args:
            theme: Anzuwendendes Theme
        """
        if hasattr(self.gui, 'root'):
            colors = theme.colors

            # Setze Hintergrund des Hauptfensters
            self.gui.root.configure(background=colors.background)

            # Attempts to set the highlight color scheme (works for some platforms)
            try:
                self.gui.root.option_add('*selectBackground', colors.primary)
                self.gui.root.option_add('*selectForeground', 'white')
                self.gui.root.option_add('*activeBackground', self._lighten_or_darken(colors.primary, 0.1, theme))
                self.gui.root.option_add('*activeForeground', 'white')
            except Exception:
                pass

    def _apply_to_existing_widgets(self, theme: Theme) -> None:
        """
        Wendet das Theme auf bestehende Widgets an.

        Args:
            theme: Anzuwendendes Theme
        """
        colors = theme.colors

        # Rekursive Anwendung auf alle Widgets
        def apply_to_widget(widget):
            if isinstance(widget, (tk.Frame, tk.LabelFrame, tk.Canvas)):
                widget.configure(bg=colors.background)

            elif isinstance(widget, tk.Label):
                widget.configure(bg=colors.background, fg=colors.text)

                # Treat label with pictures separately
                if widget.cget('image') and not widget.cget('compound') == 'text':
                    # This is an image label, only change the background
                    widget.configure(bg=colors.background)

            elif isinstance(widget, (tk.Button, tk.Radiobutton)):
                widget.configure(bg=colors.primary, fg='white',
                               activebackground=self._lighten_or_darken(colors.primary, 0.1, theme),
                               activeforeground='white')

            elif isinstance(widget, (tk.Entry, tk.Text, tk.Spinbox)):
                widget.configure(bg=self._lighten_or_darken(colors.background, 0.05, theme),
                               fg=colors.text,
                               insertbackground=colors.text)  # Cursor-Farbe

                # Attempts to set scrollbar colors, if available
                if hasattr(widget, 'vbar') and widget.vbar:
                    try:
                        widget.vbar.configure(bg=self._lighten_or_darken(colors.background, 0.05, theme),
                                           troughcolor=self._lighten_or_darken(colors.background, 0.05, theme),
                                           activebackground=self._lighten_or_darken(colors.border, 0.1, theme))
                    except Exception:
                        pass

            elif isinstance(widget, tk.Listbox):
                widget.configure(bg=self._lighten_or_darken(colors.background, 0.03, theme),
                               fg=colors.text,
                               selectbackground=colors.primary,
                               selectforeground='white')

            elif isinstance(widget, (tk.Checkbutton, tk.Scale)):
                widget.configure(bg=colors.background, fg=colors.text,
                               activebackground=self._lighten_or_darken(colors.background, 0.05, theme))

            elif isinstance(widget, tk.Menu):
                widget.configure(bg=colors.background, fg=colors.text,
                               activebackground=colors.primary,
                               activeforeground='white')

            # Set new font for widgets with text content
            if hasattr(widget, 'cget') and 'font' in widget.keys():
                try:
                    current_font = widget.cget('font')
                    if isinstance(current_font, str):
                        # It is a named font or a font description
                        widget.configure(font=(theme.font_family.split(',')[0].strip(), theme.font_size))
                except Exception:
                    pass

            # Recursive for children widgets
            for child in widget.winfo_children():
                apply_to_widget(child)

        # Start recursion from root
        apply_to_widget(self.gui.root)

    def _lighten_or_darken(self, hex_color: str, amount: float, theme: Theme) -> str:
        """
        Hellt eine Farbe auf oder dunkelt sie ab.

        Args:
            hex_color: Hex-Farbcode (z.B. "#ffffff")
            amount: Betrag der Änderung (positiv zum Aufhellen, negativ zum Abdunkeln)
            theme: Theme-Instanz für Kontextinformationen

        Returns:
            Angepasster Hex-Farbcode
        """
        # Remove the #symbol and convert to RGB
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16) / 255.0, int(hex_color[2:4], 16) / 255.0, int(hex_color[4:6], 16) / 255.0

        # Lighten or darken based on the theme type
        if theme.type == ThemeType.DARK:
            amount = -amount  # Reverse for dark themes

        # Adjust the values
        r = max(0, min(1, r + amount))
        g = max(0, min(1, g + amount))
        b = max(0, min(1, b + amount))

        # Convert back to Hex
        r, g, b = int(r * 255), int(g * 255), int(b * 255)
        return f"#{r:02x}{g:02x}{b:02x}"

    def restore_original_style(self) -> None:
        """Stellt die ursprünglichen Stile wieder her."""
        try:
            style = ttk.Style()

            # Stelle ttk-Stile wieder her
            for element, props in self.original_styles.items():
                if element != 'root':
                    for key, value in props.items():
                        try:
                            style.configure(element, **{key: value})
                        except Exception:
                            pass

            # Stelle root-Stil wieder her
            if 'root' in self.original_styles:
                self.gui.root.configure(**self.original_styles['root'])

            logger.debug("Originale Stile wiederhergestellt")
        except Exception as e:
            logger.error(f"Fehler beim Wiederherstellen der originalen Stile: {e}")

    def get_theme_selection_frame(self, parent) -> tk.Frame:
        """
        Erstellt ein Frame zur Theme-Auswahl.

        Args:
            parent: Eltern-Widget

        Returns:
            Frame mit Theme-Auswahloptionen
        """
        frame = tk.Frame(parent, bg=self.current_theme.colors.background)

        # Erstelle Label
        tk.Label(frame, text="Theme auswählen:", bg=self.current_theme.colors.background,
               fg=self.current_theme.colors.text, anchor="w").pack(fill="x", pady=(10, 5))

        # Create ComboBox for theme selection
        theme_names = self.theme_manager.get_theme_names()
        current_theme = self.theme_manager.get_current_theme_name()

        theme_var = tk.StringVar(value=current_theme)
        theme_combo = ttk.Combobox(frame, values=theme_names, textvariable=theme_var, state="readonly")
        theme_combo.pack(fill="x", pady=5)

        # Erstelle Button zum Anwenden des Themes
        apply_btn = ttk.Button(frame, text="Theme anwenden",
                             command=lambda: self._change_theme(theme_var.get()))
        apply_btn.pack(fill="x", pady=5)

        # Erstelle Button zur Theme-Anpassung
        customize_btn = ttk.Button(frame, text="Theme anpassen",
                                 command=lambda: self._show_theme_customizer())
        customize_btn.pack(fill="x", pady=5)

        return frame

    def _change_theme(self, theme_name: str) -> None:
        """
        Ändert das aktuelle Theme.

        Args:
            theme_name: Name des zu verwendenden Themes
        """
        success = self.theme_manager.set_current_theme(theme_name)
        if success:
            self.apply_theme()
            # Show a notification If Available
            if hasattr(self.gui, 'show_notification'):
                self.gui.show_notification(f"Theme '{theme_name}' wurde angewendet", "info")

    def _show_theme_customizer(self) -> None:
        """Zeigt einen Dialog zur Theme-Anpassung an."""
        # Erstelle ein neues Fenster
        customizer = tk.Toplevel(self.gui.root)
        customizer.title("Theme anpassen")
        customizer.geometry("500x550")
        customizer.resizable(True, True)
        customizer.configure(bg=self.current_theme.colors.background)

        # Center the window
        customizer.transient(self.gui.root)
        customizer.grab_set()

        main_frame = tk.Frame(customizer, bg=self.current_theme.colors.background)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Theme-Name
        name_frame = tk.Frame(main_frame, bg=self.current_theme.colors.background)
        name_frame.pack(fill="x", pady=10)

        tk.Label(name_frame, text="Theme-Name:", bg=self.current_theme.colors.background, fg=self.current_theme.colors.text).pack(side="left")
        name_var = tk.StringVar(value=f"Custom_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        name_entry = ttk.Entry(name_frame, textvariable=name_var)
        name_entry.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # Theme-Typ
        type_frame = tk.Frame(main_frame, bg=self.current_theme.colors.background)
        type_frame.pack(fill="x", pady=10)

        tk.Label(type_frame, text="Theme-Typ:", bg=self.current_theme.colors.background, fg=self.current_theme.colors.text).pack(side="left")
        type_var = tk.StringVar(value="custom")
        type_combo = ttk.Combobox(type_frame, textvariable=type_var, values=["light", "dark", "custom"], state="readonly")
        type_combo.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # Farbauswahl-Frames
        colors_frame = tk.LabelFrame(main_frame, text="Farben", bg=self.current_theme.colors.background, fg=self.current_theme.colors.text)
        colors_frame.pack(fill="x", pady=10)

        # Function for creating color selection lines
        color_vars = {}

        def create_color_picker(parent, label, color_key, initial_color):
            frame = tk.Frame(parent, bg=self.current_theme.colors.background)
            frame.pack(fill="x", pady=5)

            tk.Label(frame, text=f"{label}:", bg=self.current_theme.colors.background,
                   fg=self.current_theme.colors.text, width=12, anchor="w").pack(side="left")

            color_var = tk.StringVar(value=initial_color)
            color_vars[color_key] = color_var

            color_preview = tk.Frame(frame, bg=initial_color, width=30, height=20, bd=1, relief="solid")
            color_preview.pack(side="left", padx=5)

            color_entry = ttk.Entry(frame, textvariable=color_var, width=8)
            color_entry.pack(side="left", padx=5)

            def update_preview(*args):
                try:
                    color = color_var.get()
                    if not color.startswith("#"):
                        color = f"#{color}"
                    color_preview.configure(bg=color)
                except Exception:
                    pass

            color_var.trace("w", update_preview)

            def open_color_picker():
                color = colorchooser.askcolor(initialcolor=color_var.get())
                if color[1]:
                    color_var.set(color[1])

            color_btn = ttk.Button(frame, text="Wählen", command=open_color_picker, width=8)
            color_btn.pack(side="left", padx=5)

            return frame

        # Create color voters for all colors
        colors = self.current_theme.colors.to_dict()
        for color_key, color_value in colors.items():
            label = color_key.capitalize().replace("_", " ")
            create_color_picker(colors_frame, label, color_key, color_value)

        # Font and size
        font_frame = tk.LabelFrame(main_frame, text="Schrift", bg=self.current_theme.colors.background, fg=self.current_theme.colors.text)
        font_frame.pack(fill="x", pady=10)

        # Schriftfamilie
        family_frame = tk.Frame(font_frame, bg=self.current_theme.colors.background)
        family_frame.pack(fill="x", pady=5)

        tk.Label(family_frame, text="Schriftart:", bg=self.current_theme.colors.background, fg=self.current_theme.colors.text).pack(side="left")

        # List of common fonts
        common_fonts = ["Arial", "Helvetica", "Verdana", "Tahoma", "Times New Roman", "Georgia", "Courier New", "Consolas"]
        font_var = tk.StringVar(value=self.current_theme.font_family.split(',')[0].strip())
        font_combo = ttk.Combobox(family_frame, textvariable=font_var, values=common_fonts)
        font_combo.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # Font size
        size_frame = tk.Frame(font_frame, bg=self.current_theme.colors.background)
        size_frame.pack(fill="x", pady=5)

        tk.Label(size_frame, text="Größe:", bg=self.current_theme.colors.background, fg=self.current_theme.colors.text).pack(side="left")
        size_var = tk.IntVar(value=self.current_theme.font_size)
        size_spin = ttk.Spinbox(size_frame, from_=8, to=16, textvariable=size_var, width=5)
        size_spin.pack(side="right")

        # Button-Frame
        button_frame = tk.Frame(main_frame, bg=self.current_theme.colors.background)
        button_frame.pack(fill="x", pady=(20, 10))

        def save_theme():
            # Sammle alle Werte
            new_theme = Theme(
                name=name_var.get(),
                type=ThemeType(type_var.get()),
                colors=ColorScheme(**{k: v.get() for k, v in color_vars.items()}),
                font_family=font_var.get(),
                font_size=size_var.get()
            )

            # Add the theme and apply it to it
            success = self.theme_manager.add_theme(new_theme)
            if success:
                self.theme_manager.set_current_theme(new_theme.name)
                self.apply_theme()
                customizer.destroy()

                # Show a notification If Available
                if hasattr(self.gui, 'show_notification'):
                    self.gui.show_notification(f"Theme '{new_theme.name}' wurde erstellt und angewendet", "info")

        save_btn = ttk.Button(button_frame, text="Speichern und anwenden", command=save_theme)
        save_btn.pack(side="right", padx=5)

        cancel_btn = ttk.Button(button_frame, text="Abbrechen", command=customizer.destroy)
        cancel_btn.pack(side="right", padx=5)


# Example code for use in the GUI
if __name__ == "__main__":
    import tkinter as tk
    from tkinter import ttk

    # Konfiguriere Logging
    logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Erstelle ein einfaches Test-GUI
    root = tk.Tk()
    root.title("Theme-Test")
    root.geometry("800x600")

    # Mock Gui class for the test
    class MockGUI:
        def __init__(self):
            self.root = root

        def show_notification(self, message, level):
            print(f"[{level.upper()}] {message}")

    # Create the frame with different widgets
    main_frame = ttk.Frame(root)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Erstelle einige Test-Widgets
    ttk.Label(main_frame, text="Dies ist ein Test für das Theme-System").pack(pady=10)

    ttk.Button(main_frame, text="Standard-Button").pack(pady=5)
    ttk.Button(main_frame, text="Sekundär-Button", style="Secondary.TButton").pack(pady=5)

    ttk.Entry(main_frame).pack(fill="x", pady=5)

    check_var = tk.BooleanVar()
    ttk.Checkbutton(main_frame, text="Checkbox", variable=check_var).pack(pady=5)

    combo = ttk.Combobox(main_frame, values=["Option 1", "Option 2", "Option 3"])
    combo.set("Wähle eine Option")
    combo.pack(pady=5)

    notebook = ttk.Notebook(main_frame)
    tab1 = ttk.Frame(notebook)
    tab2 = ttk.Frame(notebook)
    notebook.add(tab1, text="Tab 1")
    notebook.add(tab2, text="Tab 2")
    notebook.pack(fill="both", expand=True, pady=10)

    # Erstelle eine Treeview
    tree = ttk.Treeview(tab1, columns=("col1", "col2"))
    tree.heading("#0", text="Element")
    tree.heading("col1", text="Wert 1")
    tree.heading("col2", text="Wert 2")
    tree.insert("", "end", text="Eintrag 1", values=("Daten 1", "Mehr Daten"))
    tree.insert("", "end", text="Eintrag 2", values=("Daten 2", "Noch mehr"))
    tree.pack(fill="both", expand=True, pady=10)

    # Erstelle den ThemeIntegrator
    gui = MockGUI()
    theme_integrator = ThemeIntegrator(gui)

    # Add theme selection
    theme_frame = theme_integrator.get_theme_selection_frame(tab2)
    theme_frame.pack(fill="both", expand=True, padx=20, pady=20)

    root.mainloop()
