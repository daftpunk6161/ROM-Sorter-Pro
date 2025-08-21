#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Configuration Package v2.1.8

This module initializes the configuration package and provides helper functions.
The package is organized in a modular way to improve maintainability.
"""

from pathlib import Path
import sys
import os
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Import modular components
from .modules import BaseConfigModule
from .modules.performance import PerformanceConfig
from .modules.sorting import SortingConfig
from .modules.ai import AIConfig

# Import the configuration manager
from .manager import ConfigManager, default_config

# For backward compatibility
class Config:
    """Base configuration class for backward compatibility"""
    def __init__(self):
        self.config_data = {}

    def load_config(self):
        """Load configuration"""
        pass

    def get(self, key, default=None):
        """Get value for a key"""
        return default

class ConfigError(Exception):
    """Fehler bei der Konfiguration."""
    pass

def load_config(config_path=None):
    """
    Lädt die Konfiguration aus einer Datei

    Args:
        config_path: Optionaler Pfad zur Konfigurationsdatei

    Returns:
        Dictionary mit der geladenen Konfiguration oder leeres Dictionary bei Fehler
    """
    if config_path is None:
        # Standardpfad verwenden
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')

    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"Konfigurationsdatei {config_path} nicht gefunden")
            return {}
    except Exception as e:
        logger.error(f"Fehler beim Laden der Konfiguration: {e}")
        return {}

# Erzeuge eine Standard-Instanz
config_instance = Config()

# Importing the extended configuration without causing circular imports
def get_enhanced_config():
    """
    Liefert die erweiterte Konfigurationsinstanz.
    Hinweis: Diese Funktion wird später durch die richtige Implementierung
    in enhanced_config.py ersetzt.
    """
    return config_instance

# Import the extended configuration only after defining the auxiliary functions
from .enhanced_config import EnhancedConfig, get_enhanced_config as get_enhanced_config_impl

# Overwritten the preliminary function with the correct implementation
get_enhanced_config = get_enhanced_config_impl

# List of the publicly available names for import
__all__ = ['Config', 'EnhancedConfig', 'ConfigError', 'load_config', 'get_enhanced_config']
