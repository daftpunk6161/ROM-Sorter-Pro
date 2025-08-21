"""
ROM Sorter Pro - Erweiterte Theme Integration

Dieses Modul verbessert die Theme-Integration, indem es sicherstellt,
dass alle UI-Komponenten ein einheitliches Erscheinungsbild haben.
Es überwacht Änderungen am aktiven Theme und wendet diese auf alle
registrierten Widgets an.
"""

import tkinter as tk
from tkinter import ttk
import os
import sys
import logging
from typing import Dict, List, Any, Optional, Set, Callable

# Logger konfigurieren
logger = logging.getLogger(__name__)

# Theme-Manager importieren
from .theme_manager import ThemeManager, Theme, ThemeType, ColorScheme
from .theme_integration import ThemeIntegrator

# Weak references for garbage collection
import weakref

# Cache for widget styles
_style_cache: Dict[str, Dict[str, Any]] = {}
_widget_registry: Set[weakref.ReferenceType] = set()
_theme_callbacks: List[Callable[[Theme], None]] = []

# Globaler Theme-Manager
_global_theme_manager = ThemeManager()


def get_current_theme() -> Theme:
    """
    Gibt das aktuell aktive Theme zurück.

    Returns:
        Das aktuelle Theme
    """
    return _global_theme_manager.get_theme()


def apply_theme_to_widget(widget: tk.Widget, theme: Optional[Theme] = None) -> None:
    """
    Wendet ein Theme auf ein Widget und seine Kinder an.

    Args:
        widget: Das Widget, auf das das Theme angewendet werden soll
        theme: Optionales Theme, standardmäßig das aktuelle Theme
    """
    if theme is None:
        theme = get_current_theme()

    # Apply the theme to the widget itself
    _apply_theme_to_single_widget(widget, theme)

    # Apply the theme to all children
    for child in widget.winfo_children():
        apply_theme_to_widget(child, theme)


def register_for_theme_updates(widget: tk.Widget) -> None:
    """
    Registriert ein Widget für automatische Theme-Updates.

    Args:
        widget: Das Widget, das bei Theme-Änderungen aktualisiert werden soll
    """
    # Use weak reference to avoid memory leaks
    _widget_registry.add(weakref.ref(widget))


def register_theme_callback(callback: Callable[[Theme], None]) -> None:
    """
    Registriert einen Callback, der bei Theme-Änderungen aufgerufen wird.

    Args:
        callback: Die Funktion, die aufgerufen werden soll
    """
    _theme_callbacks.append(callback)


def set_theme(theme_name: str) -> bool:
    """
    Setzt ein neues Theme und wendet es auf alle registrierten Widgets an.

    Args:
        theme_name: Der Name des Themes ('light', 'dark', 'custom', etc.)

    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        # Theme im Theme-Manager setzen
        if _global_theme_manager.set_active_theme(theme_name):
            # Neue Theme-Instanz abrufen
            theme = _global_theme_manager.get_theme()

            # Anwenden auf alle registrierten Widgets
            _update_all_registered_widgets(theme)

            # Callbacks aufrufen
            for callback in _theme_callbacks:
                try:
                    callback(theme)
                except Exception as e:
                    logger.error(f"Fehler im Theme-Callback: {e}")

            logger.info(f"Theme '{theme_name}' erfolgreich angewendet")
            return True
    except Exception as e:
        logger.error(f"Fehler beim Anwenden des Themes '{theme_name}': {e}")

    return False


def _update_all_registered_widgets(theme: Theme) -> None:
    """
    Aktualisiert alle registrierten Widgets mit dem neuen Theme.

    Args:
        theme: Das anzuwendende Theme
    """
    # Remove invalid references and update valid widgets
    global _widget_registry
    valid_refs = set()

    for widget_ref in _widget_registry:
        widget = widget_ref()
        if widget is not None:
            try:
                # Check whether the widget still exists
                widget.winfo_exists()
                apply_theme_to_widget(widget, theme)
                valid_refs.add(widget_ref)
            except Exception:
                # Widget no longer exists
                pass

    # Update the registry
    _widget_registry = valid_refs


def _apply_theme_to_single_widget(widget: tk.Widget, theme: Theme) -> None:
    """
    Wendet ein Theme auf ein einzelnes Widget an.

    Args:
        widget: Das Widget, auf das das Theme angewendet werden soll
        theme: Das anzuwendende Theme
    """
    try:
        widget_class = widget.__class__.__name__

        # Get the color palette
        colors = theme.get_color_scheme()

        # Common properties for all widgets
        common_props = {
            'background': colors.background,
            'foreground': colors.text
        }

        # Special properties depending on the widget type
        if widget_class in ('Button', 'TButton'):
            props = {
                'background': colors.primary,
                'foreground': '#ffffff',
                'activebackground': _adjust_color(colors.primary, 1.1),
                'activeforeground': '#ffffff',
                'relief': 'raised',
                'borderwidth': 0
            }
        elif widget_class in ('Entry', 'TEntry'):
            props = {
                'background': '#ffffff',
                'foreground': colors.text,
                'insertbackground': colors.text  # Cursor-Farbe
            }
        elif widget_class in ('Listbox', 'Treeview'):
            props = {
                'background': '#ffffff',
                'foreground': colors.text,
                'selectbackground': colors.primary,
                'selectforeground': '#ffffff'
            }
        elif widget_class in ('Frame', 'TFrame', 'Canvas'):
            props = {
                'background': colors.background
            }
        elif widget_class in ('Label', 'TLabel'):
            props = common_props
        else:
            # Standard properties for unknown widgets
            props = common_props

        # Apply the properties
        for prop, value in props.items():
            try:
                widget.configure(**{prop: value})
            except Exception:
                # Property is not supported by the widget
                pass

    except Exception as e:
        # Ignorize error for widgets that do not support certain properties
        pass


def _adjust_color(color: str, factor: float) -> str:
    """
    Passt eine Farbe an (heller/dunkler).

    Args:
        color: Hex-Farbcode (z.B. "#3498db")
        factor: Faktor > 1.0 für hellere, < 1.0 für dunklere Farbe

    Returns:
        Angepasster Hex-Farbcode
    """
    try:
        # Convert hex to rgb
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)

        # Passe Helligkeit an
        r = min(255, max(0, int(r * factor)))
        g = min(255, max(0, int(g * factor)))
        b = min(255, max(0, int(b * factor)))

        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return color


def initialize_theme_system(root_widget: tk.Widget) -> None:
    """
    Initialisiert das Theme-System und wendet das Standardtheme an.

    Args:
        root_widget: Das Root-Widget der Anwendung
    """
    # Register the root widget for theme updates
    register_for_theme_updates(root_widget)

    # Apply the current theme to the root widget
    apply_theme_to_widget(root_widget)

    logger.info("Theme-System initialisiert")
