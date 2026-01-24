#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROM Sorter Pro - Performance Settings Configuration Module

This module contains performance-related configuration settings and classes
for managing system performance parameters like threads, memory limits, etc.
"""

from dataclasses import dataclass
from typing import Any, Optional
import multiprocessing
import logging

from . import BaseConfigModule
from ...exceptions import ValidationError

logger = logging.getLogger(__name__)

def validate_integer(value: Any, min_value: Optional[int] = None, max_value: Optional[int] = None,
                    field_name: str = "value") -> int:
    """
    Validate integer with bounds checking.

    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        field_name: Name of field for error messages

    Returns:
        Validated integer value

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(value, (int, float)):
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be an integer, got {type(value).__name__}")

    value = int(value)

    if min_value is not None and value < min_value:
        raise ValidationError(f"{field_name} must be >= {min_value}, got {value}")

    if max_value is not None and value > max_value:
        raise ValidationError(f"{field_name} must be <= {max_value}, got {value}")

    return value

def validate_boolean(value: Any, field_name: str = "value") -> bool:
    """
    Validate boolean value.

    Args:
        value: Value to validate
        field_name: Name of field for error messages

    Returns:
        Validated boolean value

    Raises:
        ValidationError: If validation fails
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        value_lower = value.lower()
        if value_lower in ('true', '1', 'yes', 'on'):
            return True
        elif value_lower in ('false', '0', 'no', 'off'):
            return False

    if isinstance(value, (int, float)):
        return bool(value)

    raise ValidationError(f"{field_name} must be a boolean value, got {type(value).__name__}")

@dataclass
class PerformanceConfig(BaseConfigModule):
    """Security-enhanced performance configuration with validation."""
    enable_caching: bool = True
    cache_size: int = 5000
    parallel_workers: Optional[int] = None
    batch_size: int = 300
    max_memory_usage: str = "1GB"
    use_fast_hash: bool = True
    lazy_loading: bool = True

    def __init__(self, **kwargs):
        """Custom init with comprehensive validation."""
        # Handle nested configuration from old format
        if 'caching' in kwargs:
            caching = kwargs.pop('caching')
            if isinstance(caching, dict):
                kwargs.update({k: v for k, v in caching.items() if k not in kwargs})

        if 'processing' in kwargs:
            processing = kwargs.pop('processing')
            if isinstance(processing, dict):
                kwargs.update({k: v for k, v in processing.items() if k not in kwargs})

        if 'optimization' in kwargs:
            optimization = kwargs.pop('optimization')
            if isinstance(optimization, dict):
                kwargs.update({k: v for k, v in optimization.items() if k not in kwargs})

        # Set defaults and validate
        self.enable_caching = validate_boolean(kwargs.get('enable_caching', True), 'enable_caching')
        self.cache_size = validate_integer(kwargs.get('cache_size', 5000), 100, 50000, 'cache_size')

        parallel_workers = kwargs.get('parallel_workers')
        if parallel_workers is not None:
            self.parallel_workers = validate_integer(parallel_workers, 1, 32, 'parallel_workers')
        else:
            # Auto-detect cores
            self.parallel_workers = max(1, multiprocessing.cpu_count() - 1)

        self.batch_size = validate_integer(kwargs.get('batch_size', 300), 10, 10000, 'batch_size')

        max_memory = kwargs.get('max_memory_usage', "1GB")
        self.max_memory_usage = max_memory

        self.use_fast_hash = validate_boolean(kwargs.get('use_fast_hash', True), 'use_fast_hash')
        self.lazy_loading = validate_boolean(kwargs.get('lazy_loading', True), 'lazy_loading')

    @property
    def max_workers(self):
        """Alias for parallel_workers to maintain backward compatibility."""
        return self.parallel_workers

    @max_workers.setter
    def max_workers(self, value):
        """Set the number of parallel workers."""
        self.parallel_workers = validate_integer(value, 1, 32, 'max_workers')
