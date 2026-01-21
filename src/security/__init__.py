#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""ROM SARTER Pro Security package This package contains security functions and validations for the Rome sorting application."""

from .security_utils import (
    SecurityError,
    InvalidPathError,
    is_valid_directory,
    sanitize_path,
    sanitize_filename,
    validate_file_operation,
    check_environment_security,
    validate_input,
    is_path_traversal_attack,
    validate_extension,
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
