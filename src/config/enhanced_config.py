#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Konfigurationsadapter für die neue Architektur
Phase 1 Implementation: Desktop-Optimierung und Integration

Dieses Modul erweitert die bestehende Konfigurationskomponente um die
Unterstützung der neuen Features der Phase 1.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

# Import the existing configuration
from ..config import Config as BaseConfig, ConfigError, config_instance

# Configure logging
logger = logging.getLogger(__name__)

class EnhancedConfig(BaseConfig):
    """
    Erweiterte Konfigurationsklasse, die die neue Architektur unterstützt.
    Erbt von der bestehenden Konfigurationsklasse und fügt neue Funktionalitäten hinzu.
    """

# New standard configuration options for expanded functionality
    DEFAULT_CONFIG_EXTENSION = {
# Scanner configuration
        "scanner": {
            "use_high_performance": True,
            "max_threads": 0,  # 0 = Automatisch basierend auf CPU-Kernen
            "chunk_size": 4 * 1024 * 1024,  # 4 MB chunk size for large files
            "follow_symlinks": False,
            "use_cache": True,
            "recursive": True,
            "max_depth": -1,  # -1 = Unbegrenzte Tiefe
        },

# Desktop UI configuration
        "ui": {
            "theme": "system",  # "system", "light", "dark"
            "language": "de_DE",
            "remember_window_state": True,
            "remember_last_directories": True,
            "show_tooltips": True,
            "animation_speed": 1.0,  # Multiplier for animation speed
            "icon_size": "medium",  # "small", "medium", "large"
            "enable_drag_drop": True,
            "show_status_bar": True,
            "show_toolbar": True,
        },

# Database configuration
        "database": {
            "use_memory_cache": True,
            "cache_size_mb": 100,
            "auto_backup": True,
            "backup_interval_days": 7,
            "backup_max_count": 10,
            "vacuum_on_exit": True,
        },

# Cache configuration
        "cache": {
            "enabled": True,
            "max_size_mb": 500,
            "clean_on_exit": False,
            "expiry_days": 30,
        }
    }

    def __init__(self, config_path: Optional[str] = None, *args, **kwargs):
        """
        Initialisiert die erweiterte Konfiguration.

        Args:
            config_path: Optionaler Pfad zur Konfigurationsdatei
            *args, **kwargs: Weitere Parameter für die Basisklasse
        """
# Call initialization method of the basic class
        super().__init__(config_path=config_path, *args, **kwargs)

# Make sure that the extensions are available in the configuration
        self._ensure_extensions()

# Record the successful initialization
        logger.info("Erweiterte Konfiguration initialisiert")

    def _ensure_extensions(self):
        """
        Stellt sicher, dass alle notwendigen erweiterten Konfigurationsoptionen vorhanden sind.
        Fügt fehlende Optionen mit Standardwerten hinzu.
        """
        modified = False

# Add the new configuration sections if they do not exist
        for section, options in self.DEFAULT_CONFIG_EXTENSION.items():
            if section not in self._config:
                logger.info(f"Füge neuen Konfigurationsabschnitt '{section}' hinzu")
                self._config[section] = {}
                modified = True

# Add missing options in each section
            for option, default_value in options.items():
                if option not in self._config[section]:
                    logger.debug(f"Füge neue Konfigurationsoption '{section}.{option}' hinzu")
                    self._config[section][option] = default_value
                    modified = True

