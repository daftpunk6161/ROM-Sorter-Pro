#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Core Package

This package contains core functionality and utilities for the application.
"""
# ruff: noqa: E402

from .file_utils import (
    create_directory_if_not_exists,
    enhanced_copy_file,
    calculate_file_hash,
    get_file_extension,
    safe_move_file,
    normalize_filename
)

from ..utils.performance_enhanced import (
    PerformanceMonitor as AdvancedPerformanceMonitor,
    measure_time as measure_performance,
    measure_block
)

# Compatibility wrapper for old API
def get_performance_summary():
    return AdvancedPerformanceMonitor.get_instance().get_summary()

# Compatibility function for old API
def print_performance_summary(summary=None):
    summary_data = summary if summary is not None else get_performance_summary()
    print(summary_data)

# Global monitor for old API compatibility
global_monitor = AdvancedPerformanceMonitor.get_instance()

from .rom_utils import (
    get_all_rom_extensions,
    get_sorted_rom_list,
    group_roms_by_console,
    is_valid_rom_file,
    calculate_rom_signature
)

__all__ = [
# File Utilities
    'create_directory_if_not_exists',
    'enhanced_copy_file',
    'calculate_file_hash',
    'get_file_extension',
    'safe_move_file',
    'normalize_filename',

    # Performance monitoring
    'AdvancedPerformanceMonitor',
    'measure_performance',
    'measure_block',
    'get_performance_summary',
    'print_performance_summary',
    'global_monitor',

# Rome Utilities
    'get_all_rom_extensions',
    'get_sorted_rom_list',
    'group_roms_by_console',
    'is_valid_rom_file',
    'calculate_rom_signature',
    'print_performance_summary',
    'global_monitor'
]
