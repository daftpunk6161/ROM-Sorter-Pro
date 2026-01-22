#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""ROM SARTER PRO - Safety validation This module contains functions for the safe validation of paths And user inputs to prevent directory traversal and other attacks."""

import os
import re
import logging
import sys
import stat
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from pathlib import PurePosixPath
import zipfile

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Basic class for safety -relevant error."""
    pass


class InvalidPathError(SecurityError):
    """Error in invalid or uncertain paths."""
    pass


def is_valid_directory(path: Union[str, Path], must_exist: bool = True) -> bool:
    """Check Whether a path is a valid directory. Args: Path: The Directory Path to Be Tested must_exist: Whether the Directory must exist Return: True if the path is a valid directory"""
    try:
        path_obj = Path(path).resolve()

# Check for existence
        if must_exist and not path_obj.exists():
            logger.warning(f"Verzeichnis existiert nicht: {path_obj}")
            return False

# Check Whether it is a directory (or could be)
        if path_obj.exists() and not path_obj.is_dir():
            logger.warning(f"Pfad ist kein Verzeichnis: {path_obj}")
            return False

# Check on suspicious paths
        suspicious_patterns = [
            r'\\\\', r'\.\.'  # Double backslashes or directory traversal
        ]
        path_str = str(path_obj)
        for pattern in suspicious_patterns:
            if re.search(pattern, path_str):
                logger.warning(f"Verdächtiger Pfad erkannt: {path_obj} (Muster: {pattern})")
                return False

        return True

    except Exception as e:
        logger.error(f"Fehler bei der Pfadvalidierung von {path}: {e}")
        return False


def sanitize_path(path: str) -> str:
    """Adjusted a path to make it safe. Args: Path: The Path to Be Adjusted Return: Cleaning Path"""
    if not path:
        return ""

# Save the original scouting sign
    orig_sep = '/' if '/' in path and '\\' not in path else os.path.sep

# Normalize the path
    sanitized = os.path.normpath(path)

# Restore the original scout separator
    if orig_sep == '/' and os.path.sep == '\\':
        sanitized = sanitized.replace('\\', '/')

    return sanitized


def resolve_path_safe(path: Union[str, Path]) -> Path:
    """Sanitize, validate, and resolve a path to an absolute Path."""
    raw = str(path)
    if is_path_traversal_attack(raw):
        raise InvalidPathError(f"Path traversal detected: {raw}")
    sanitized = sanitize_path(raw)
    if is_path_traversal_attack(sanitized):
        raise InvalidPathError(f"Path traversal detected: {sanitized}")
    return Path(sanitized).resolve()


def validate_file_operation(file_path: Union[str, Path],
                          base_dir: Optional[Union[str, Path]] = None,
                          allow_read: bool = True,
                          allow_write: bool = True) -> bool:
    """Validates a File Surgery in Terms of Security. Check Whether the File Path is Safe and is Within the Permitted Area. Args: File_Path: The File Path to Be validated base_dir: The basic directory in which the file should be allow_read: Whether reading access is allow_write: Whether wring access is allowed Return: True When Safe Raises: Invalid Path is unsavory"""
    file_path = resolve_path_safe(file_path)

# Check basic directory, if specified
    if base_dir:
        base_dir = resolve_path_safe(base_dir)

# Make sure the file is in the base directory (prefix-safe)
        try:
            file_path.relative_to(base_dir)
        except ValueError:
            logger.warning(f"Security warning: File access outside base directory denied: {file_path}")
            raise InvalidPathError(f"File access outside allowed directory: {file_path}")

# Check special directories
    sensitive_dirs = [
        '/etc', '/var/log', '/root', '/boot', '/bin', '/sbin',
        'C:\\Windows', 'C:\\Program Files', 'C:\\Users\\Administrator'
    ]

    def _is_subpath(target: Path, parent: Path) -> bool:
        try:
            target.relative_to(parent)
            return True
        except Exception:
            return False

    for sensitive in sensitive_dirs:
        try:
            sensitive_path = Path(sensitive).resolve()
        except Exception:
            continue
        try:
            if _is_subpath(file_path, sensitive_path):
                logger.warning(f"Security warning: Access to protected directory denied: {file_path}")
                raise InvalidPathError(f"Access to protected directory not allowed: {file_path}")
        except Exception:
            if os.name == "nt":
                if str(file_path).lower().startswith(str(sensitive_path).lower()):
                    logger.warning(f"Security warning: Access to protected directory denied: {file_path}")
                    raise InvalidPathError(f"Access to protected directory not allowed: {file_path}")

# Check for hidden files (Unix) and system files (Windows)
    if file_path.name.startswith('.') and sys.platform != 'win32':
        logger.warning(f"Warning: Access to hidden file: {file_path}")

# Check whether writing access is required, but is not allowed
    if not allow_write and file_path.exists() and os.access(str(file_path), os.W_OK):
        logger.warning(f"Security warning: Write access not allowed for: {file_path}")
        raise InvalidPathError(f"Write access not allowed for: {file_path}")

# Check whether reading access is needed, but is not allowed
    if not allow_read and file_path.exists() and os.access(str(file_path), os.R_OK):
        logger.warning(f"Security warning: Read access not allowed for: {file_path}")
        raise InvalidPathError(f"Read access not allowed for: {file_path}")

    return True


def check_environment_security() -> Dict[str, Any]:
    """
    Checks the security of the execution environment.

    Returns:
        Dict with security information and warnings
    """
    results = {
        'security_warnings': [],
        'is_secure': True
    }

# Check authorizations of the current directory
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if os.access(current_dir, os.W_OK):
# Current directory permits are okay
            pass
    except Exception as e:
        results['security_warnings'].append(f"Could not check permissions: {e}")
        results['is_secure'] = False

# Check Python version
    if sys.version_info < (3, 8):
        results['security_warnings'].append(
            f"Outdated Python version {sys.version}. Version 3.8 or higher recommended."
        )

# Check on uncertain environment variables
    if os.environ.get('PYTHONHTTPSVERIFY') == '0':
        results['security_warnings'].append(
            "PYTHONHTTPSVERIFY=0 found. SSL certificate verification is disabled."
        )
        results['is_secure'] = False

    if results['security_warnings']:
        for warning in results['security_warnings']:
            logger.warning(f"Security warning: {warning}")

    return results


def validate_input(input_value: str, max_length: int = 255, pattern: Optional[str] = None) -> str:
    """Validated and Adjusted a user input. ARGS: Input_value: The Entry to Be validated max_length: Maximum permissible Length patterns: Optional regex pattern for valid inputs return: The adjusted input raises: Security Terror: if the input is invalid or potential danger"""
    if not input_value:
        return ""

# Length check
    if len(input_value) > max_length:
        raise SecurityError(f"Eingabe überschreitet maximale Länge von {max_length} Zeichen")

# Remove potentially dangerous signs
    sanitized = re.sub(r'[;<>&\'"()]', '', input_value)

# Check against patterns, if specified
    if pattern and not re.fullmatch(pattern, sanitized):
        raise SecurityError(f"Eingabe entspricht nicht dem erlaubten Muster: {pattern}")

    return sanitized


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize filenames for safe use across file systems."""
    if not filename:
        raise ValueError("Dateiname darf nicht leer sein")

    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f]', '_', filename)
    sanitized = sanitized.strip(' .')

    if not sanitized:
        sanitized = "unknown_file"

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