# Save the configuration if changes have been made
        if modified:
            self.save()

    def get_scanner_config(self) -> Dict[str, Any]:
        """
        Gibt die Konfiguration für den Scanner zurück.

        Returns:
            Dictionary mit Scanner-Konfigurationsoptionen
        """
        return self._config.get("scanner", self.DEFAULT_CONFIG_EXTENSION["scanner"])

    def get_ui_config(self) -> Dict[str, Any]:
        """
        Gibt die Konfiguration für die Benutzeroberfläche zurück.

        Returns:
            Dictionary mit UI-Konfigurationsoptionen
        """
        return self._config.get("ui", self.DEFAULT_CONFIG_EXTENSION["ui"])

    def get_database_config(self) -> Dict[str, Any]:
        """
        Gibt die Konfiguration für die Datenbank zurück.

        Returns:
            Dictionary mit Datenbank-Konfigurationsoptionen
        """
        return self._config.get("database", self.DEFAULT_CONFIG_EXTENSION["database"])

    def get_cache_config(self) -> Dict[str, Any]:
        """
        Gibt die Konfiguration für den Cache zurück.

        Returns:
            Dictionary mit Cache-Konfigurationsoptionen
        """
        return self._config.get("cache", self.DEFAULT_CONFIG_EXTENSION["cache"])

    def set_scanner_option(self, option: str, value: Any) -> bool:
        """
        Setzt eine Scanner-Konfigurationsoption.

        Args:
            option: Name der Option
            value: Neuer Wert

        Returns:
            True, wenn erfolgreich, False bei Fehler
        """
        return self.set(f"scanner.{option}", value)

    def set_ui_option(self, option: str, value: Any) -> bool:
        """
        Setzt eine UI-Konfigurationsoption.

        Args:
            option: Name der Option
            value: Neuer Wert

        Returns:
            True, wenn erfolgreich, False bei Fehler
        """
        return self.set(f"ui.{option}", value)

    def set_database_option(self, option: str, value: Any) -> bool:
        """
        Setzt eine Datenbank-Konfigurationsoption.

        Args:
            option: Name der Option
            value: Neuer Wert

        Returns:
            True, wenn erfolgreich, False bei Fehler
        """
        return self.set(f"database.{option}", value)

    def set_cache_option(self, option: str, value: Any) -> bool:
        """
        Setzt eine Cache-Konfigurationsoption.

        Args:
            option: Name der Option
            value: Neuer Wert

        Returns:
            True, wenn erfolgreich, False bei Fehler
        """
        return self.set(f"cache.{option}", value)

    def get_ui_theme(self) -> str:
        """
        Gibt das konfigurierte UI-Theme zurück.

        Returns:
            Name des Themes ('system', 'light', 'dark')
        """
        return self.get_ui_config().get("theme", "system")

    def get_ui_language(self) -> str:
        """
        Gibt die konfigurierte UI-Sprache zurück.

        Returns:
            Sprachcode (z.B. 'de_DE')
        """
        return self.get_ui_config().get("language", "de_DE")

    def get_max_threads(self) -> int:
        """
        Gibt die maximale Anzahl von Threads für den Scanner zurück.

        Returns:
            Maximale Thread-Anzahl (0 für automatisch)
        """
        threads = self.get_scanner_config().get("max_threads", 0)

# If automatically (0), calculated based on CPU cores
        if threads == 0:
            import os
            cpu_count = os.cpu_count() or 4
            threads = max(2, cpu_count)

        return threads

    def should_use_high_performance(self) -> bool:
        """
        Gibt an, ob der High-Performance-Scanner verwendet werden soll.

        Returns:
            True, wenn der High-Performance-Scanner verwendet werden soll,
            False für den klassischen Scanner
        """
        return self.get_scanner_config().get("use_high_performance", True)

    def validate_scanner_config(self) -> List[str]:
        """
        Überprüft die Gültigkeit der Scanner-Konfiguration.

        Returns:
            Liste von Fehlermeldungen (leere Liste, wenn keine Fehler)
        """
        errors = []
        scanner_config = self.get_scanner_config()

# Check max_threads
        max_threads = scanner_config.get("max_threads", 0)
        if not isinstance(max_threads, int):
            errors.append("max_threads muss eine Ganzzahl sein")
        elif max_threads < 0:
            errors.append("max_threads darf nicht negativ sein")

# Check chunk_size
        chunk_size = scanner_config.get("chunk_size", 4 * 1024 * 1024)
        if not isinstance(chunk_size, int):
            errors.append("chunk_size muss eine Ganzzahl sein")
        elif chunk_size <= 0:
            errors.append("chunk_size muss positiv sein")

# Check Max_deth
        max_depth = scanner_config.get("max_depth", -1)
        if not isinstance(max_depth, int):
            errors.append("max_depth muss eine Ganzzahl sein")

        return errors

    def validate_ui_config(self) -> List[str]:
        """
        Überprüft die Gültigkeit der UI-Konfiguration.

        Returns:
            Liste von Fehlermeldungen (leere Liste, wenn keine Fehler)
        """
        errors = []
        ui_config = self.get_ui_config()

# Check theme
        theme = ui_config.get("theme", "system")
        if theme not in ["system", "light", "dark"]:
            errors.append(f"Ungültiges Theme: {theme}")

# Check animation_speed
        animation_speed = ui_config.get("animation_speed", 1.0)
        if not isinstance(animation_speed, (int, float)):
            errors.append("animation_speed muss eine Zahl sein")
        elif animation_speed < 0:
            errors.append("animation_speed darf nicht negativ sein")

# Check icon_size
        icon_size = ui_config.get("icon_size", "medium")
        if icon_size not in ["small", "medium", "large"]:
            errors.append(f"Ungültige Symbolgröße: {icon_size}")

        return errors

# Create a global instance of the extended configuration
enhanced_config_instance = None

def get_enhanced_config(config_path: Optional[str] = None) -> EnhancedConfig:
    """
    Gibt die globale Instanz der erweiterten Konfiguration zurück
    oder erstellt eine neue, wenn noch keine existiert.

    Args:
        config_path: Optionaler Pfad zur Konfigurationsdatei

    Returns:
        EnhancedConfig-Instanz
    """
    global enhanced_config_instance

    if enhanced_config_instance is None:
        enhanced_config_instance = EnhancedConfig(config_path)

    return enhanced_config_instance

# Initialize the extended configuration when importing the module
get_enhanced_config()
