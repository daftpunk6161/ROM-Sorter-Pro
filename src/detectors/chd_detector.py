"""Improved CHD recognition module for Rome Sorter ------------------------------------------ This module adds specialized detection for CHD files several types of console can be used, including: - Mame Arcade - Playstation (1, 2) - Dreamcast - Sega CD - and other disc-based systems The detection is based on: 1. File name pattern 2. Header analysis 3. Metadata from the CHD file 4. External databases (if available) 5. Context -based information (folder structure)"""

import os
import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

import os
import re
import sys
import logging
import hashlib
import sqlite3
from pathlib import Path
from typing import Tuple, Dict, List, Optional, Set, Any

logger = logging.getLogger(__name__)

# CHD header signature for type detection
CHD_SIGNATURE = b'MComprHD'
CHD_V5_SIGNATURE = b'MComprHD\x05'

# Well-known CHD format version and corresponding consoles
CHD_CONSOLE_MAPPING = {
# MAME CHD formats often have specific features
    'MAME': [
        r'chd[0-9]+', r'harddisk', r'cdrom\d*', r'chd[\\/]',
        r'arcade', r'mame', r'final\s*burn', r'neogeo'
    ],

# Sony Playstation
    'Sony - PlayStation': [
        r'ps[x1]', r'playstation(?!\s*[234])', r'psx', r'psone'
    ],

    # Sony PlayStation 2
    'Sony - PlayStation 2': [
        r'ps2', r'playstation\s*2', r'ps\s*2'
    ],

    # Sega Dreamcast
    'Sega - Dreamcast': [
        r'dreamcast', r'dc\s*', r'dc[\\/]', r'sega\s*dreamcast'
    ],

    # Sega CD/Mega-CD
    'Sega - CD': [
        r'sega\s*cd', r'mega\s*cd', r'scd', r'mega\-cd'
    ],

# Nintendo Gamecube
    'Nintendo - GameCube': [
        r'gamecube', r'gc', r'nintendo\s*gc'
    ],

    # Nintendo Wii
    'Nintendo - Wii': [
        r'wii(?!\s*u)', r'nintendo\s*wii(?!\s*u)'
    ],
}

# Typical game ID patterns for different consoles
CONSOLE_ID_PATTERNS = {
    'Sony - PlayStation': [
        r'S[A-Z]{2,3}\-\d{4,5}',  # SCUS-12345, SCES-12345
        r'SL[A-Z]{2}\d{5}'        # SLUS12345, SLES12345
    ],
    'Sony - PlayStation 2': [
        r'S[A-Z]{3}_\d{3}\.\d{2}',  # SCES_123.45
        r'S[A-Z]{3}\-\d{5}'         # SLUS-12345
    ],
    'Sega - Dreamcast': [
        r'T\d{5}[A-Z]',          # T12345N
        r'MK\-\d{7}[A-Z]'        # MK-1234567E
    ],
    'Nintendo - GameCube': [
        r'G[A-Z]{2}[A-Z0-9]',    # GALE01
        r'DOL\-[A-Z0-9]{4}'      # DOL-GALE
    ],
    'Nintendo - Wii': [
        r'RVL\-[A-Z]\w{2}[A-Z]'  # RVL-RMCE
    ],
}

# List of typical file size according to the console (approximate area in MB)
CONSOLE_SIZE_RANGES = {
    'MAME - Arcade': (5, 5000),           # Sehr variabel
    'Sony - PlayStation': (300, 750),      # Typisch 650MB
    'Sony - PlayStation 2': (1000, 4700),  # Typisch 4.7GB (DVD)
    'Sega - Dreamcast': (500, 1200),       # Typisch 1GB GD-ROM
    'Sega - CD': (200, 750),               # Typisch 650MB
    'Nintendo - GameCube': (500, 1500),    # Typisch 1.35GB mini-DVD
    'Nintendo - Wii': (1000, 4700),        # Typisch 4.7GB DVD
}

def get_chd_console(chd_path: str) -> Tuple[str, float]:
    """Recognize the Console for a Chd File Using Several Methods. ARGS: CHD_Path: Path to the Chd File Return: Tube with (Console_Name, Confidence)"""
# Standard values
    console = "MAME - Arcade"  # Standard-Fallback
    confidence = 0.5

# Does the file even exist?
    if not os.path.exists(chd_path):
        logger.warning(f"CHD-Datei existiert nicht: {chd_path}")
        return console, confidence

# 1. File name pattern check
    filename = os.path.basename(chd_path).lower()
    parent_dir = os.path.basename(os.path.dirname(chd_path)).lower()

# Check for console-specific patterns in the file name and folder names
    console_scores = {}

# Analyze file names and directory
    for console_name, patterns in CHD_CONSOLE_MAPPING.items():
        score = 0
        for pattern in patterns:
# Check in the file name
            if re.search(pattern, filename, re.IGNORECASE):
                score += 0.3

# Check in the higher -level directory (higher weight)
            if re.search(pattern, parent_dir, re.IGNORECASE):
                score += 0.4

        console_scores[console_name] = score

