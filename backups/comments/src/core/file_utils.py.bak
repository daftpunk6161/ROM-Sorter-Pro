#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Core Module

Dieses Modul enthält die grundlegenden Datei-Operationen und Utilities
für die ROM-Sortierungs-Anwendung.
"""

import os
import logging
import shutil
import hashlib
import mmap
from typing import Union, Optional, List, Tuple
from pathlib import Path
from functools import lru_cache
import io

logger = logging.getLogger(__name__)

def _calculate_small_file_hash(file_path: Path, algorithm: str) -> str:
    """
    Effizientere Hashberechnung für kleine Dateien mit Memory-Mapping.
    
    Args:
        file_path: Path-Objekt der Datei
        algorithm: Hashalgorithmus ('md5', 'sha1', 'sha256')
        
    Returns:
        Hashwert als Hex-String
    """
    hash_obj = None
    if algorithm == 'md5':
        hash_obj = hashlib.md5()
    elif algorithm == 'sha1':
        hash_obj = hashlib.sha1()
    elif algorithm == 'sha256':
        hash_obj = hashlib.sha256()
    else:
        raise ValueError(f"Nicht unterstützter Hash-Algorithmus: {algorithm}")
        
    with open(file_path, 'rb') as f:
# Memory map for small files (very efficient)
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            hash_obj.update(mm)
            
    return hash_obj.hexdigest()

def create_directory_if_not_exists(path: Union[str, Path]) -> bool:
    """
    Erstellt ein Verzeichnis, falls es noch nicht existiert.

    Args:
        path: Pfad des zu erstellenden Verzeichnisses

    Returns:
        True bei Erfolg, False bei Fehler
    """
    try:
        path_obj = Path(path)
        if not path_obj.exists():
            path_obj.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Verzeichnis erstellt: {path}")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Verzeichnisses {path}: {e}")
        return False


def enhanced_copy_file(source: Union[str, Path], destination: Union[str, Path]) -> bool:
    """
    Kopiert eine Datei mit erweiterten Fehlerprüfungen und Logging.

    Args:
        source: Quellpfad der zu kopierenden Datei
        destination: Zielpfad für die Datei

    Returns:
        True bei Erfolg, False bei Fehler
    """
    source_path = Path(source)
    dest_path = Path(destination)

    try:
# Make sure the source file exists
        if not source_path.exists():
            logger.error(f"Quelldatei existiert nicht: {source}")
            return False

# Make sure the target directory exists
        dest_dir = dest_path.parent
        if not dest_dir.exists():
            dest_dir.mkdir(parents=True, exist_ok=True)

# Copy the file
        shutil.copy2(source_path, dest_path)
        logger.debug(f"Datei kopiert: {source} -> {destination}")

# Verify the copy
        if dest_path.exists() and dest_path.stat().st_size == source_path.stat().st_size:
            return True
        else:
            logger.error(f"Kopie fehlgeschlagen oder Größe stimmt nicht überein: {source} -> {destination}")
            return False

    except Exception as e:
        logger.error(f"Fehler beim Kopieren von {source} nach {destination}: {e}")
        return False


@lru_cache(maxsize=256)
def calculate_file_hash(file_path: Union[str, Path], algorithm='md5', block_size=65536) -> Optional[str]:
    """
    Berechnet den Hashwert einer Datei mit dem angegebenen Algorithmus.
    Optimiert mit größerem Cache und Blocksize für bessere Performance.

    Args:
        file_path: Pfad zur Datei
        algorithm: Hashalgorithmus ('md5', 'sha1', 'sha256')
        block_size: Größe der zu lesenden Blöcke in Bytes (Standard: 64KB)

    Returns:
        Hashwert als Hex-String oder None bei Fehler
    """
    try:
        file_path_obj = Path(file_path)
        file_size = file_path_obj.stat().st_size
        
# Processing optimized for small files
        if file_size < 1024 * 1024 and os.name != 'nt':  # 1MB, not for Windows (because of MMAP restrictions)
            return _calculate_small_file_hash(file_path_obj, algorithm)
            
# Choose Hashalgorithm
        if algorithm == 'md5':
            hash_obj = hashlib.md5()
        elif algorithm == 'sha1':
            hash_obj = hashlib.sha1()
        elif algorithm == 'sha256':
            hash_obj = hashlib.sha256()
        else:
            logger.error(f"Unbekannter Hashalgorithmus: {algorithm}")
            return None

# For very small files
        if file_path_obj.stat().st_size < block_size * 2:
            with open(file_path_obj, 'rb') as f:
                hash_obj.update(f.read())
        else:
# For larger files, use memory mapping for better performance
            with open(file_path_obj, 'rb') as f:
                try:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        for i in range(0, len(mm), block_size):
                            hash_obj.update(mm[i:i+block_size])
                except (ValueError, OSError):
# Fallback for files that do not support memory mapping
                    while True:
                        buffer = f.read(block_size)
                        if not buffer:
                            break
                        hash_obj.update(buffer)

        return hash_obj.hexdigest()

    except Exception as e:
        logger.error(f"Fehler bei der Berechnung des {algorithm}-Hash für {file_path}: {e}")
        return None


def get_file_extension(file_path: Union[str, Path]) -> str:
    """
    Gibt die Dateierweiterung mit führendem Punkt zurück.
    Behandelt auch Sonderfälle wie doppelte Extensions.

    Args:
        file_path: Pfad zur Datei

    Returns:
        Dateierweiterung mit führendem Punkt oder leerer String
    """
    path_obj = Path(file_path)
    file_name = path_obj.name

# Special case for double points at the end (..)
    if file_name.endswith('.'):
        parts = file_name.split('.')
        if len(parts) > 2:  # mindestens name.ext.
            return f".{parts[-2]}"
        return ""

# Normal expansion
    suffix = path_obj.suffix
    return suffix.lower() if suffix else ""


def normalize_filename(filename: str, max_length: int = 255) -> str:
    """
    Normalisiert einen Dateinamen für sichere Verwendung auf verschiedenen Dateisystemen.

    Entfernt ungültige Zeichen, begrenzt die Länge und stellt sicher,
    dass der Dateiname den Standards entspricht.

    Args:
        filename: Originaler Dateiname
        max_length: Maximale erlaubte Länge

    Returns:
        Normalisierter Dateiname
    """
    import re

    if not filename:
        return "unnamed_file"

# Remove dangerous signs
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f]', '_', filename)

# Remove leading/subsequent points and spaces
    sanitized = sanitized.strip(' .')

# Make sure that the file name is not empty after cleaning up
    if not sanitized:
        sanitized = "unnamed_file"

# Run, if too long, and keep expansion, if possible
    if len(sanitized) > max_length:
        if '.' in sanitized:
            name, ext = sanitized.rsplit('.', 1)
            max_name_length = max_length - len(ext) - 1
            if max_name_length > 0:
                sanitized = name[:max_name_length] + '.' + ext
            else:
                sanitized = sanitized[:max_length]
        else:
            sanitized = sanitized[:max_length]

    return sanitized


def safe_move_file(source: Union[str, Path], destination: Union[str, Path],
                  ensure_dir: bool = True) -> bool:
    """
    Verschiebt eine Datei sicher mit erweiterter Fehlerbehandlung.

    Diese Funktion versucht zuerst eine direkte Verschiebung (schneller und atomisch).
    Falls das fehlschlägt, wird ein Kopieren und anschließendes Löschen durchgeführt.

    Args:
        source: Quellpfad der Datei
        destination: Zielpfad für die Datei
        ensure_dir: Zielverzeichnis automatisch erstellen, falls es nicht existiert

    Returns:
        True bei Erfolg, False bei Fehler
    """
    source_path = Path(source)
    dest_path = Path(destination)

    try:
# Check whether the source file exists
        if not source_path.exists() or not source_path.is_file():
            logger.error(f"Quelldatei existiert nicht oder ist kein reguläres File: {source}")
            return False

# Make sure the target directory exists
        if ensure_dir:
            dest_dir = dest_path.parent
            if not dest_dir.exists():
                dest_dir.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Verzeichnis erstellt: {dest_dir}")

# Try direct displacement (fast and atomic)
        try:
            shutil.move(str(source_path), str(dest_path))
            logger.debug(f"Datei direkt verschoben: {source} -> {destination}")
            return True
        except (OSError, shutil.Error) as e:
# If moving fails (e.g. different partitions),
# Copy and delete tests
            logger.debug(f"Direktes Verschieben fehlgeschlagen, versuche Kopieren: {e}")

# Try to copy
            if enhanced_copy_file(source_path, dest_path):
# Check whether copying was successful
                if dest_path.exists() and dest_path.stat().st_size == source_path.stat().st_size:
                    try:
# Delete original after a successful copy
                        source_path.unlink()
                        logger.debug(f"Datei kopiert und Original gelöscht: {source} -> {destination}")
                        return True
                    except OSError as del_err:
                        logger.warning(f"Konnte Original nach Kopie nicht löschen: {source}, {del_err}")
# Nevertheless successful because copy worked
                        return True
                else:
                    logger.error(f"Kopieren fehlgeschlagen oder Größe stimmt nicht überein: {source} -> {destination}")
                    return False
            else:
                logger.error(f"Kopieren fehlgeschlagen: {source} -> {destination}")
                return False

    except Exception as e:
        logger.error(f"Fehler beim sicheren Verschieben von {source} nach {destination}: {e}")
        return False
