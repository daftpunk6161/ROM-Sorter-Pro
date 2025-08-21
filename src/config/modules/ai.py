#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROM Sorter Pro - AI Configuration Module

This module contains AI-related configuration classes.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging

from . import BaseConfigModule
from ...exceptions import ValidationError

logger = logging.getLogger(__name__)

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

def validate_float(value: Any, min_value: Optional[float] = None, max_value: Optional[float] = None,
                  field_name: str = "value") -> float:
    """
    Validate float with bounds checking.

    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        field_name: Name of field for error messages

    Returns:
        Validated float value

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(value, (int, float)):
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a number, got {type(value).__name__}")

    value = float(value)

    if min_value is not None and value < min_value:
        raise ValidationError(f"{field_name} must be >= {min_value}, got {value}")

    if max_value is not None and value > max_value:
        raise ValidationError(f"{field_name} must be <= {max_value}, got {value}")

    return value

@dataclass
class AIConfig(BaseConfigModule):
    """Security-enhanced AI configuration with validation."""
    enable_ai_detection: bool = False
    confidence_threshold: float = 0.85
    online_metadata: bool = False
    download_covers: bool = False
    enable_fuzzy_matching: bool = True

    def __init__(self, **kwargs):
        """Initialize with validated parameters."""
        self.enable_ai_detection = validate_boolean(
            kwargs.get('enable_ai_detection', False), 'enable_ai_detection')

        self.confidence_threshold = validate_float(
            kwargs.get('confidence_threshold', 0.85), 0.5, 1.0, 'confidence_threshold')

        self.online_metadata = validate_boolean(
            kwargs.get('online_metadata', False), 'online_metadata')

        self.download_covers = validate_boolean(
            kwargs.get('download_covers', False), 'download_covers')

        self.enable_fuzzy_matching = validate_boolean(
            kwargs.get('enable_fuzzy_matching', True), 'enable_fuzzy_matching')
