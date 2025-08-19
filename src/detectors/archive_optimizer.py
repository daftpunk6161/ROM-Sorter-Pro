#!/usr/bin/env python3
# -*-coding: utf-8-*-

"""
ROM Sorter Pro - Erweiterte Archiv-Erkennung und Verarbeitung

Dieses Modul bietet erweiterte Funktionen zur Erkennung und Verarbeitung von
verschiedenen Archivformaten (ZIP, RAR, 7Z, etc.), mit Unterstützung für
verschachtelte Archive und interne Strukturen.

Features:
- Erkennung von verschiedenen Archivformaten
- Verarbeitung verschachtelter Archive
- Optimierte Extraktion von ROMs aus Archiven
- Komprimierungsoptimierungen für ROMs
- Analyse von Archivstrukturen
"""

import os
import re
import io
import zipfile
import tarfile
import logging
import hashlib
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union, Set, Generator, BinaryIO

# Configure logger
logger = logging.getLogger(__name__)

# Constants for supported archive formats
ARCHIVE_EXTENSIONS = {
    '.zip': 'ZIP',
    '.7z': '7Z',
    '.rar': 'RAR',
    '.tar': 'TAR',
    '.gz': 'GZIP',
    '.bz2': 'BZIP2',
    '.xz': 'XZ',
    '.tgz': 'TAR_GZIP',
    '.tbz2': 'TAR_BZIP2',
    '.txz': 'TAR_XZ',
    '.lzh': 'LZH',
    '.lha': 'LHA',
    '.arj': 'ARJ',
    '.cab': 'CAB',
    '.iso': 'ISO',
    '.chd': 'CHD'
}

# ROMS that are often contained in archives
ROM_EXTENSIONS = [
    '.nes', '.smc', '.sfc', '.n64', '.z64', '.v64',
    '.gb', '.gbc', '.gba', '.nds', '.md', '.smd',
    '.gen', '.32x', '.iso', '.cue', '.bin', '.chd',
    '.img', '.rom', '.pce'
]

# Constants for external tools
_7ZIP_PATHS = [
    r"C:\Program Files\7-Zip\7z.exe",
    r"C:\Program Files (x86)\7-Zip\7z.exe",
    "/usr/bin/7z",
    "/usr/local/bin/7z",
]


def find_7zip_path() -> Optional[str]:
    """
    Sucht nach dem Pfad zur 7-Zip-Executable.

    Returns:
        Pfad zu 7-Zip oder None, wenn nicht gefunden
    """
    for path in _7ZIP_PATHS:
        if os.path.exists(path):
            return path

# Try to find it via Path
    try:
        if os.name == 'nt':  # Windows
            result = subprocess.run(["where", "7z"], capture_output=True, text=True, check=False)
        else:  # Unix/Linux
            result = subprocess.run(["which", "7z"], capture_output=True, text=True, check=False)

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")[0]
    except Exception:
        pass

    return None


class ArchiveInfo:
    """Klasse zur Speicherung von Informationen über ein Archiv."""

    def __init__(self, file_path: str):
        """
        Initialisiert ein ArchiveInfo-Objekt.

        Args:
            file_path: Pfad zur Archivdatei
        """
        self.file_path = file_path
        self.archive_type = self._detect_archive_type()
        self.files = []
        self.nested_archives = []
        self.rom_files = []
        self.size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        self.compressed_size = 0
        self.compression_ratio = 0.0
        self.is_multi_rom = False

    def _detect_archive_type(self) -> str:
        """
        Erkennt den Typ des Archivs anhand der Dateiendung.

        Returns:
            Archivtyp als String
        """
        ext = os.path.splitext(self.file_path.lower())[1]
        return ARCHIVE_EXTENSIONS.get(ext, "UNKNOWN")

    def __str__(self) -> str:
        """String-Repräsentation des ArchiveInfo-Objekts."""
        return (f"ArchiveInfo({os.path.basename(self.file_path)}, "
                f"type={self.archive_type}, files={len(self.files)}, "
                f"roms={len(self.rom_files)}, nested={len(self.nested_archives)})")


