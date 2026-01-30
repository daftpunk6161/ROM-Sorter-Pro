"""Rome Sorter Pro Utils module This package contains utility functions and classes for the ROM sorter-pro application."""

from functools import lru_cache
from pathlib import Path
import os
import re
import logging
from typing import Tuple, Optional, List, Dict, Any, Union

# Module exports for easier use
try:
    from .fuzzy_matching import (
        fuzz_ratio, fuzz_partial_ratio, fuzz_token_sort_ratio,
        fuzz_token_set_ratio, ProcessMatch
    )
except ImportError:
    pass  # Module may not yet

try:
    from .performance import (
        measure_time, PerformanceMetric, PerformanceMonitor,
    )
except ImportError:
    pass  # Module may not yet

# Wrapper for functions that are still imported from utils.py
# This enables a Gentle Migration
logger = logging.getLogger(__name__)

# Perform the charging message for debugging purposes
logger.info("Utils-Modul mit Wrapper-Funktionen geladen")

# Fallback console database for compatibility
ENHANCED_CONSOLE_DATABASE = {
    "nintendo_nes": {
        "extensions": [".nes", ".unf", ".unif"],
        "folder": "Nintendo NES",
        "priority": 100,
        "enabled": True
    },
    "nintendo_snes": {
        "extensions": [".sfc", ".smc", ".fig"],
        "folder": "Super Nintendo",
        "priority": 100,
        "enabled": True
    },
    "nintendo_n64": {
        "extensions": [".n64", ".v64", ".z64"],
        "folder": "Nintendo 64",
        "priority": 100,
        "enabled": True
    },
    "nintendo_gba": {
        "extensions": [".gba", ".agb"],
        "folder": "Game Boy Advance",
        "priority": 100,
        "enabled": True
    },
    "nintendo_gbc": {
        "extensions": [".gbc", ".cgb"],
        "folder": "Game Boy Color",
        "priority": 100,
        "enabled": True
    },
    "sega_genesis": {
        "extensions": [".md", ".gen", ".smd", ".bin"],
        "folder": "Sega Genesis",
        "priority": 100,
        "enabled": True
    }
}

@lru_cache(maxsize=1000)
def detect_console_by_extension_cached(filename: str) -> str:
    """Recognize the console based on the file extension with caching. This function is a wrapper that is the functionality of utils.detect_console_by_extension_cached Replicated and migration is relieved. Args: Filename: the file name or path Return: Recognized console or "unknown\""""
    path_obj = Path(filename)
    extension = path_obj.suffix.lower()

    from ..database.console_db import get_console_for_extension
    console = get_console_for_extension(extension)

    return console if console else "Unknown"

def get_all_rom_extensions(include_dot: bool = False) -> List[str]:
    """Wrapper to Core.rom_Utils.get_all_Rom_Extensions for downward compatibility. Args: Include_dot: Whether the point should be included at the beginning of the expansion Return: List of all supported file extensions"""
    from ..core.rom_utils import get_all_rom_extensions as _get_all_rom_extensions
    return _get_all_rom_extensions(include_dot)

@lru_cache(maxsize=1000)
def detect_console_fast(filename: str, file_path: Optional[str] = None) -> Tuple[str, float]:
    """Fast console detection based on the file name and file extension. This function is a wrapper for the function in console_detector.py and enables one Consistent import structure over the entire project. Args: Filename: Rome date name File_Path: Optional full file path Return: Tupel with (console name, confidence value)"""
    from ..detectors.console_detector import detect_console_fast as _detect_console_fast
    return _detect_console_fast(filename, file_path)

def is_chd_file(file_path: str) -> bool:
    """Checks if a file is in CHD format. This function is a wrapper for the function in chd_detector.py and enables a Consistent Import Structure Throughout the Project. Args: File_Path: Path to the File to Check Return: True if it's a chd file, OtherWise False"""
    from ..detectors.chd_detector import is_chd_file as _is_chd_file
    return _is_chd_file(file_path)

def detect_console_from_chd(file_path: str) -> Tuple[str, float]:
    """Recognize the console from a CHD file. This function is a wrapper for the function in chd_detector.py and enables one Consistent import structure over the entire project. Args: File_Path: path to the CHD file Return: Tuble from (console_name, confidence)"""
    from ..detectors.chd_detector import detect_console_from_chd as _detect_console_from_chd
    return _detect_console_from_chd(file_path)

def is_archive_file(file_path: str) -> bool:
    """Checks if a file is an archive. This function is a wrapper for the function in archive_detector.py and enables a Consistent Import Structure Throughout the Project. Args: File_Path: Path to the File to Check Return: True if it is an archive, otherwise false"""
    from ..detectors.archive_detector import is_archive_file as _is_archive_file
    return _is_archive_file(file_path)

def detect_console_from_archive(file_path: str) -> Tuple[str, float]:
    """Recognizes the console from an archive. This function is a wrapper for the function in archive_detector.py and enables one Consistent import structure over the entire project. Args: File_Path: path to the archive Return: Tuble from (console_name, confidence)"""
    from ..detectors.archive_detector import detect_console_from_archive as _detect_console_from_archive
    return _detect_console_from_archive(file_path)


