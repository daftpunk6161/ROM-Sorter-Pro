#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROM Sorter Pro - Performance Settings Configuration Module

This module contains performance-related configuration settings and classes
for managing system performance parameters like threads, memory limits, etc.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import multiprocessing
import logging

from . import BaseConfigModule
from ...exceptions import ValidationError

logger = logging.getLogger(__name__)

def validate_integer(value: Any, min_value: Optional[int] = None, max_value: Optional[int] = None,
                    field_name: str = "value") -> int:
    """Validate Integer with Bounds Checking. Args: Value: Value to validate min_value: minimum allowed value max_value: Maximum allowed value field_name: name of field for error measurement Return: validated integer value raises: validationeror: if value is not a valid integer or outside bounds"""
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be an integer, got {type(value).__name__}")

    if min_value is not None and int_value < min_value:
        raise ValidationError(f"{field_name} must be at least {min_value}")

    if max_value is not None and int_value > max_value:
        raise ValidationError(f"{field_name} must not exceed {max_value}")

    return int_value

@dataclass
class PerformanceConfig(BaseConfigModule):
    """Configuration Settings for Application Performance. Attributes: Max_threads: Maximum Number of Threads for Parallel Operations Memory_Limit_MB: Maximum Memory Usage Limit in MB (0 = No Limit) Cache_Size: Size of the Cache in Entries Scan_Chunk_Size: Number of Files to Process in A Chunk During Scanning Enable_lazy_Loading: Whether to use Lazy Loading for Large Datasets Optimization_Level: Level of Optimization (0-3)"""

    max_threads: int = 0
    memory_limit_mb: int = 0
    cache_size: int = 1000
    scan_chunk_size: int = 500
    enable_lazy_loading: bool = True
    optimization_level: int = 2

    def __post_init__(self):
        """Validate configuration values after initialization."""
        # Set max_threads to CPU count if 0 or negative
        if self.max_threads <= 0:
            self.max_threads = multiprocessing.cpu_count()
        else:
            self.max_threads = validate_integer(self.max_threads, 1, 32, "max_threads")

        # Validate other numeric fields
        self.memory_limit_mb = validate_integer(self.memory_limit_mb, 0, None, "memory_limit_mb")
        self.cache_size = validate_integer(self.cache_size, 10, 100000, "cache_size")
        self.scan_chunk_size = validate_integer(self.scan_chunk_size, 1, 10000, "scan_chunk_size")
        self.optimization_level = validate_integer(self.optimization_level, 0, 3, "optimization_level")

        # Validate boolean fields
        if not isinstance(self.enable_lazy_loading, bool):
            raise ValidationError("enable_lazy_loading must be a boolean")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "max_threads": self.max_threads,
            "memory_limit_mb": self.memory_limit_mb,
            "cache_size": self.cache_size,
            "scan_chunk_size": self.scan_chunk_size,
            "enable_lazy_loading": self.enable_lazy_loading,
            "optimization_level": self.optimization_level,
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "PerformanceConfig":
        """Create configuration from dictionary."""
        return cls(
            max_threads=config_dict.get("max_threads", 0),
            memory_limit_mb=config_dict.get("memory_limit_mb", 0),
            cache_size=config_dict.get("cache_size", 1000),
            scan_chunk_size=config_dict.get("scan_chunk_size", 500),
            enable_lazy_loading=config_dict.get("enable_lazy_loading", True),
            optimization_level=config_dict.get("optimization_level", 2),
        )
