#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Konfigurationspaket
Phase 1 Implementation: Desktop-Optimierung und Integration

Dieses Modul initialisiert das Konfigurationspaket und stellt Hilfsfunktionen bereit.
"""

from pathlib import Path
import sys
import os

# Import the global configuration
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config, config_instance

# Export the Enhanced_Config for use
try:
    from .enhanced_config import EnhancedConfig, get_enhanced_config
except ImportError:
# Fallback, if Enhanced_Config does not yet exist
    EnhancedConfig = Config
    get_enhanced_config = lambda: config_instance

# List of publicly available names for import
__all__ = ['Config', 'EnhancedConfig', 'config_instance', 'get_enhanced_config']
