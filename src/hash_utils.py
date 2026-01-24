"""ROM hash utilities - This module contains functions for calculating hash values for ROM files, that are used for database integration and ROM identification."""

import os
import time
import hashlib
from typing import Optional, Tuple
from functools import lru_cache


def _read_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _read_float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


_IO_THROTTLE_MIN_SIZE_BYTES = max(0, _read_int_env("ROM_SORTER_IO_THROTTLE_MIN_MB", 512)) * 1024 * 1024
_IO_THROTTLE_SLEEP_SECONDS = max(0.0, _read_float_env("ROM_SORTER_IO_THROTTLE_SLEEP_MS", 1.0) / 1000.0)


def _get_file_signature(file_path: str) -> Optional[Tuple[int, int]]:
    try:
        stat = os.stat(file_path)
    except OSError as e:
        print(f"Fehler bei Dateistat für {file_path}: {e}")
        return None
    mtime_ns = getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))
    return mtime_ns, int(stat.st_size)


def _should_throttle(size_bytes: int) -> bool:
    return _IO_THROTTLE_SLEEP_SECONDS > 0 and size_bytes >= _IO_THROTTLE_MIN_SIZE_BYTES

@lru_cache(maxsize=1000)
def _calculate_md5_fast_cached(file_path: str, mtime_ns: int, size_bytes: int, chunk_size: int) -> Optional[str]:
    """Calculate the MD5 hash of a file with optimal performance. ARGS: File_Path: Path to the File Chunk_Size: Size of the Chunks When Reading the File Return: Md5-Hash as a Hex String Or None in the event of errors"""
    try:
        md5 = hashlib.md5()
        throttle = _should_throttle(size_bytes)
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                md5.update(data)
                if throttle:
                    time.sleep(_IO_THROTTLE_SLEEP_SECONDS)
        return md5.hexdigest()
    except Exception as e:
        print(f"Fehler bei der MD5-Berechnung für {file_path}: {e}")
        return None


def calculate_md5_fast(file_path: str, chunk_size: int = 1048576) -> Optional[str]:
    """Calculate the MD5 hash of a file with optimal performance. ARGS: File_Path: Path to the File Chunk_Size: Size of the Chunks When Reading the File Return: Md5-Hash as a Hex String Or None in the event of errors"""
    signature = _get_file_signature(file_path)
    if signature is None:
        return None
    mtime_ns, size_bytes = signature
    return _calculate_md5_fast_cached(file_path, mtime_ns, size_bytes, chunk_size)

@lru_cache(maxsize=1000)
def _calculate_sha1_cached(file_path: str, mtime_ns: int, size_bytes: int, chunk_size: int) -> Optional[str]:
    """Calculate the Sha1-Hash of a File. ARGS: File_Path: Path to the File Chunk_Size: Size of the Chunks When Reading the File Return: Sha1-Hash as a Hex-String Or None in the event of errors"""
    try:
        sha1 = hashlib.sha1()
        throttle = _should_throttle(size_bytes)
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                sha1.update(data)
                if throttle:
                    time.sleep(_IO_THROTTLE_SLEEP_SECONDS)
        return sha1.hexdigest()
    except Exception as e:
        print(f"Fehler bei der SHA1-Berechnung für {file_path}: {e}")
        return None


def calculate_sha1(file_path: str, chunk_size: int = 1048576) -> Optional[str]:
    """Calculate the Sha1-Hash of a File. ARGS: File_Path: Path to the File Chunk_Size: Size of the Chunks When Reading the File Return: Sha1-Hash as a Hex-String Or None in the event of errors"""
    signature = _get_file_signature(file_path)
    if signature is None:
        return None
    mtime_ns, size_bytes = signature
    return _calculate_sha1_cached(file_path, mtime_ns, size_bytes, chunk_size)


@lru_cache(maxsize=1000)
def _calculate_crc32_cached(file_path: str, mtime_ns: int, size_bytes: int, chunk_size: int) -> Optional[str]:
    """Calculate the Crc32-Hash of a File. Args: File_Path: Path to the File Return: CRC32 Value as a Hex String or None in the event of errors"""
    try:
        import zlib
        crc = 0
        throttle = _should_throttle(size_bytes)
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                crc = zlib.crc32(data, crc)
                if throttle:
                    time.sleep(_IO_THROTTLE_SLEEP_SECONDS)
        return "%08X" % (crc & 0xFFFFFFFF)
    except Exception as e:
        print(f"Fehler bei der CRC32-Berechnung für {file_path}: {e}")
        return None


def calculate_crc32(file_path: str) -> Optional[str]:
    """Calculate the Crc32-Hash of a File. Args: File_Path: Path to the File Return: CRC32 Value as a Hex String or None in the event of errors"""
    signature = _get_file_signature(file_path)
    if signature is None:
        return None
    mtime_ns, size_bytes = signature
    return _calculate_crc32_cached(file_path, mtime_ns, size_bytes, 8192)
