#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ROM SARTER PRO THE SETTIONS This module defines the standard themes and paths for custom themes."""

import os
from pathlib import Path

# Pfad zur benutzerdefinierten Theme-Datei
CUSTOM_THEME_PATH = os.path.join(os.path.expanduser("~"), ".rom_sorter_pro", "themes", "custom_theme.json")

# Standard-Theme-Einstellungen
THEME_SETTINGS = {
    "light": {
        "bg_primary": "#f0f0f0",
        "bg_secondary": "#e0e0e0",
        "bg_accent": "#d0d0d0",
        "text_primary": "#000000",
        "text_secondary": "#333333",
        "accent": "#0078d7",
        "accent_hover": "#1e90ff",
        "success": "#28a745",
        "warning": "#ffc107",
        "error": "#dc3545",
        "border": "#c0c0c0"
    },
    "dark": {
        "bg_primary": "#2b2b2b",
        "bg_secondary": "#3c3c3c",
        "bg_accent": "#4a4a4a",
        "text_primary": "#ffffff",
        "text_secondary": "#cccccc",
        "accent": "#0078d7",
        "accent_hover": "#1e90ff",
        "success": "#28a745",
        "warning": "#ffc107",
        "error": "#dc3545",
        "border": "#555555"
    }
}

def get_theme_path():
    """Gives back the path to the theme directory and creates it if necessary Return: Path: path to the theme directory"""
    theme_dir = Path(os.path.expanduser("~")) / ".rom_sorter_pro" / "themes"
    theme_dir.mkdir(parents=True, exist_ok=True)
    return theme_dir

def get_default_theme_settings(theme_name="system"):
    """Gives Back the Standard Theme Settings for A Specific Theme Args: Theme_Name: Name of the Themes ('Light', 'Dark' Or 'System') Return: Dict: Theme Settings"""
    if theme_name == "system":
        # Systemeinstellung ermitteln
        import platform
        if platform.system() == "Windows":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                   r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    return THEME_SETTINGS["light"] if value == 1 else THEME_SETTINGS["dark"]
            except Exception as exc:
                import logging

                logging.getLogger(__name__).debug("Theme settings: Windows theme detection failed: %s", exc)

        # Fallback if the system setting cannot be determined
        return THEME_SETTINGS["light"]

    elif theme_name in THEME_SETTINGS:
        return THEME_SETTINGS[theme_name]

    # Fallback
    return THEME_SETTINGS["light"]
