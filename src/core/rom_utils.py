#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - ROM Dateisystem-Funktionen

Dieses Modul enthält Funktionen zur Verarbeitung von ROM-spezifischen Dateisystem-Operationen,
einschließlich ROM-spezifischer Dateiendungen und Pfadoperationen.
"""

import os
import logging
import hashlib
from pathlib import Path
from typing import List, Set, Dict, Union, Optional, Any, Tuple

logger = logging.getLogger(__name__)

def get_all_rom_extensions(include_dot: bool = False) -> List[str]:
    """
    Gibt alle unterstützten ROM-Dateierweiterungen zurück.
    Diese Liste wird für Scanner und Filter verwendet.

    Args:
        include_dot: Ob der Punkt am Anfang der Erweiterung enthalten sein soll

    Returns:
        Liste aller unterstützten Dateierweiterungen
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
    """
    Durchsucht das angegebene Verzeichnis nach ROM-Dateien und gibt eine sortierte Liste zurück.

    Args:
        directory_path: Zu durchsuchendes Verzeichnis
        filter_extensions: Optionaler Filter für bestimmte Dateierweiterungen

    Returns:
        Sortierte Liste von ROM-Dateipfaden
    """
# Normalize path
    path_obj = Path(directory_path)

    if not path_obj.exists() or not path_obj.is_dir():
        logger.error(f"Ungültiges Verzeichnis: {directory_path}")
        return []

# Use all ROM extensions if no filter is specified
    if filter_extensions is None:
        filter_extensions = get_all_rom_extensions()
    else:
# Make sure that all extensions are without a point
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
    """
    Gruppiert ROMs nach ihrer Konsole.

    Args:
        rom_paths: Liste von ROM-Dateipfaden

    Returns:
        Dictionary mit Konsolen als Schlüssel und ROM-Listen als Werte
    """
# Importing identification functions
    from src.detectors import detect_console_fast

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
    """
    Überprüft, ob eine Datei eine gültige ROM-Datei ist.

    Args:
        file_path: Zu prüfender Dateipfad

    Returns:
        True, wenn es sich um eine gültige ROM-Datei handelt
    """
# Normalize path
    path_obj = Path(file_path)

    if not path_obj.exists() or not path_obj.is_file():
        return False

# Check file extension
    extension = path_obj.suffix.lstrip('.').lower()
    valid_extensions = get_all_rom_extensions()

    return extension in valid_extensions


def calculate_rom_signature(file_path: Union[str, Path], chunk_size: int = 16 * 1024) -> str:
    """
    Berechnet eine eindeutige Signatur für eine ROM-Datei.
    Diese Funktion verwendet verschiedene Teile der Datei für eine schnelle, aber zuverlässige Erkennung.

    Args:
        file_path: Pfad zur ROM-Datei
        chunk_size: Größe der zu lesenden Chunks für die Signaturberechnung

    Returns:
        Hexadezimale Signatur der ROM-Datei
    """
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

# Jump to the middle of the file and read a chunk
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
