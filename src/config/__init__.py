#!/usr/bin/env python3
# -*-coding: utf-8-*-
# ruff: noqa: E402,F401
"""Rome Sarter Pro - Configuration Package V2.1.8 This module Initialities the Configuration Package and Provides Helper Functions. The package is organized in a modular way to improve."""

import logging
from typing import Any, Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Import modular components
from .modules import BaseConfigModule
from .modules.performance import PerformanceConfig
from .modules.sorting import SortingConfig
from .modules.ai import AIConfig

# Import the configuration manager
from .manager import ConfigManager, default_config

# I/O + schema helpers
from .io import get_config_path, load_config as load_config_data, save_config
from .schema import validate_config_schema

# For backward compatibility
class Config:
    """Simple configuration wrapper for backward compatibility."""

    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        self.config_data = config_data or {}

    def load_config(self, config_path: Optional[str] = None) -> "Config":
        self.config_data = load_config_data(config_path)
        return self

    def get(self, key, default=None):
        return self.config_data.get(key, default)

    def set(self, key, value) -> None:
        self.config_data[key] = value

    def save(self, config_path: Optional[str] = None) -> bool:
        return save_config(self.config_data, config_path)

class ConfigError(Exception):
    """Configuration error."""
    pass

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration data."""
    return load_config_data(config_path)

# Erzeuge eine Standard-Instanz
config_instance = Config()

# Import the extended configuration lazily to avoid circular imports
from .enhanced_config import EnhancedConfig


def get_enhanced_config():
    """Delivers the extended configuration instance."""
    from .enhanced_config import get_enhanced_config as get_enhanced_config_impl

    return get_enhanced_config_impl()

# List of the publicly available names for import
__all__ = [
    'Config',
    'EnhancedConfig',
    'ConfigError',
    'BaseConfigModule',
    'PerformanceConfig',
    'SortingConfig',
    'AIConfig',
    'ConfigManager',
    'default_config',
    'load_config',
    'get_enhanced_config',
    'get_config_path',
    'save_config',
    'validate_config_schema',
]
