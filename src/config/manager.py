#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROM Sorter Pro - Configuration Manager Module

This module contains the centralized configuration manager that integrates
all the modular configuration components.
"""

import os
import json
import logging
import threading
from typing import Dict, List, Any
from datetime import datetime

from .modules.perf_settings import PerformanceConfig
from .modules.sorting import SortingConfig
from .modules.ai import AIConfig
from ..exceptions import ConfigurationError

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Centralized configuration manager that integrates all modular components.

    This class loads, validates, and provides access to all configuration modules
    while maintaining backward compatibility with the original design.
    """

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the configuration manager.

        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self._config_lock = threading.RLock()

        # Initialize configuration components
        self.performance = PerformanceConfig()
        self.sorting = SortingConfig()
        self.ai = AIConfig()
        self._metadata = {
            "version": "2.1.8",
            "description": "ROM Sorter Pro - Modular Configuration",
            "last_updated": datetime.now().isoformat()
        }

        # Load configuration if file exists
        if os.path.exists(config_path):
            self._load_config()

    def _load_config(self):
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # Update metadata
            if "_metadata" in config_data:
                self._metadata = config_data["_metadata"]

            # Load performance configuration
            if "performance" in config_data:
                self.performance = PerformanceConfig(**config_data["performance"])

            # Load sorting configuration
            if "features" in config_data and "sorting" in config_data["features"]:
                self.sorting = SortingConfig(**config_data["features"]["sorting"])

            # Load AI configuration
            if "features" in config_data and "ai_features" in config_data["features"]:
                self.ai = AIConfig(**config_data["features"]["ai_features"])

            logger.info(f"Configuration loaded from {self.config_path}")

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing configuration: {e}")
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")

        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def save_config(self):
        """Save configuration to file."""
        # Update metadata
        self._metadata["last_updated"] = datetime.now().isoformat()

        # Prepare configuration data
        config_data = {
            "_metadata": self._metadata,
            "performance": self.performance.to_dict(),
            "features": {
                "sorting": self.sorting.to_dict(),
                "ai_features": self.ai.to_dict()
            }
        }

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)

            with self._config_lock:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4)

            logger.info(f"Configuration saved to {self.config_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise ConfigurationError(f"Failed to save configuration: {e}")

    def validate_configuration(self) -> List[str]:
        """
        Validate all configuration components.

        Returns:
            List of validation errors, empty if valid
        """
        errors = []

        # Validate all components
        # This could be extended with component-specific validation

        return errors

    def get_section_dict(self, section: str) -> dict:
        """
        Get configuration section as dictionary.

        Args:
            section: Section name (performance, sorting, ai)

        Returns:
            Dictionary with section configuration
        """
        if section == "performance":
            return self.performance.to_dict()
        elif section == "sorting":
            return self.sorting.to_dict()
        elif section == "ai":
            return self.ai.to_dict()
        else:
            raise KeyError(f"Unknown configuration section: {section}")

    def update_section(self, section: str, updates: dict):
        """
        Update configuration section.

        Args:
            section: Section name (performance, sorting, ai)
            updates: Dictionary with updates
        """
        with self._config_lock:
            if section == "performance":
                self.performance = PerformanceConfig(**{**self.performance.to_dict(), **updates})
            elif section == "sorting":
                self.sorting = SortingConfig(**{**self.sorting.to_dict(), **updates})
            elif section == "ai":
                self.ai = AIConfig(**{**self.ai.to_dict(), **updates})
            else:
                raise KeyError(f"Unknown configuration section: {section}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get configuration summary.

        Returns:
            Dictionary with configuration summary
        """
        return {
            "version": self._metadata.get("version", "2.1.8"),
            "last_updated": self._metadata.get("last_updated", "N/A"),
            "components": {
                "performance": self.performance.to_dict(),
                "sorting": self.sorting.to_dict(),
                "ai": self.ai.to_dict()
            }
        }


# Create a default instance for global use
default_config = ConfigManager()