def normalize_filename(filename: str, max_length: int = 255) -> str:
    """Normalize a filename by reusing sanitize rules."""
    return sanitize_filename(filename, max_length=max_length)


def is_path_traversal_attack(path: str) -> bool:
    """Detect typical path traversal patterns."""
    suspicious_patterns = [
        r'\.{2}/', r'\.{2}\\',
        r'/\.{2}', r'\\\.{2}',
        r'^\.{2}$', r'^\.{2}/',
        r'%2e%2e', r'%2E%2E',
        r'\\\\', r'//',
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, path):
            logger.warning(f"Möglicher Path-Traversal-Angriff erkannt: {path}")
            return True

    unicode_normalization_check = Path(os.path.normpath(path)).as_posix()
    if unicode_normalization_check != Path(path).as_posix():
        logger.warning(f"Verdächtige Unicode-Normalisierung erkannt: {path}")
        return True

    return False


def is_safe_archive_member(member: Union[str, zipfile.ZipInfo]) -> bool:
    """Check for safe archive members (no traversal, no abs paths, no symlinks)."""
    if isinstance(member, zipfile.ZipInfo):
        member_name = member.filename
        try:
            mode = stat.S_IFMT(member.external_attr >> 16)
            if mode == stat.S_IFLNK:
                return False
        except Exception:
            pass
    else:
        member_name = str(member)

    if not member_name:
        return False
    if "\x00" in member_name:
        return False
    if member_name.startswith(('/', '\\')):
        return False
    if re.match(r"^[a-zA-Z]:", member_name):
        return False
    if member_name.startswith("\\\\"):
        return False
    try:
        parts = PurePosixPath(member_name.replace("\\", "/")).parts
    except Exception:
        return False
    return ".." not in parts


def validate_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """Validate file extension against a whitelist."""
    normalized_extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in allowed_extensions]
    _, ext = os.path.splitext(filename.lower())
    return ext in normalized_extensions


def safe_extract_zip(zip_path: Union[str, Path], dest_dir: Union[str, Path]) -> None:
    """Safely extract a ZIP file, preventing zip-slip path traversal."""
    zip_path = Path(zip_path)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_root = dest_dir.resolve()

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.infolist():
            if not is_safe_archive_member(member):
                raise InvalidPathError(f"Unsafe archive member blocked: {member.filename}")
            member_path = dest_root / member.filename
            try:
                resolved = member_path.resolve()
            except Exception as e:
                raise InvalidPathError(f"Invalid ZIP entry path: {member.filename}") from e

            if not str(resolved).startswith(str(dest_root)):
                raise InvalidPathError(f"Zip-slip detected: {member.filename}")

        zip_ref.extractall(dest_root)
