#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Consolidated Exception Classes

This module contains all exception classes used in the project,
centralized in one place to avoid duplication and improve consistency.
"""

from datetime import datetime
from typing import Dict, Any, Optional


class BaseError(Exception):
    """Base class for all project-specific errors."""

    def __init__(self, message: str, error_code: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code or "ERROR"
        self.details = details or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Converts the exception to a dictionary for structured logging."""
        return {
            'error_code': self.error_code,
            'message': str(self),
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


# =====================================================================================================
# Safety -related errors
# =====================================================================================================

class SecurityError(BaseError):
    """Base class for security-related errors."""

    def __init__(self, message: str, error_code: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code or "SECURITY_ERROR", details)


class PathTraversalError(SecurityError):
    """Raized when a Path Traversal Attack is Detected."""

    def __init__(self, message: str, path: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        path_details = details or {}
        if path:
            path_details['path'] = str(path)
        super().__init__(message, "PATH_TRAVERSAL", path_details)


class InvalidPathError(SecurityError):
    """Raised when path validation fails."""

    def __init__(self, message: str, path: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        path_details = details or {}
        if path:
            path_details['path'] = str(path)
        super().__init__(message, "INVALID_PATH", path_details)


# =====================================================================================================
# Configuration -related errors
# =====================================================================================================

class ConfigurationError(BaseError):
    """Base class for configuration errors."""

    def __init__(self, message: str, error_code: Optional[str] = None,
                 file_path: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        config_details = details or {}
        if file_path:
            config_details['file_path'] = file_path
        super().__init__(message, error_code or "CONFIG_ERROR", config_details)


class ValidationError(ConfigurationError):
    """Raised when configuration validation fails."""

    def __init__(self, message: str, field_name: Optional[str] = None,
                 expected_type: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        validation_details = details or {}
        if field_name:
            validation_details['field_name'] = field_name
        if expected_type:
            validation_details['expected_type'] = expected_type
        super().__init__(message, "VALIDATION_ERROR", None, validation_details)


# =====================================================================================================
# IO and data -related errors
# =====================================================================================================

class ScannerError(BaseError):
    """Raised when a file scanning operation fails."""

    def __init__(self, message: str, file_path: Optional[str] = None,
                 scanner_name: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        scanner_details = details or {}
        if file_path:
            scanner_details['file_path'] = file_path
        if scanner_name:
            scanner_details['scanner_name'] = scanner_name
        super().__init__(message, "SCANNER_ERROR", scanner_details)

class DataError(BaseError):
    """Base class for data-related errors."""

    def __init__(self, message: str, error_code: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code or "DATA_ERROR", details)


class DatabaseError(DataError):
    """Raised when database errors occur."""

    def __init__(self, message: str, query: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        db_details = details or {}
        if query:
# Make sure that no sensitive data appear in the log
            db_details['query_type'] = query.split()[0] if query else "UNKNOWN"
        super().__init__(message, "DB_ERROR", db_details)


class FileOperationError(DataError):
    """Raised when file operation errors occur."""

    def __init__(self, message: str, file_path: Optional[str] = None,
                 operation: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        file_details = details or {}
        if file_path:
            file_details['file_path'] = str(file_path)
        if operation:
            file_details['operation'] = operation
        super().__init__(message, "FILE_OP_ERROR", file_details)


# =====================================================================================================
# Processing errors
# =====================================================================================================

class ProcessingError(BaseError):
    """Base class for errors during ROM processing."""

    def __init__(self, message: str, error_code: Optional[str] = None,
                 rom_path: Optional[str] = None,
                 phase: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        proc_details = details or {}
        if rom_path:
            proc_details['rom_path'] = str(rom_path)
        if phase:
            proc_details['phase'] = phase
        super().__init__(message, error_code or "PROCESSING_ERROR", proc_details)


class ConsoleDetectionError(ProcessingError):
    """Raised when console detection fails."""

    def __init__(self, message: str, rom_path: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONSOLE_DETECTION_ERROR", rom_path, "detection", details)


class DuplicateHandlingError(ProcessingError):
    """Raised during errors in duplicate handling."""

    def __init__(self, message: str, rom_path: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DUPLICATE_ERROR", rom_path, "duplicate_check", details)
