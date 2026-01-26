#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""Rome Sorter Pro - Detector Package This package contains all detector modules for the detection of ROM types, including console, archive and CHD detectors."""

import os
import logging

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

detect_console_with_ml = None
MLEnhancedConsoleDetector = None
if os.environ.get("ROM_SORTER_ENABLE_ML", "").strip() == "1":
    try:
        from .ml_detector import detect_console_with_ml, MLEnhancedConsoleDetector
    except ImportError:
        pass

detect_console = None
detect_rom_type = None
DetectionManager = None

# Import and re-export of the new consolidated functions
try:
    from .detection_handler import detect_console, detect_console_with_metadata, DetectionManager
    detect_rom_type = detect_console_with_metadata
except Exception:
    # Some modules could not yet be available during the consolidation phase
    pass

logging.getLogger(__name__).warning("Detector facade is consolidating. Prefer detection_handler.detect_console.")

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
