#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""ROM SARTER Pro configuration adapter for the new architecture Phase 1 Implementation: Desktop optimization and integration This module extends the existing configuration component to Support of the new features of phase 1."""

import os
import logging
import sys
import json
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

# Import the base class from config
from ..config import Config as BaseConfig, ConfigError

# Configure logging
logger = logging.getLogger(__name__)

class EnhancedConfig(BaseConfig):
    """Extended configuration class that supports the new architecture. Inherits from the existing configuration class and adds new functionalities."""

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
        """Initialized the extended configuration. Args: Config_Path: Optional path to the configuration file *Args, ** Kwargs: More parameters for the basic class"""
        # Initialization of the basic class
        # Super ().__ init __ () is avoided to prevent circular imports
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), '..', 'config.json')

        # Initialize the configuration with standard values
        self._config = {}
        self._load_config()

# Make sure that the extensions are available in the configuration
        self._ensure_extensions()

# Record the successful initialization
        logger.info("Erweiterte Konfiguration initialisiert")

    def _ensure_extensions(self):
        """Make sure that all the necessary extended configuration options are available. Add missing options with standard values."""
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
        """Gives back the configuration for the scanner. Return: Dictionary with scanner configuration options"""
        return self._config.get("scanner", self.DEFAULT_CONFIG_EXTENSION["scanner"])

    def get_ui_config(self) -> Dict[str, Any]:
        """Gives back the configuration for the user interface. Return: Dictionary with UI configuration options"""
        return self._config.get("ui", self.DEFAULT_CONFIG_EXTENSION["ui"])

    def get_database_config(self) -> Dict[str, Any]:
        """Gives back the configuration for the database. Return: Dictionary with database configuration options"""
        return self._config.get("database", self.DEFAULT_CONFIG_EXTENSION["database"])

    def get_cache_config(self) -> Dict[str, Any]:
        """Gives back the configuration for the cache. Return: Dictionary with cache configuration options"""
        return self._config.get("cache", self.DEFAULT_CONFIG_EXTENSION["cache"])

    def set_scanner_option(self, option: str, value: Any) -> bool:
        """Set A Scanner Configuration option. ARGS: Option: Name of the Option Value: New Value Return: True, IF Successful, False in the event of errors"""
        return self.set(f"scanner.{option}", value)

    def set_ui_option(self, option: str, value: Any) -> bool:
        """Set a ui configuration option. ARGS: Option: Name of the Option Value: New Value Return: True, IF Successful, False in the event of errors"""
        return self.set(f"ui.{option}", value)

    def set_database_option(self, option: str, value: Any) -> bool:
        """Set A Database Configuration option. ARGS: Option: Name of the Option Value: New Value Return: True, IF Successful, False in the event of errors"""
        return self.set(f"database.{option}", value)

    def set_cache_option(self, option: str, value: Any) -> bool:
        """Set a cache configuration option. ARGS: Option: Name of the Option Value: New Value Return: True, IF Successful, False in the event of errors"""
        return self.set(f"cache.{option}", value)

    def get_ui_theme(self) -> str:
        """Gives back the configured UI theme. Return: Name of the theme ('System', 'Light', 'Dark')"""
        return self.get_ui_config().get("theme", "system")

    def get_ui_language(self) -> str:
        """Gives back the configured UI language. Return: Language code (e.g. 'de_de')"""
        return self.get_ui_config().get("language", "de_DE")

    def get_max_threads(self) -> int:
        """Gives back the maximum number of threads for the scanner. Return: Maximum number of thread (0 for automatic)"""
        threads = self.get_scanner_config().get("max_threads", 0)

# If automatically (0), calculated based on CPU cores
        if threads == 0:
            import os
            cpu_count = os.cpu_count() or 4
            threads = max(2, cpu_count)

        return threads

    def should_use_high_performance(self) -> bool:
        """Indicates whether the high performance scanner should be used. Return: True if the high-performance scanner is to be used, False for the classic scanner"""
        return self.get_scanner_config().get("use_high_performance", True)

    def validate_scanner_config(self) -> List[str]:
        """Check the validity of the scanner configuration. Return: List of error messages (empty list if no errors)"""
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
        """Check the validity of the UI configuration. Return: List of error messages (empty list if no errors)"""
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

    def _load_config(self) -> None:
        """Loads the configuration from the file or initializes it with standard values."""
        try:
            # Check whether the file exists
            if os.path.exists(self.config_path):
                import json
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    try:
                        self._config = json.load(f)
                        logger.info(f"Konfiguration aus {self.config_path} geladen")
                    except json.JSONDecodeError as e:
                        logger.error(f"Fehler beim Laden der Konfiguration: {e}")
                        # Initialize with Standard Values for Errors
                        self._config = {}
            else:
                logger.info(f"Konfigurationsdatei {self.config_path} nicht gefunden, verwende Standardwerte")
                self._config = {}
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim Laden der Konfiguration: {e}")
            self._config = {}

    def save(self) -> bool:
        """Saves the configuration in the file. Return: True, if successful, false in the event of errors"""
        try:
            # Make sure the directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            import json
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4)

            logger.info(f"Konfiguration in {self.config_path} gespeichert")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Konfiguration: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Gives back the value for a key. Args: key: key (can use point notation for nested keys) default: default value if the key was not found: value or default, if not found"""
        parts = key.split('.')
        current = self._config

        for part in parts:
            if part not in current:
                return default
            current = current[part]

        return current

    def set(self, key: str, value: Any) -> bool:
        """Sets the value for a key. Args: Key: Key (can use point notation for nested keys) Value: Return: True, IF Successful, False in the event of errors"""
        try:
            parts = key.split('.')
            current = self._config

            # Navigiere zur letzten Ebene
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Setze den Wert
            current[parts[-1]] = value

            return True
        except Exception as e:
            logger.error(f"Fehler beim Setzen der Konfiguration: {e}")
            return False

# Create a global instance of the extended configuration
enhanced_config_instance = None

def get_enhanced_config(config_path: Optional[str] = None) -> EnhancedConfig:
    """Returns the Global Instance of the Extended Configuration or Create a New One IF None Still Exists. ARGS: Config_Path: Optional path to the configuration File Return: Enhanancedconfig Instance"""
    global enhanced_config_instance

    if enhanced_config_instance is None:
        enhanced_config_instance = EnhancedConfig(config_path)

    return enhanced_config_instance

# Initialize the extended configuration, but only if necessary
# get_enhanced_config () - is only called when needed

# Erstelle eine initiale Instanz
enhanced_config_instance = EnhancedConfig()