class AdvancedArchiveDetector:
    """
    Erweiterte Klasse zur Erkennung und Verarbeitung von Archivdateien.
    Unterstützt verschiedene Archivformate und verschachtelte Archive.
    """

    def __init__(self):
        """Initialisiert den AdvancedArchiveDetector."""
        self._7zip_path = find_7zip_path()
        logger.debug(f"7-Zip-Pfad: {self._7zip_path}")

    def is_archive(self, file_path: str) -> bool:
        """
        Prüft, ob eine Datei ein unterstütztes Archiv ist.

        Args:
            file_path: Pfad zur Datei

        Returns:
            True, wenn die Datei ein unterstütztes Archiv ist, sonst False
        """
        ext = os.path.splitext(file_path.lower())[1]
        return ext in ARCHIVE_EXTENSIONS

    def get_archive_type(self, file_path: str) -> str:
        """
        Gibt den Typ eines Archivs zurück.

        Args:
            file_path: Pfad zum Archiv

        Returns:
            Archivtyp als String oder "UNKNOWN", wenn unbekannt
        """
        ext = os.path.splitext(file_path.lower())[1]
        return ARCHIVE_EXTENSIONS.get(ext, "UNKNOWN")

    def get_archive_info(self, file_path: str, scan_nested: bool = True) -> Optional[ArchiveInfo]:
        """
        Sammelt Informationen über ein Archiv.

        Args:
            file_path: Pfad zum Archiv
            scan_nested: Ob verschachtelte Archive gescannt werden sollen

        Returns:
            ArchiveInfo-Objekt oder None bei Fehler
        """
        if not self.is_archive(file_path) or not os.path.exists(file_path):
            return None

        archive_info = ArchiveInfo(file_path)

        try:
# Process zip files with Python library
            if archive_info.archive_type == "ZIP":
                self._process_zip_archive(archive_info, scan_nested)
# Use for other formats 7-Zip if available
            elif self._7zip_path:
                self._process_archive_with_7zip(archive_info, scan_nested)
            else:
                logger.warning(f"Kein 7-Zip gefunden, kann {file_path} nicht verarbeiten")
                return archive_info

# Determine Whether it is a multi-rome archive
            if len(archive_info.rom_files) > 1:
                archive_info.is_multi_rom = True

            return archive_info
        except Exception as e:
            logger.error(f"Fehler bei der Verarbeitung von {file_path}: {e}")
            return archive_info

    def _process_zip_archive(self, archive_info: ArchiveInfo, scan_nested: bool) -> None:
        """
        Verarbeitet ein ZIP-Archiv.

        Args:
            archive_info: ArchiveInfo-Objekt
            scan_nested: Ob verschachtelte Archive gescannt werden sollen
        """
        try:
            with zipfile.ZipFile(archive_info.file_path, 'r') as zip_file:
# Collect information about all files
                for file_info in zip_file.infolist():
                    if file_info.is_dir():
                        continue

                    archive_info.files.append({
                        'name': file_info.filename,
                        'size': file_info.file_size,
                        'compressed_size': file_info.compress_size,
                        'date_time': file_info.date_time
                    })

# Compression size
                    archive_info.compressed_size += file_info.compress_size

# Check Whether it is a rome file
                    ext = os.path.splitext(file_info.filename.lower())[1]
                    if ext in ROM_EXTENSIONS:
                        archive_info.rom_files.append(file_info.filename)

# Check on nested archives
                    if scan_nested and ext in ARCHIVE_EXTENSIONS:
                        archive_info.nested_archives.append(file_info.filename)

# Optional: Extract and scanne nested archives
                        if scan_nested:
                            with tempfile.TemporaryDirectory() as temp_dir:
                                nested_path = os.path.join(temp_dir, os.path.basename(file_info.filename))
                                with zip_file.open(file_info.filename) as source, open(nested_path, 'wb') as target:
                                    shutil.copyfileobj(source, target)

                                nested_info = self.get_archive_info(nested_path, scan_nested=False)
                                if nested_info:
                                    for rom in nested_info.rom_files:
                                        archive_info.rom_files.append(f"{file_info.filename}/{rom}")

# Calculate compression rate
                if archive_info.size > 0:
                    archive_info.compression_ratio = archive_info.compressed_size / archive_info.size

        except zipfile.BadZipFile:
            logger.error(f"{archive_info.file_path} ist keine gültige ZIP-Datei")
        except Exception as e:
            logger.error(f"Fehler bei der Verarbeitung von {archive_info.file_path}: {e}")

    def _process_archive_with_7zip(self, archive_info: ArchiveInfo, scan_nested: bool) -> None:
        """
        Verarbeitet ein Archiv mit 7-Zip.

        Args:
            archive_info: ArchiveInfo-Objekt
            scan_nested: Ob verschachtelte Archive gescannt werden sollen
        """
        try:
