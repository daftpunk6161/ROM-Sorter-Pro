#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROM Sorter Pro - Sorting Configuration Module

This module contains sorting-related configuration classes.
"""

from dataclasses import dataclass
from typing import Any, List
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

def validate_choice(value: Any, choices: List[Any], field_name: str = "value") -> Any:
    """
    Validate value is in allowed choices.

    Args:
        value: Value to validate
        choices: List of allowed values
        field_name: Name of field for error messages

    Returns:
        Validated value

    Raises:
        ValidationError: If validation fails
    """
    if value not in choices:
        raise ValidationError(f"{field_name} must be one of {choices}, got {value}")

    return value

@dataclass
class SortingConfig(BaseConfigModule):
    """Security-enhanced sorting configuration with validation."""
    console_sorting_enabled: bool = True
    create_console_folders: bool = True
    region_based_sorting: bool = True
    folder_structure: str = "console_first"
    create_unknown_folder: bool = True

    def __init__(self, **kwargs):
        """Initialize with validated parameters."""
        self.console_sorting_enabled = validate_boolean(
            kwargs.get('console_sorting_enabled', True), 'console_sorting_enabled')

        self.create_console_folders = validate_boolean(
            kwargs.get('create_console_folders', True), 'create_console_folders')

        self.region_based_sorting = validate_boolean(
            kwargs.get('region_based_sorting', True), 'region_based_sorting')

        self.folder_structure = validate_choice(
            kwargs.get('folder_structure', "console_first"),
            ["console_first", "region_first", "alphabetical", "flat"],
            'folder_structure')

        self.create_unknown_folder = validate_boolean(
            kwargs.get('create_unknown_folder', True), 'create_unknown_folder')