# 2. File size-based analysis
    try:
        file_size_mb = os.path.getsize(chd_path) / (1024 * 1024)

        for console_name, (min_size, max_size) in CONSOLE_SIZE_RANGES.items():
            if min_size <= file_size_mb <= max_size:
                console_scores[console_name] = console_scores.get(console_name, 0) + 0.1

# Typical sizes for certain consoles get an additional bonus
                if console_name == 'Sony - PlayStation' and 600 <= file_size_mb <= 700:
                    console_scores[console_name] += 0.1
                elif console_name == 'Sony - PlayStation 2' and 4300 <= file_size_mb <= 4700:
                    console_scores[console_name] += 0.1
    except Exception as e:
        logger.warning(f"Fehler bei der Größenberechnung von {chd_path}: {e}")

# 3. Try to extract metadata from the CHD file (simplified)
    try:
# Open the first 100 bytes to read header
        with open(chd_path, 'rb') as f:
            header = f.read(100)

# Check on MAME CHD signature
            if CHD_SIGNATURE in header:
                console_scores['MAME - Arcade'] = console_scores.get('MAME - Arcade', 0) + 0.2

# CHD V5 format is often used for newer Mame versions
                if CHD_V5_SIGNATURE in header:
                    console_scores['MAME - Arcade'] += 0.1

# Search for console -specific IDs throughout the header
            header_str = header.decode('utf-8', errors='ignore')
            for console_name, patterns in CONSOLE_ID_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, header_str):
                        console_scores[console_name] = console_scores.get(console_name, 0) + 0.3
    except Exception as e:
        logger.warning(f"Fehler beim Lesen des CHD-Headers von {chd_path}: {e}")

# 4. Database check, if available
    try:
# Calculate MD5 only for the first 4MB (faster)
        md5_hash = calculate_partial_md5(chd_path, 4*1024*1024)
        if md5_hash:
            db_console = check_chd_database(md5_hash)
            if db_console:
                console_scores[db_console] = console_scores.get(db_console, 0) + 0.5
    except Exception as e:
        logger.debug(f"Fehler bei der Datenbankabfrage für {chd_path}: {e}")

# Find the console with the highest score
    if console_scores:
        best_console = max(console_scores.items(), key=lambda x: x[1])

        if best_console[1] > 0.3:  # Minimaler Schwellenwert
            console = best_console[0]
            confidence = min(best_console[1], 0.95)  # Begrenzen auf 0.95

    logger.debug(f"CHD-Datei {os.path.basename(chd_path)} erkannt als {console} mit Konfidenz {confidence:.2f}")
    logger.debug(f"Score-Details: {console_scores}")

    return console, confidence

def calculate_partial_md5(file_path: str, read_size: int = 4*1024*1024) -> Optional[str]:
    """Calculate to Md5-Hash only the first n bytes of a file. This is Faster for Large Files and for Most Recognition Purposes. ARGS: File_Path: Path to the File Read_Size: Number of bytes to be read Return: Md5-Hash as a Hex String or None in the event of errors"""
    try:
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            data = f.read(read_size)
            md5.update(data)
        return md5.hexdigest()
    except Exception as e:
        logger.warning(f"Fehler bei MD5-Berechnung für {file_path}: {e}")
        return None

def check_chd_database(md5_hash: str) -> Optional[str]:
    """Checks the Rome Database for a Game with the Specified Hash. Args: md5_hash: md5-haash of the chd file return: console name or none if not found"""
    from ..database.connection_pool import ROM_DATABASE_PATH, database_connection

# If database does not exist, do not try
    if not Path(ROM_DATABASE_PATH).exists():
        return None

    try:
# Use the context manager for secure database connections
        with database_connection(ROM_DATABASE_PATH) as conn:
            cursor = conn.cursor()

# Check after the hash in the database
            cursor.execute("SELECT console FROM roms WHERE md5=? OR crc=? OR sha1=? LIMIT 1",
                         (md5_hash, md5_hash[:8], md5_hash))
            result = cursor.fetchone()

        if result:
            return result[0]
    except Exception as e:
        logger.warning(f"Datenbankfehler beim Suchen nach MD5 {md5_hash}: {e}")

    return None

def detect_chd_console(file_path: str) -> Tuple[str, float]:
    """Public API function for recognizing CHD consoles. Args: File_Path: path to the CHD file Return: Tuble from (console_name, confidence)"""
# Check Whether it is actual a chd file
    if not file_path.lower().endswith('.chd'):
        return "Unknown", 0.0

    return get_chd_console(file_path)

def is_chd_file(file_path: str) -> bool:
    """Check Whether there is a file in CHD format. ARGS: File_Path: Path to the File to Be Tested Return: True IF IT is A Chd File, Other Whisse"""
    if not file_path.lower().endswith('.chd'):
        return False

    try:
# Check on CHD header signature
        with open(file_path, 'rb') as f:
            header = f.read(8)
            return header == CHD_SIGNATURE or header == CHD_V5_SIGNATURE[:8]
    except Exception:
        return False

def detect_console_from_chd(file_path: str) -> Tuple[str, float]:
    """Recognize the Console from A Chd File. This function is an alias for detect_chd_console for api Consistency. Args: File_Path: Path to the Chd File Return: Tube from (Console_Name, Confidence)"""
    return detect_chd_console(file_path)