# List mode for archive content
            cmd = [self._7zip_path, "l", "-slt", archive_info.file_path]
            process = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if process.returncode != 0:
                logger.error(f"7-Zip konnte {archive_info.file_path} nicht verarbeiten")
                return

            output = process.stdout
            files = []
            current_file = None

# Parse 7-Zip edition
            for line in output.splitlines():
                line = line.strip()

                if line.startswith("Path = "):
                    if current_file:
                        files.append(current_file)

                    file_path = line[7:]
                    current_file = {
                        'name': file_path,
                        'size': 0,
                        'compressed_size': 0,
                        'date_time': None
                    }
                elif line.startswith("Size = ") and current_file:
                    try:
                        current_file['size'] = int(line[7:])
                    except ValueError:
                        pass
                elif line.startswith("Packed Size = ") and current_file:
                    try:
                        current_file['compressed_size'] = int(line[14:])
                    except ValueError:
                        pass
                elif line.startswith("Modified = ") and current_file:
                    current_file['date_time'] = line[11:]

# Add last entry
            if current_file:
                files.append(current_file)

# Processed files
            for file_info in files:
                if file_info['name'].endswith('/'):  # Verzeichnis
                    continue

                archive_info.files.append(file_info)
                archive_info.compressed_size += file_info['compressed_size']

# Check Whether it is a rome file
                ext = os.path.splitext(file_info['name'].lower())[1]
                if ext in ROM_EXTENSIONS:
                    archive_info.rom_files.append(file_info['name'])

# Check on nested archives
                if ext in ARCHIVE_EXTENSIONS:
                    archive_info.nested_archives.append(file_info['name'])

# Optional: Extract and scanne nested archives
                    if scan_nested:
                        with tempfile.TemporaryDirectory() as temp_dir:
                            nested_path = os.path.join(temp_dir, os.path.basename(file_info['name']))
                            extract_cmd = [self._7zip_path, "e", "-y", "-o" + temp_dir,
                                          archive_info.file_path, file_info['name']]

                            extract_process = subprocess.run(extract_cmd, capture_output=True, check=False)
                            if extract_process.returncode == 0 and os.path.exists(nested_path):
                                nested_info = self.get_archive_info(nested_path, scan_nested=False)
                                if nested_info:
                                    for rom in nested_info.rom_files:
                                        archive_info.rom_files.append(f"{file_info['name']}/{rom}")

