#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""ROM SARTER Pro - Database package This package contains all database-related modules and functionalities."""

from .console_db import (
    get_all_rom_extensions,
    get_supported_consoles,
    get_console_for_extension,
    get_console_folder_for_extension,
    get_consoles_by_manufacturer,
    ENHANCED_CONSOLE_DATABASE
)

from .connection_pool import (
    DatabaseConnectionPool,
    database_connection,
    ROM_DATABASE_PATH
)

from .external_db import (
    ExternalDatabaseManager
)

__all__ = [
    'get_all_rom_extensions',
    'get_supported_consoles',
    'get_console_for_extension',
    'get_console_folder_for_extension',
    'get_consoles_by_manufacturer',
    'ENHANCED_CONSOLE_DATABASE',
    'DatabaseConnectionPool',
    'database_connection',
    'ROM_DATABASE_PATH',
    'ExternalDatabaseManager'
]
