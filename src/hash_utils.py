"""ROM hash utilities - This module contains functions for calculating hash values for ROM files, that are used for database integration and ROM identification."""

import os
import hashlib
from typing import Optional
from functools import lru_cache

@lru_cache(maxsize=1000)
def calculate_md5_fast(file_path: str, chunk_size: int = 1048576) -> Optional[str]:
    """Calculate the MD5 hash of a file with optimal performance. ARGS: File_Path: Path to the File Chunk_Size: Size of the Chunks When Reading the File Return: Md5-Hash as a Hex String Or None in the event of errors"""
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
    """Calculate the Sha1-Hash of a File. ARGS: File_Path: Path to the File Chunk_Size: Size of the Chunks When Reading the File Return: Sha1-Hash as a Hex-String Or None in the event of errors"""
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
    """Calculate the Crc32-Hash of a File. Args: File_Path: Path to the File Return: CRC32 Value as a Hex String or None in the event of errors"""
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
