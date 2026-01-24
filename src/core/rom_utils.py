#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - ROM Filesystem Functions

This module contains functions for processing ROM-specific filesystem operations,
including ROM-specific file extensions and path operations.
"""

import os
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Union, Optional

logger = logging.getLogger(__name__)

def get_all_rom_extensions(include_dot: bool = False) -> List[str]:
    """
    Returns all supported ROM file extensions.
    This list is used for scanners and filters.

    Args:
        include_dot: Whether to include the dot at the beginning of the extension

    Returns:
        List of all supported file extensions
    """
    extensions = [
        # Nintendo
        'nes', 'smc', 'sfc', 'fig', 'swc', 'mgd', 'fds', 'gba', 'gbc', 'gb',
        'n64', 'z64', 'v64', 'ndd', '3ds', 'cia', 'nds', 'nsp', 'xci',

        # Sega
        'smd', 'gen', 'md', '32x', 'bin', 'iso', 'cue', 'gdi', 'chd', 'cdi',

        # Sony
        'cue', 'bin', 'img', 'mdf', 'pbp', 'toc', 'znx', 'cbn',

        # Atari
        'a26', 'a52', 'a78', 'j64', 'jag', 'lnx',

# Snk
        'ngp', 'ngc', 'npc', 'neo',

# Nec
        'pce', 'sgx', 'cue', 'ccd',

        # Commodore
        'd64', 't64', 'g64', 'x64', 'tap', 'prg', 'p00', 'crt',

        # Arcade
        'zip', '7z', 'rar',

        # Misc
        'adf', 'adz', 'dms', 'ipf', 'uae', 'woz', 'po', 'rom', 'mx1', 'mx2',
        'col', 'sc', 'cas', 'sgm', 'st', 'msa', 'dsk', 'dmk', 'rzx', 'tzx',
        'udi', 'mgt', 'img', 'ima', 'vhd', 'vdi', 'xdf', 'fs', 'm3u', 'cso',

# Cartridge-images
        'cart', 'ws', 'wsc',

        # Handheld
        'lnx', 'vboy', 'min',

# PC engine
        'pce', 'tg16'
    ]

    if include_dot:
        return [f'.{ext}' for ext in extensions]
    return extensions


def get_sorted_rom_list(directory_path: Union[str, Path], filter_extensions: Optional[List[str]] = None) -> List[str]:
    """Searches the Specified Directory for Rome Files and Returns a Sorted List. ARGS: Directory_Path: Filter_extensions: Optional Filter for Certain File Extensions Return: Sorted List of Rome File Paths"""
# Normalize path
    path_obj = Path(directory_path)

    if not path_obj.exists() or not path_obj.is_dir():
        logger.error(f"Ungültiges Verzeichnis: {directory_path}")
        return []

# Use all ROM extensions if no filter is specified
    if filter_extensions is None:
        filter_extensions = get_all_rom_extensions()
    else:
# Make Sure that all extensions are without a point
        filter_extensions = [ext.lstrip('.') for ext in filter_extensions]

# Find all files with suitable extensions
    matching_files = []
    for file in path_obj.glob('**/*'):
        if file.is_file():
            extension = file.suffix.lstrip('.').lower()
            if extension in filter_extensions:
                matching_files.append(str(file))

# Sort the list
    matching_files.sort()

    return matching_files


def group_roms_by_console(rom_paths: List[str]) -> Dict[str, List[str]]:
    """Group Rome after her console. Args: ROM_PATHS: List of ROM file paths Return: Dictionary with consoles as keys and Rome lists as values"""
# Importing identification functions
    from ..detectors import detect_console_fast

    grouped_roms = {}

    for rom_path in rom_paths:
        try:
# Recognize console
            console, _ = detect_console_fast(os.path.basename(rom_path), rom_path)

# Initialist list for console, if not yet available
            if console not in grouped_roms:
                grouped_roms[console] = []

# Add Rome to the corresponding console
            grouped_roms[console].append(rom_path)
        except Exception as e:
            logger.warning(f"Fehler beim Gruppieren von ROM {rom_path}: {e}")
# Add Rome to the "Unknown" group
            if "Unknown" not in grouped_roms:
                grouped_roms["Unknown"] = []
            grouped_roms["Unknown"].append(rom_path)

    return grouped_roms


def is_valid_rom_file(file_path: Union[str, Path]) -> bool:
    """Check Whether a file is a valid rome file. ARGS: File_Path: File Path to Be Examined Return: True When It Comes to A Valid Rome File"""
# Normalize path
    path_obj = Path(file_path)

    if not path_obj.exists() or not path_obj.is_file():
        return False

# Check file extension
    extension = path_obj.suffix.lstrip('.').lower()
    valid_extensions = get_all_rom_extensions()

    return extension in valid_extensions


def calculate_rom_signature(file_path: Union[str, Path], chunk_size: int = 16 * 1024) -> str:
    """Calculate A Clear Signature for a Rome File. This function uses various parts of the file for quick but reliable detection. Args: File_Path: Path to the Rome File Chunk_Size: Size of the Chunks to Be Read for the Signature Calculation Return: Hexadecimal Signature of the Rome File"""
    path_obj = Path(file_path)

    if not path_obj.exists() or not path_obj.is_file():
        raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")

# Initialisalize Hasher
    hasher = hashlib.md5()

    try:
        file_size = path_obj.stat().st_size

        with open(path_obj, 'rb') as f:
# Read the first chunk (header)
            if file_size > 0:
                header = f.read(min(chunk_size, file_size))
                hasher.update(header)

# Jump to the Middle of the File and Read a Chunk
            if file_size > chunk_size * 2:
                mid_pos = file_size // 2 - chunk_size // 2
                f.seek(mid_pos)
                mid_chunk = f.read(chunk_size)
                hasher.update(mid_chunk)

# Read the last chunk (footer)
            if file_size > chunk_size:
                f.seek(max(0, file_size - chunk_size))
                footer = f.read(chunk_size)
                hasher.update(footer)

    except Exception as e:
        logger.error(f"Fehler beim Berechnen der ROM-Signatur für {file_path}: {e}")
        return "error_signature"

# Add file size as an additional factor
    hasher.update(str(file_size).encode())

    return hasher.hexdigest()
