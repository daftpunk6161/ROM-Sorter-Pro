"""
ROM Hash Utilities

Dieses Modul enthält Funktionen zur Berechnung von Hash-Werten für ROM-Dateien,
die für die Datenbankintegration und ROM-Identifizierung verwendet werden.
"""

import os
import hashlib
from typing import Optional
from functools import lru_cache

@lru_cache(maxsize=1000)
def calculate_md5_fast(file_path: str, chunk_size: int = 1048576) -> Optional[str]:
    """
    Berechnet den MD5-Hash einer Datei mit optimaler Leistung.

    Args:
        file_path: Pfad zur Datei
        chunk_size: Größe der Chunks beim Lesen der Datei

    Returns:
        MD5-Hash als Hex-String oder None bei Fehler
    """
    try:
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                md5.update(data)
        return md5.hexdigest()
    except Exception as e:
        print(f"Fehler bei der MD5-Berechnung für {file_path}: {e}")
        return None

def calculate_sha1(file_path: str, chunk_size: int = 1048576) -> Optional[str]:
    """
    Berechnet den SHA1-Hash einer Datei.

    Args:
        file_path: Pfad zur Datei
        chunk_size: Größe der Chunks beim Lesen der Datei

    Returns:
        SHA1-Hash als Hex-String oder None bei Fehler
    """
    try:
        sha1 = hashlib.sha1()
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                sha1.update(data)
        return sha1.hexdigest()
    except Exception as e:
        print(f"Fehler bei der SHA1-Berechnung für {file_path}: {e}")
        return None

def calculate_crc32(file_path: str) -> Optional[str]:
    """
    Berechnet den CRC32-Hash einer Datei.

    Args:
        file_path: Pfad zur Datei

    Returns:
        CRC32-Wert als Hex-String oder None bei Fehler
    """
    try:
        import zlib
        crc = 0
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(8192)
                if not data:
                    break
                crc = zlib.crc32(data, crc)
        return "%08X" % (crc & 0xFFFFFFFF)
    except Exception as e:
        print(f"Fehler bei der CRC32-Berechnung für {file_path}: {e}")
        return None
