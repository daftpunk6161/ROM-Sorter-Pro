#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Security-Paket

Dieses Paket enthält Sicherheitsfunktionen und Validierungen
für die ROM-Sortier-Anwendung.
"""

from .security_utils import (
    SecurityError,
    InvalidPathError,
    is_valid_directory,
    sanitize_path,
    check_environment_security,
    validate_input
)

from .file_security import (
    sanitize_filename,
    validate_file_operation,
    is_path_traversal_attack,
    validate_extension
)

# For downward compatibility - Validate_Path was the old name for Sanitize_Path
validate_path = sanitize_path

__all__ = [
    'SecurityError',
    'InvalidPathError',
    'is_valid_directory',
    'sanitize_path',
    'validate_path',  # Downward compatibility
    'check_environment_security',
    'validate_input',
    'sanitize_filename',
    'validate_file_operation',
    'is_path_traversal_attack',
    'validate_extension'
]
