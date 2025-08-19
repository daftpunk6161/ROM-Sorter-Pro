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
from collections import Counter

# Importing functions from Utils
from src.utils import detect_console_fast

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

# Maximum number of files to be tested in an archive
MAX_FILES_TO_CHECK = 50

# Minimal confidence for positive console recognition
MIN_CONFIDENCE = 0.65


@lru_cache(maxsize=100)
def get_archive_type(file_path: str) -> str:
    """
    Bestimmt den Archivtyp basierend auf der Dateierweiterung.

    Args:
        file_path: Pfad zur Archivdatei

    Returns:
        String mit dem Archivtyp oder "Unknown" falls unbekannt
    """
    file_path_lower = file_path.lower()

# Check first combined extensions such as .tar.gz
    for ext in ['.tar.gz', '.tar.bz2']:
        if file_path_lower.endswith(ext):
            return ARCHIVE_EXTENSIONS.get(ext, "Unknown")

# Then check simple extensions
    extension = Path(file_path_lower).suffix
    return ARCHIVE_EXTENSIONS.get(extension, "Unknown")


def is_archive_file(file_path: str) -> bool:
    """
    Prüft, ob eine Datei ein Archiv ist.

    Args:
        file_path: Pfad zur Datei

    Returns:
        True, wenn es sich um ein Archiv handelt
    """
    return get_archive_type(file_path) != "Unknown"


def analyze_zip_archive(zip_path: str) -> Tuple[str, float]:
    """
    Analysiert ein ZIP-Archiv, um den Konsolentyp zu bestimmen.

    Args:
        zip_path: Pfad zum ZIP-Archiv

    Returns:
        Tuple mit (Konsolentyp, Konfidenz)
    """
    try:
        if not os.path.exists(zip_path) or not zipfile.is_zipfile(zip_path):
            logger.warning(f"Ungültige ZIP-Datei: {zip_path}")
            return "Archive", 0.0

        console_counts = Counter()
        total_files = 0

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()

# Filtere hidden files and directories
            file_list = [f for f in file_list if not f.startswith('__MACOSX')
                         and not f.startswith('.') and not f.endswith('/')]

# Limit the number of files to be checked
            files_to_check = file_list[:MAX_FILES_TO_CHECK]

            for file_name in files_to_check:
                extension = os.path.splitext(file_name)[1].lower()

# Skip meta files
                if file_name.startswith('.') or extension in ['.txt', '.nfo', '.xml', '.html', '.jpg', '.png', '.gif']:
                    continue

# Detectors Console based on the file name
                console, confidence = detect_console_fast(file_name)

# If we have found a console with sufficient confidence, count it
                if confidence >= MIN_CONFIDENCE and console != "Unknown" and console not in ["Archive", "Binary", "ROM_File"]:
                    console_counts[console] += 1
                    total_files += 1

# If we have found consoles, use the most common
        if total_files > 0:
            most_common_console, count = console_counts.most_common(1)[0]
            confidence = min(count / total_files * 1.2, 0.95)  # Reinforced confidence, max 95%
            return most_common_console, confidence

# Fallback: Attempts to recognize the console from the archive name
        console, confidence = detect_console_fast(os.path.basename(zip_path))
        if confidence >= 0.5:
            return console, confidence * 0.8  # Reduziere Konfidenz leicht

        return "Archive", 0.3  # Generic archive type with low confidence

    except Exception as e:
        logger.error(f"Fehler beim Analysieren des ZIP-Archivs {zip_path}: {e}")
        return "Archive", 0.0


def detect_console_from_archive(archive_path: str) -> Tuple[str, float]:
    """
    Hauptfunktion zum Erkennen der Konsole aus einem Archiv.

    Args:
        archive_path: Pfad zur Archivdatei

    Returns:
        Tuple mit (Konsolentyp, Konfidenz)
    """
    if not os.path.exists(archive_path):
        logger.warning(f"Archiv existiert nicht: {archive_path}")
        return "Unknown", 0.0

    archive_type = get_archive_type(archive_path)

# Processing based on the archive type
    if archive_type == "ZIP":
        return analyze_zip_archive(archive_path)

# For other archive types (not yet implemented)
# ToDo: Add support for rare, 7Z etc.

# Fallback: Attempts to recognize the console from the archive name
    console, confidence = detect_console_fast(os.path.basename(archive_path))
    if confidence >= 0.5:
        return console, confidence * 0.8  # Reduziere Konfidenz leicht

    return "Archive", 0.3  # Generic archive type with low confidence


# Pattern-based consoling caps for certain archive types
def detect_console_from_patterns(file_name: str) -> Optional[str]:
    """
    Erkennt die Konsole anhand von Dateinamen-Mustern.

    Args:
        file_name: Dateiname

    Returns:
        Erkannte Konsole oder None
    """
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
    """
    Verbessert die Erkennung für generische Dateitypen wie Archive und Binärdateien.

    Args:
        file_path: Pfad zur Datei
        file_type: Aktueller Dateityp (z.B. "Archive", "Binary", "ROM_File")

    Returns:
        Tuple mit (verbesserter Dateityp, Konfidenz)
    """
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
