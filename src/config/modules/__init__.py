#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROM Sorter Pro - Config Modules Package

This package contains modularized configuration components
to improve maintainability and organization.

Available modules:
- BaseConfigModule: Base class for all config modules
- perf_settings (PerformanceConfig): Performance-related settings
- sorting (SortingConfig): ROM sorting configuration
- ai (AIConfig): AI features configuration
"""

from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class BaseConfigModule:
    """Base class for all configuration modules."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert module to dictionary format."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create instance from dictionary data."""
        return cls(**data)
