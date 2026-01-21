"""
Archive Detection Module
-----------------------
Specialized module for analyzing archive files to determine their console type
based on the contents within the archive.

This module provides functionality to:
- Detect ROM console from archive contents
- Support multiple archive formats (ZIP, RAR, 7Z)
- Safe archive content inspection
- Pattern matching for ROM identification
"""

import os
import re
import zipfile
from pathlib import Path
from typing import Optional, Tuple
import logging
from functools import lru_cache

# Importing functions from Utils
from ..utils import detect_console_fast
from ..security.security_utils import is_safe_archive_member

# Set up logger
logger = logging.getLogger(__name__)

# Constant
ARCHIVE_EXTENSIONS = {
    '.zip': 'ZIP',
    '.rar': 'RAR',
    '.7z': '7Z',
    '.tar': 'TAR',
    '.gz': 'GZIP',
    '.tar.gz': 'TARGZ',
    '.bz2': 'BZIP2',
}



@lru_cache(maxsize=100)
def get_archive_type(file_path: str) -> str:
    """Determines the archive type based on the file extension. Args: File_Path: path to the archive file Return: String with the archive type or "unknown" if unknown"""
    file_path_lower = file_path.lower()

# Check first combined extensions such as .tar.gz
    for ext in ['.tar.gz', '.tar.bz2']:
        if file_path_lower.endswith(ext):
            return ARCHIVE_EXTENSIONS.get(ext, "Unknown")

# Then check simple extensions
    extension = Path(file_path_lower).suffix
    return ARCHIVE_EXTENSIONS.get(extension, "Unknown")


def is_archive_file(file_path: str) -> bool:
    """Check Whether a file is an archive. Args: File_Path: Path to the File Return: True When It It Comes to an Archive"""
    return get_archive_type(file_path) != "Unknown"


def analyze_zip_archive(zip_path: str) -> Tuple[str, float]:
    """Analyzes A ZIP Archive to Determine the Console Type. ARGS: ZIP_Path: Path to the ZIP Archive Return: Tuple with (Console Type, Confidence)"""
    try:
        if not os.path.exists(zip_path) or not zipfile.is_zipfile(zip_path):
            logger.warning(f"Ungültige ZIP-Datei: {zip_path}")
            return "Archive", 0.0

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            infos = [zi for zi in zip_ref.infolist() if not zi.is_dir()]

            unsafe_entries = [zi.filename for zi in infos if not is_safe_archive_member(zi)]
            if unsafe_entries:
                for name in unsafe_entries[:5]:
                    logger.warning(f"Unsafe archive member skipped: {name}")

        # Strict policy: do not guess console from archive contents here.
        return "Archive", 0.0

    except Exception as e:
        logger.error(f"Fehler beim Analysieren des ZIP-Archivs {zip_path}: {e}")
        return "Archive", 0.0


def detect_console_from_archive(archive_path: str) -> Tuple[str, float]:
    """Main function to recognize the console from an archive. Args: Archive_Path: path to the archive file Return: Tuple with (console type, confidence)"""
    if not os.path.exists(archive_path):
        logger.warning(f"Archiv existiert nicht: {archive_path}")
        return "Unknown", 0.0

    archive_type = get_archive_type(archive_path)

# Processing based on the archive type
    if archive_type == "ZIP":
        return analyze_zip_archive(archive_path)

    # For other archive types (RAR, 7Z, etc.), do not guess.
    return "Archive", 0.0


# Pattern-based consoling caps for certain archive types
def detect_console_from_patterns(file_name: str) -> Optional[str]:
    """Recognize the console using file name patterns. Args: File_Name: File name Return: Recognized console or none"""
    patterns = {
        'NES': [r'\.nes$', r'nintendo.*entertainment.*system'],
        'SNES': [r'\.smc$', r'\.sfc$', r'super.*nintendo'],
        'N64': [r'\.n64$', r'\.z64$', r'nintendo.*64'],
        'GameCube': [r'\.gcm$', r'\.iso$', r'gamecube'],
        'Wii': [r'\.wbfs$', r'\.wad$', r'\.wii$'],
        'PlayStation': [r'\.bin$', r'\.cue$', r'\.img$', r'playstation'],
        'PlayStation2': [r'\.iso$', r'playstation.*2', r'ps2'],
        'PSP': [r'\.iso$', r'\.cso$', r'playstation.*portable'],
        'GameBoy': [r'\.gb$', r'gameboy[^a]'],  # Prevents hits for "Gameboy Advance"
        'GameBoy Color': [r'\.gbc$', r'gameboy.*color'],
        'GameBoy Advance': [r'\.gba$', r'gameboy.*advance'],
        'Nintendo DS': [r'\.nds$', r'nintendo.*ds[^i]'],  # Prevents hits for "Nintendo DSI"
        'Sega Genesis': [r'\.md$', r'\.gen$', r'sega.*genesis', r'mega.*drive'],
        'Sega Saturn': [r'\.cue$', r'sega.*saturn'],
        'Sega Dreamcast': [r'\.gdi$', r'\.cdi$', r'dreamcast'],
    }

    file_name_lower = file_name.lower()

    for console, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, file_name_lower):
                return console

    return None

# Main function to improve the detection of generic files
def improve_generic_type_detection(file_path: str, file_type: str) -> Tuple[str, float]:
    """Improves detection for generic file types such as archives and binary files. Args: File_Path: path to the file File_type: Current file type (e.g. "Archive", "Binary", "Rom_file") Return: Tuble with (improved file type, confidence)"""
    if file_type == "Archive" and is_archive_file(file_path):
        return detect_console_from_archive(file_path)
    elif file_type in ["Binary", "ROM_File"]:
# Try to recognize the console from the file name
        console, confidence = detect_console_fast(os.path.basename(file_path))
        if confidence >= 0.6:
            return console, confidence

# Try it with sample comparison
        detected_console = detect_console_from_patterns(file_path)
        if detected_console:
            return detected_console, 0.7

# Checking the parent list on console information
        parent_dir = os.path.basename(os.path.dirname(file_path))
        dir_console, dir_confidence = detect_console_fast(parent_dir)
        if dir_confidence >= 0.6 and dir_console not in ["Unknown", "Archive", "Binary", "ROM_File"]:
            return dir_console, dir_confidence * 0.8

# Fallback: Keep the original type
    return file_type, 0.3
