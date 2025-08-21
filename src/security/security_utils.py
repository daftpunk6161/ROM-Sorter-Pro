#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Sicherheitsvalidierung

Dieses Modul enthält Funktionen zur sicheren Validierung von Pfaden
und Benutzereingaben, um Directory-Traversal und andere Angriffe zu verhindern.
"""

import os
import re
import logging
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Basisklasse für sicherheitsrelevante Error."""
    pass


class InvalidPathError(SecurityError):
    """Error bei ungültigen oder unsicheren Pfaden."""
    pass


def is_valid_directory(path: Union[str, Path], must_exist: bool = True) -> bool:
    """
    Überprüft, ob ein Pfad ein gültiges Verzeichnis ist.

    Args:
        path: Der zu prüfende Verzeichnispfad
        must_exist: Ob das Verzeichnis existieren muss

    Returns:
        True, wenn der Pfad ein gültiges Verzeichnis ist
    """
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
    """
    Bereinigt einen Pfad, um ihn sicherer zu machen.

    Args:
        path: Der zu bereinigende Pfad

    Returns:
        Bereinigter Pfad
    """
    if not path:
        return ""

# Save the original scouting sign
    orig_sep = '/' if '/' in path and '\\' not in path else os.path.sep

# Normalize the path
    normalized = os.path.normpath(path)

# Remove potentially dangerous sequences
    sanitized = re.sub(r'\.\.[/\\]', '', normalized)

# Restore the original scout separator
    if orig_sep == '/' and os.path.sep == '\\':
        sanitized = sanitized.replace('\\', '/')

    return sanitized


def validate_file_operation(file_path: Union[str, Path],
                          base_dir: Optional[Union[str, Path]] = None,
                          allow_read: bool = True,
                          allow_write: bool = True) -> bool:
    """
    Validiert eine Dateioperation hinsichtlich Sicherheit.

    Prüft, ob der Dateipfad sicher ist und innerhalb des erlaubten Bereichs liegt.

    Args:
        file_path: Der zu validierende Dateipfad
        base_dir: Das Basisverzeichnis, in dem die Datei liegen sollte
        allow_read: Ob Lesezugriff erlaubt ist
        allow_write: Ob Schreibzugriff erlaubt ist

    Returns:
        True, wenn die Operation sicher ist

    Raises:
        InvalidPathError: Wenn der Pfad unsicher ist
    """
# Convert to path objects
    file_path = Path(file_path).resolve()

# Check basic directory, if specified
    if base_dir:
        base_dir = Path(base_dir).resolve()

# Make sure the file is in the basic directory
        if not str(file_path).startswith(str(base_dir)):
            logger.warning(f"Security warning: File access outside base directory denied: {file_path}")
            raise InvalidPathError(f"File access outside allowed directory: {file_path}")

# Check special directories
    sensitive_dirs = ['/etc', '/var/log', '/root', '/boot', '/bin', '/sbin',
                     'C:\\Windows', 'C:\\Program Files', 'C:\\Users\\Administrator']

    for sensitive in sensitive_dirs:
        if str(file_path).startswith(sensitive):
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
    """
    Validiert und bereinigt eine Benutzereingabe.

    Args:
        input_value: Die zu validierende Eingabe
        max_length: Maximale zulässige Länge
        pattern: Optionales Regex-Muster für gültige Eingaben

    Returns:
        Die bereinigte Eingabe

    Raises:
        SecurityError: Wenn die Eingabe ungültig oder potenziell gefährlich ist
    """
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
