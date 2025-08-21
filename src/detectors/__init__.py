#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""Rome Sorter Pro - Detector Package This package contains all detector modules for the detection of ROM types, including console, archive and CHD detectors."""

# Import and re-export of the basic functions
from .base_detector import BaseDetector
from .console_detector import (
    detect_console_from_file,
    detect_console_from_path,
    detect_console_from_name,
    detect_console_fast,
    detect_console_by_extension
)
from .archive_detector import detect_console_from_archive, is_archive_file
from .chd_detector import detect_console_from_chd, is_chd_file

# Import and re-export of the ML detector functions
try:
    from .ml_detector import detect_console_with_ml, MLEnhancedConsoleDetector
except ImportError:
# ML detector is optional and requires Scikit-Learn
    pass

# Import and re-export of the new consolidated functions
try:
    from .detection_handler import detect_console, detect_rom_type, DetectionManager
except ImportError:
# Some modules could not yet be available during the consolidation phase
    pass

__all__ = [
    'BaseDetector',
    'detect_console_from_file',
    'detect_console_from_path',
    'detect_console_from_name',
    'detect_console_from_archive',
    'detect_console',
    'detect_rom_type',
    'DetectionManager',
    'detect_console_fast',
    'detect_console_by_extension',
    'is_archive_file',
    'detect_console_with_ml',
    'MLEnhancedConsoleDetector',
    'detect_console_from_chd',
    'is_chd_file'
]