# Calculate compression rate
            if archive_info.size > 0:
                archive_info.compression_ratio = archive_info.compressed_size / archive_info.size

        except Exception as e:
            logger.error(f"Fehler bei der 7-Zip-Verarbeitung von {archive_info.file_path}: {e}")

    def extract_file_from_archive(self, archive_path: str, file_path: str, output_path: str) -> bool:
        """
        Extrahiert eine einzelne Datei aus einem Archiv.

        Args:
            archive_path: Pfad zum Archiv
            file_path: Pfad der zu extrahierenden Datei im Archiv
            output_path: Zielverzeichnis für die extrahierte Datei

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            archive_type = self.get_archive_type(archive_path)

# Process zip files with Python library
            if archive_type == "ZIP":
                with zipfile.ZipFile(archive_path, 'r') as zip_file:
# Check whether the file exists in the archive
                    try:
                        info = zip_file.getinfo(file_path)
                    except KeyError:
                        logger.error(f"Datei {file_path} nicht im Archiv {archive_path} gefunden")
                        return False

# Extract the file
                    zip_file.extract(file_path, output_path)
                    return True

# Use for other formats 7-Zip if available
            elif self._7zip_path:
                cmd = [self._7zip_path, "e", "-y", "-o" + output_path, archive_path, file_path]
                process = subprocess.run(cmd, capture_output=True, check=False)
                return process.returncode == 0
            else:
                logger.warning(f"Kein 7-Zip gefunden, kann {archive_path} nicht entpacken")
                return False

        except Exception as e:
            logger.error(f"Fehler beim Extrahieren aus {archive_path}: {e}")
            return False

    def extract_all_roms_from_archive(self, archive_path: str, output_path: str) -> List[str]:
        """
        Extrahiert alle ROM-Dateien aus einem Archiv.

        Args:
            archive_path: Pfad zum Archiv
            output_path: Zielverzeichnis für die extrahierten Dateien

        Returns:
            Liste der extrahierten Dateien oder leere Liste bei Fehler
        """
        try:
            archive_info = self.get_archive_info(archive_path)
            if not archive_info or not archive_info.rom_files:
                logger.warning(f"Keine ROM-Dateien in {archive_path} gefunden")
                return []

            extracted_files = []

# Create the target directory if it does not exist
            os.makedirs(output_path, exist_ok=True)

            archive_type = self.get_archive_type(archive_path)

# Process zip files with Python library
            if archive_type == "ZIP":
                with zipfile.ZipFile(archive_path, 'r') as zip_file:
                    for rom_file in archive_info.rom_files:
# Check Whether the Rome File is Directly in the Archive Or in A Nested Archive
                        if "/" in rom_file and rom_file.split("/")[0] in archive_info.nested_archives:
# Nested Rome - first extract the inner archive
                            nested_archive = rom_file.split("/")[0]
                            inner_rom = "/".join(rom_file.split("/")[1:])

                            with tempfile.TemporaryDirectory() as temp_dir:
                                temp_archive = os.path.join(temp_dir, nested_archive)
                                with zip_file.open(nested_archive) as source, open(temp_archive, 'wb') as target:
                                    shutil.copyfileobj(source, target)

# Extract Rome from nested archive
                                if self.extract_file_from_archive(temp_archive, inner_rom, output_path):
                                    extracted_path = os.path.join(output_path, os.path.basename(inner_rom))
                                    if os.path.exists(extracted_path):
                                        extracted_files.append(extracted_path)
                        else:
# Direct Rome file
                            zip_file.extract(rom_file, output_path)
                            extracted_path = os.path.join(output_path, rom_file)
                            if os.path.exists(extracted_path):
                                extracted_files.append(extracted_path)

# Use for other formats 7-Zip if available
            elif self._7zip_path:
# Extract all Rome files
                cmd = [self._7zip_path, "e", "-y", "-o" + output_path, archive_path]
                cmd.extend([f for f in archive_info.rom_files if "/" not in f])

                if cmd[4:]:  # Wenn es direkte ROMs gibt
                    process = subprocess.run(cmd, capture_output=True, check=False)
                    if process.returncode == 0:
# Add extracted files to the list
                        for rom_file in archive_info.rom_files:
                            if "/" not in rom_file:
                                extracted_path = os.path.join(output_path, os.path.basename(rom_file))
                                if os.path.exists(extracted_path):
                                    extracted_files.append(extracted_path)

# Processed nested archives
                for rom_file in archive_info.rom_files:
                    if "/" in rom_file:
                        nested_archive = rom_file.split("/")[0]
                        inner_rom = "/".join(rom_file.split("/")[1:])

                        with tempfile.TemporaryDirectory() as temp_dir:
# Extract the inner archive
                            extract_cmd = [self._7zip_path, "e", "-y", "-o" + temp_dir, archive_path, nested_archive]
                            extract_process = subprocess.run(extract_cmd, capture_output=True, check=False)

                            if extract_process.returncode == 0:
                                temp_archive = os.path.join(temp_dir, os.path.basename(nested_archive))
                                if os.path.exists(temp_archive):
# Extract Rome from nested archive
                                    if self.extract_file_from_archive(temp_archive, inner_rom, output_path):
                                        extracted_path = os.path.join(output_path, os.path.basename(inner_rom))
                                        if os.path.exists(extracted_path):
                                            extracted_files.append(extracted_path)

            return extracted_files

        except Exception as e:
            logger.error(f"Fehler beim Extrahieren aller ROMs aus {archive_path}: {e}")
            return []

    def create_optimized_archive(self, files: List[str], output_path: str,
                               archive_type: str = "ZIP") -> bool:
        """
        Erstellt ein optimiertes Archiv mit den angegebenen Dateien.

        Args:
            files: Liste der Dateipfade, die archiviert werden sollen
            output_path: Pfad für das Ausgabearchiv
            archive_type: Typ des zu erstellenden Archivs (ZIP, 7Z)

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            if not files:
                logger.warning("Keine Dateien zum Archivieren angegeben")
                return False

# Make sure that all files exist
            for file_path in files:
                if not os.path.exists(file_path):
                    logger.error(f"Datei {file_path} existiert nicht")
                    return False

