#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""Rome Sorter Pro-Rome scanning package This package contains modules and classes for the efficient scanning and detection of ROM files. The scanning module consists of the following components: 1. Scanner.py basic classes for Rome scanning and parallel workmanship 2. Adaptive_scanner.py - Extended scanner with adaptive adaptation to the file system"""

from .scanner import (
    scan_directory,
    scan_directory_parallel,
    scan_directory_recursive,
    ROMScanner,
    OptimizedScanner
)

from .adaptive_scanner import (
    scan_directory_adaptive,
    get_scanner_performance_stats,
    AdaptiveScanner
)

__all__ = [
    'scan_directory',
    'scan_directory_parallel',
    'scan_directory_recursive',
    'scan_directory_adaptive',
    'get_scanner_performance_stats',
    'ROMScanner',
    'OptimizedScanner',
    'AdaptiveScanner'
]
