#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - ROM-Scanning-Paket

Dieses Paket enthält Module und Klassen für das effiziente Scannen und Erkennen von ROM-Dateien.

Das Scanning-Modul besteht aus folgenden Komponenten:
1. scanner.py - Basisklassen für ROM-Scanning und parallele Verarbeitung
2. adaptive_scanner.py - Erweiterte Scanner mit adaptiver Anpassung an das Dateisystem
"""

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