# Create the output directory, if necessary
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

# Choose the archiving method
            if archive_type == "ZIP":
                return self._create_zip_archive(files, output_path)
            elif archive_type == "7Z" and self._7zip_path:
                return self._create_7z_archive(files, output_path)
            else:
                logger.warning(f"Nicht unterstützter Archivtyp: {archive_type}")
                return False

        except Exception as e:
            logger.error(f"Fehler beim Erstellen des optimierten Archivs {output_path}: {e}")
            return False

    def _create_zip_archive(self, files: List[str], output_path: str) -> bool:
        """
        Erstellt ein optimiertes ZIP-Archiv.

        Args:
            files: Liste der zu archivierenden Dateien
            output_path: Pfad für das Ausgabearchiv

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            compression = zipfile.ZIP_DEFLATED

            with zipfile.ZipFile(output_path, 'w', compression=compression) as zip_file:
                for file_path in files:
# Use the file name without a path as an archive entry
                    zip_file.write(file_path, arcname=os.path.basename(file_path))

            return True

        except Exception as e:
            logger.error(f"Fehler beim Erstellen des ZIP-Archivs {output_path}: {e}")
            return False

    def _create_7z_archive(self, files: List[str], output_path: str) -> bool:
        """
        Erstellt ein optimiertes 7Z-Archiv mit 7-Zip.

        Args:
            files: Liste der zu archivierenden Dateien
            output_path: Pfad für das Ausgabearchiv

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
# Change to the directory of the first file so that only file names are archived
            working_dir = os.path.dirname(files[0])
            filenames = [os.path.basename(f) for f in files]

            cmd = [self._7zip_path, "a", "-mx=9", output_path]
            cmd.extend(filenames)

            process = subprocess.run(cmd, cwd=working_dir, capture_output=True, check=False)
            return process.returncode == 0

        except Exception as e:
            logger.error(f"Fehler beim Erstellen des 7Z-Archivs {output_path}: {e}")
            return False

    def get_best_compression_format(self, file_path: str) -> str:
        """
        Bestimmt das beste Komprimierungsformat für eine Datei.

        Args:
            file_path: Pfad zur Datei

        Returns:
            Empfohlenes Archivformat ("ZIP", "7Z", etc.)
        """
        ext = os.path.splitext(file_path.lower())[1]

# ZIP is often better for compressed file formats
        if ext in ['.jpg', '.jpeg', '.png', '.mp3', '.mp4', '.ogg', '.iso']:
            return "ZIP"

# 7Z is often better for Rome files
        if ext in ROM_EXTENSIONS:
            return "7Z" if self._7zip_path else "ZIP"

# Standard value
        return "ZIP"


def get_advanced_archive_detector() -> AdvancedArchiveDetector:
    """
    Gibt eine Instanz des AdvancedArchiveDetector zurück.

    Returns:
        Eine Instanz des AdvancedArchiveDetector
    """
    return AdvancedArchiveDetector()


def is_archive_file(file_path: str) -> bool:
    """
    Prüft, ob eine Datei ein unterstütztes Archiv ist.

    Args:
        file_path: Pfad zur Datei

    Returns:
        True, wenn die Datei ein unterstütztes Archiv ist, sonst False
    """
    detector = get_advanced_archive_detector()
    return detector.is_archive(file_path)


def extract_rom_from_archive(archive_path: str, output_dir: str) -> List[str]:
    """
    Extrahiert ROM-Dateien aus einem Archiv.

    Args:
        archive_path: Pfad zum Archiv
        output_dir: Zielverzeichnis für die extrahierten Dateien

    Returns:
        Liste der extrahierten Dateipfade
    """
    detector = get_advanced_archive_detector()
    return detector.extract_all_roms_from_archive(archive_path, output_dir)


def create_rom_archive(rom_files: List[str], output_path: str) -> bool:
    """
    Erstellt ein optimiertes Archiv mit ROM-Dateien.

    Args:
        rom_files: Liste der ROM-Dateipfade
        output_path: Pfad für das Ausgabearchiv

    Returns:
        True bei Erfolg, False bei Fehler
    """
    detector = get_advanced_archive_detector()

# Determine the best format based on the first file
    if rom_files:
        archive_type = detector.get_best_compression_format(rom_files[0])
    else:
        archive_type = "ZIP"

    return detector.create_optimized_archive(rom_files, output_path, archive_type)
