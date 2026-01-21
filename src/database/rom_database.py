#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Enhanced Database Module v2.1.8
Phase 1 Implementation: Desktop Optimization

This module provides an enhanced database layer for ROM Sorter Pro.
It supports local caching, highly optimized queries, and improved metadata management.
"""

# Standard libraries
import os
import json
import logging
import sqlite3
import time
import hashlib
import threading
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any

from .db_paths import get_rom_db_path

# Set up logging
logger = logging.getLogger(__name__)

# Constant
DEFAULT_DB_PATH = get_rom_db_path()
DEFAULT_CACHE_PATH = 'rom_databases/cache'
SCHEMA_VERSION = '2.1.8'  # Current schema version

class ROMDatabase:
    """Enhanced database implementation for ROM metadata."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH, cache_path: str = DEFAULT_CACHE_PATH,
                 auto_commit: bool = True, cache_enabled: bool = True):
        """Initialized the database connection. Args: DB_Path: path to the SQLite database file Cache_path: path to the cache directory Auto_Commit: Whether changes should be automatically commented Cache_enabled: Whether the memory cache should be activated"""
        self.db_path = db_path
        self.cache_path = cache_path
        self.auto_commit = auto_commit
        self.cache_enabled = cache_enabled

# Thread safe
        self._lock = threading.RLock()

# Memory Cache for Frequently Accessed Data
        self._cache = {
            'roms': {},         # CRC32 -> ROM-Info
            'systems': {},      # System-ID -> System-Info
            'collections': {}   # Collection-ID -> Collection-Info
        }

# Make sure that directories exist
        self._ensure_directories()

# Initialize connection
        self.conn = None
        self.cursor = None
        self._connect_db()

# Check and initialize scheme
        self._init_schema()

    def _ensure_directories(self):
        """Ensures that all required directories exist."""
# Database Directory
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

# Cache directory
        if self.cache_enabled and not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)

    def _connect_db(self):
        """Make the database connection."""
        try:
            if self.conn:
                self.conn.close()

            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Ergebnisse als dict
            self.cursor = self.conn.cursor()

# SQLite optimizations
            self.cursor.execute('PRAGMA journal_mode=WAL')
            self.cursor.execute('PRAGMA synchronous=NORMAL')
            self.cursor.execute('PRAGMA cache_size=10000')
            self.cursor.execute('PRAGMA temp_store=MEMORY')
            self.cursor.execute('PRAGMA mmap_size=30000000000')

            logger.debug(f"Datenbankverbindung hergestellt: {self.db_path}")

        except sqlite3.Error as e:
            logger.error(f"Fehler beim Verbinden mit Datenbank: {e}")
            raise

    def _init_schema(self):
        """Initializes the database schema if needed."""
        with self._lock:
            try:
# Check If the version Table Exists
                self.cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='version'"
                )
                version_table_exists = bool(self.cursor.fetchone())

                if not version_table_exists:
# Create the version table
                    self.cursor.execute('''
                    CREATE TABLE version (
                        id INTEGER PRIMARY KEY,
                        version TEXT NOT NULL,
                        updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    ''')

# Insert the Current version
                    self.cursor.execute(
                        "INSERT INTO version (version) VALUES (?)",
                        (SCHEMA_VERSION,)
                    )

# Create the tables
                    self._create_tables()

                    if self.auto_commit:
                        self.conn.commit()
                else:
# Get the Current version
                    self.cursor.execute(
                        "SELECT version FROM version ORDER BY id DESC LIMIT 1"
                    )
                    current_version = self.cursor.fetchone()['version']

# Run Migration If Needed
                    if current_version != SCHEMA_VERSION:
                        logger.info(
                            f"Migrating database schema from {current_version} "
                            f"to {SCHEMA_VERSION}"
                        )
                        self._migrate_schema(current_version)

            except sqlite3.Error as e:
                logger.error(f"Error initializing schema: {e}")
                if self.auto_commit:
                    self.conn.rollback()
                raise

    def _create_tables(self):
        """Creates all necessary tables in the database."""
# Table for Systems
        self.cursor.execute('''
        CREATE TABLE systems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            extensions TEXT NOT NULL,
            description TEXT,
            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

# Table for Rome
        self.cursor.execute('''
        CREATE TABLE roms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            system_id INTEGER NOT NULL,
            path TEXT,
            size INTEGER,
            crc32 TEXT,
            md5 TEXT,
            sha1 TEXT,
            verified BOOLEAN DEFAULT 0,
            favorite BOOLEAN DEFAULT 0,
            rating INTEGER DEFAULT 0,
            play_count INTEGER DEFAULT 0,
            last_played TIMESTAMP,
            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (system_id) REFERENCES systems(id),
            UNIQUE(crc32, system_id)
        )
        ''')

# Table for Collections
        self.cursor.execute('''
        CREATE TABLE collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

# Table for Rome in Collections (M: N Relationship)
        self.cursor.execute('''
        CREATE TABLE collection_roms (
            collection_id INTEGER,
            rom_id INTEGER,
            added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (collection_id, rom_id),
            FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
            FOREIGN KEY (rom_id) REFERENCES roms(id) ON DELETE CASCADE
        )
        ''')

# Table for Metadata
        self.cursor.execute('''
        CREATE TABLE metadata (
            rom_id INTEGER,
            key TEXT,
            value TEXT,
            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (rom_id, key),
            FOREIGN KEY (rom_id) REFERENCES roms(id) ON DELETE CASCADE
        )
        ''')

# Indices for Fast Queries
        self.cursor.execute('CREATE INDEX idx_roms_crc32 ON roms(crc32)')
        self.cursor.execute('CREATE INDEX idx_roms_system_id ON roms(system_id)')
        self.cursor.execute('CREATE INDEX idx_roms_name ON roms(name)')
        self.cursor.execute('CREATE INDEX idx_metadata_rom_id ON metadata(rom_id)')

        logger.info("Database schema created")

        # Insert default systems
        self._insert_default_systems()

    def _insert_default_systems(self):
        """Adds default systems to the database."""
        default_systems = [
            ('Nintendo Entertainment System', '.nes,.fds', 'Nintendo 8-Bit-Konsole'),
            ('Super Nintendo', '.sfc,.smc', 'Nintendo 16-Bit-Konsole'),
            ('Nintendo 64', '.n64,.z64,.v64', 'Nintendo 64-Bit-Konsole'),
            ('GameBoy', '.gb,.gbc', 'Nintendo tragbare 8-Bit-Konsole'),
            ('GameBoy Advance', '.gba', 'Nintendo tragbare 32-Bit-Konsole'),
            ('Nintendo DS', '.nds', 'Nintendo tragbare Dual-Screen-Konsole'),
            ('Sega Master System', '.sms', 'Sega 8-Bit-Konsole'),
            ('Sega Genesis/Mega Drive', '.gen,.bin,.md,.smd', 'Sega 16-Bit-Konsole'),
            ('Sega CD', '.iso,.bin,.img', 'Sega CD extension for Genesis'),
            ('Sega 32X', '.32x', 'Sega 32X extension for Genesis'),
            ('Sega Saturn', '.iso,.bin,.img', 'Sega 32-Bit-Konsole'),
            ('Sega Dreamcast', '.gdi,.cdi,.chd', 'Sega 128-Bit-Konsole'),
            ('PlayStation', '.iso,.bin,.img,.chd,.pbp', 'Sony 32-Bit-Konsole'),
            ('PlayStation 2', '.iso,.bin,.img,.chd', 'Sony 128-Bit-Konsole'),
            ('PlayStation Portable', '.iso,.cso', 'Sony tragbare Konsole'),
            ('TurboGrafx-16/PC Engine', '.pce', 'NEC 16-Bit-Konsole'),
            ('Neo Geo', '.neo', 'SNK Arcade-basierte Konsole'),
            ('Atari 2600', '.a26', 'Atari early home console'),
            ('Atari 7800', '.a78', 'Atari Heimkonsole'),
            ('Arcade', '.zip,.7z', 'Arcade-Systeme')
        ]

        for name, extensions, description in default_systems:
            self.cursor.execute(
                "INSERT OR IGNORE INTO systems (name, extensions, description) VALUES (?, ?, ?)",
                (name, extensions, description)
            )

    def _migrate_schema(self, current_version: str):
        """Performs A Migration of the Database Scheme. Args: Current_Version: The Current version of the Schema"""
        # Create backup
        backup_path = f"{self.db_path}.backup-{current_version}"
        shutil.copy2(self.db_path, backup_path)
        logger.info(f"Database backup created: {backup_path}")

# Migration Logic for different versions
        # (In a real implementation, migration steps would be here)

        # Update version
        self.cursor.execute(
            "INSERT INTO version (version) VALUES (?)",
            (SCHEMA_VERSION,)
        )

        if self.auto_commit:
            self.conn.commit()

        logger.info(f"Migration to schema version {SCHEMA_VERSION} completed")

    def add_rom(self, name: str, system_id: int, file_path: Optional[str] = None,
                size: Optional[int] = None, crc32: Optional[str] = None,
                md5: Optional[str] = None, sha1: Optional[str] = None,
                metadata: Optional[Dict[str, str]] = None) -> int:
        """Add a new rome to the database or update to existing one. ARGS: Name: Name of the Rome File System_ID: ID of the Associated System File_Path: Optional Path to the File Size: Optional File Size Crc32: Optional CRC32 Checksum MD5: Optional MD5 Checks Sha1: Optional SHA1 Checks Metadata: Optional Dictionary with Metadata Return: Id of the Added Or Updated Rome"""
        with self._lock:
            try:
# Check IF ROM Already Exist (Based on Crc32)
                rom_id = None
                if crc32:
                    self.cursor.execute(
                        "SELECT id FROM roms WHERE crc32=? AND system_id=?",
                        (crc32, system_id)
                    )
                    result = self.cursor.fetchone()
                    if result:
                        rom_id = result['id']

                now = datetime.now().isoformat()

                if rom_id:
# Update Existing Rome
                    self.cursor.execute('''
                    UPDATE roms SET
                        name=?, path=?, size=?, md5=?, sha1=?, updated=?
                    WHERE id=?
                    ''', (name, file_path, size, md5, sha1, now, rom_id))
                else:
# Add New Rome
                    self.cursor.execute('''
                    INSERT INTO roms
                        (name, system_id, path, size, crc32, md5, sha1)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (name, system_id, file_path, size, crc32, md5, sha1))

                    rom_id = self.cursor.lastrowid

# Add Metadata If Available
                if metadata and rom_id:
                    for key, value in metadata.items():
                        self.cursor.execute('''
                        INSERT OR REPLACE INTO metadata (rom_id, key, value, updated)
                        VALUES (?, ?, ?, ?)
                        ''', (rom_id, key, value, now))

                if self.auto_commit:
                    self.conn.commit()

# Update cache
                if self.cache_enabled and crc32:
                    self._update_rom_cache(rom_id, name, system_id, file_path,
                                          size, crc32, md5, sha1, metadata)

                return rom_id

            except sqlite3.Error as e:
                logger.error(f"Error adding ROM: {e}")
                if self.auto_commit:
                    self.conn.rollback()
                raise

    def get_rom_by_crc(self, crc32: str, system_id: Optional[int] = None) -> Optional[Dict]:
        """Searches for a rome by Its Crc32 Checksum. ARGS: CRC32: CRC32 Checksum System_ID: Optional System ID to Narrow Down Search Return: Rome Information as Dictionary Or None IF Not Found"""
# Try to Load from Cache First
        if self.cache_enabled and crc32 in self._cache['roms']:
            cached_rom = self._cache['roms'][crc32]
# If System_id is Specified, Check for a Match
            if system_id is None or cached_rom.get('system_id') == system_id:
                return cached_rom.copy()

        with self._lock:
            try:
                query = '''
                SELECT r.*, s.name as system_name
                FROM roms r
                JOIN systems s ON r.system_id = s.id
                WHERE r.crc32 = ?
                '''
                params = [crc32]

                if system_id is not None:
                    query += " AND r.system_id = ?"
                    params.append(system_id)

                self.cursor.execute(query, params)
                rom = self.cursor.fetchone()

                if rom:
# Wand Row in Dict Um
                    rom_dict = dict(rom)

# Hole metadata
                    metadata = self.get_rom_metadata(rom_dict['id'])
                    rom_dict['metadata'] = metadata

# Update cache
                    if self.cache_enabled:
                        self._cache['roms'][crc32] = rom_dict.copy()

                    return rom_dict

                return None

            except sqlite3.Error as e:
                logger.error(f"Fehler bei der Suche nach ROM mit CRC32 {crc32}: {e}")
                return None

    def get_rom_by_id(self, rom_id: int) -> Optional[Dict]:
        """Get rom information based on the id. ARGS: ROM_ID: ROM ID Return: Rome Information as a dictionary or none, if not found"""
        with self._lock:
            try:
                self.cursor.execute('''
                SELECT r.*, s.name as system_name
                FROM roms r
                JOIN systems s ON r.system_id = s.id
                WHERE r.id = ?
                ''', (rom_id,))

                rom = self.cursor.fetchone()

                if rom:
# Wand Row in Dict Um
                    rom_dict = dict(rom)

# Hole metadata
                    metadata = self.get_rom_metadata(rom_id)
                    rom_dict['metadata'] = metadata

# Update cache
                    if self.cache_enabled and rom_dict.get('crc32'):
                        self._cache['roms'][rom_dict['crc32']] = rom_dict.copy()

                    return rom_dict

                return None

            except sqlite3.Error as e:
                logger.error(f"Fehler beim Abrufen des ROMs mit ID {rom_id}: {e}")
                return None

    def search_roms(self, query: str, system_id: Optional[int] = None,
                   limit: int = 100, offset: int = 0) -> List[Dict]:
        """Rome searches for name or metadata. Args: query: search term System_id: Optional system ID for limitation Limit: Maximum number of results Offset: Offset for pagination Return: List of Rome Dictionaries"""
        with self._lock:
            try:
                search_query = f"%{query}%"

                base_query = '''
                SELECT DISTINCT r.*, s.name as system_name
                FROM roms r
                JOIN systems s ON r.system_id = s.id
                LEFT JOIN metadata m ON r.id = m.rom_id
                WHERE (r.name LIKE ? OR m.value LIKE ?)
                '''

                params = [search_query, search_query]

                if system_id is not None:
                    base_query += " AND r.system_id = ?"
                    params.append(system_id)

                base_query += " ORDER BY r.name LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                self.cursor.execute(base_query, params)
                results = self.cursor.fetchall()

# Convert results and hole metadata
                roms = []
                for rom in results:
                    rom_dict = dict(rom)
                    rom_dict['metadata'] = self.get_rom_metadata(rom_dict['id'])
                    roms.append(rom_dict)

                return roms

            except sqlite3.Error as e:
                logger.error(f"Fehler bei der ROM-Suche nach '{query}': {e}")
                return []

    def get_rom_metadata(self, rom_id: int) -> Dict[str, str]:
        """Get all metadata for a rome. Args: rom_id: rom id return: dictionary with metadata (key -> value)"""
        with self._lock:
            try:
                self.cursor.execute(
                    "SELECT key, value FROM metadata WHERE rom_id = ?",
                    (rom_id,)
                )

                metadata = {}
                for row in self.cursor.fetchall():
                    metadata[row['key']] = row['value']

                return metadata

            except sqlite3.Error as e:
                logger.error(f"Error retrieving metadata for ROM {rom_id}: {e}")
                return {}

    def set_rom_metadata(self, rom_id: int, key: str, value: str) -> bool:
        """Set a metadata value for a rome. ARGS: ROM_ID: ROM ID KEY: Metadata Key Value: Metadata Value Return: True in the Event of Success, False in the event of errors"""
        with self._lock:
            try:
                now = datetime.now().isoformat()

                self.cursor.execute('''
                INSERT OR REPLACE INTO metadata (rom_id, key, value, updated)
                VALUES (?, ?, ?, ?)
                ''', (rom_id, key, value, now))

                if self.auto_commit:
                    self.conn.commit()

# Update cache, if available
                if self.cache_enabled:
                    for crc32, rom in self._cache['roms'].items():
                        if rom.get('id') == rom_id:
                            if 'metadata' not in rom:
                                rom['metadata'] = {}
                            rom['metadata'][key] = value
                            break

                return True

            except sqlite3.Error as e:
                logger.error(f"Error setting metadata for ROM {rom_id}: {e}")
                if self.auto_commit:
                    self.conn.rollback()
                return False

    def get_system_by_id(self, system_id: int) -> Optional[Dict]:
        """Get System Information Based on the ID. ARGS: System_id: System ID Return: System Information as a dictionary or none, if not found"""
# Try to load from the cache first
        if self.cache_enabled and system_id in self._cache['systems']:
            return self._cache['systems'][system_id].copy()

        with self._lock:
            try:
                self.cursor.execute(
                    "SELECT * FROM systems WHERE id = ?",
                    (system_id,)
                )

                system = self.cursor.fetchone()

                if system:
# Wand Row in Dict Um
                    system_dict = dict(system)

# Update cache
                    if self.cache_enabled:
                        self._cache['systems'][system_id] = system_dict.copy()

                    return system_dict

                return None

            except sqlite3.Error as e:
                logger.error(f"Fehler beim Abrufen des Systems mit ID {system_id}: {e}")
                return None

    def get_system_by_name(self, name: str) -> Optional[Dict]:
        """Get System Information Based on the name. ARGS: Name: System Name Return: System Information as a dictionary or none, if not found"""
# Finding tests from the cache
        if self.cache_enabled:
            for system_id, system in self._cache['systems'].items():
                if system.get('name') == name:
                    return system.copy()

        with self._lock:
            try:
                self.cursor.execute(
                    "SELECT * FROM systems WHERE name = ?",
                    (name,)
                )

                system = self.cursor.fetchone()

                if system:
# Wand Row in Dict Um
                    system_dict = dict(system)

# Update cache
                    if self.cache_enabled:
                        self._cache['systems'][system_dict['id']] = system_dict.copy()

                    return system_dict

                return None

            except sqlite3.Error as e:
                logger.error(f"Fehler beim Abrufen des Systems mit Namen {name}: {e}")
                return None

    def get_all_systems(self) -> List[Dict]:
        """Get all available systems. Return: List of system dictionaries"""
        with self._lock:
            try:
                self.cursor.execute("SELECT * FROM systems ORDER BY name")

                systems = []
                for system in self.cursor.fetchall():
                    system_dict = dict(system)

# Update cache
                    if self.cache_enabled:
                        self._cache['systems'][system_dict['id']] = system_dict.copy()

                    systems.append(system_dict)

                return systems

            except sqlite3.Error as e:
                logger.error(f"Fehler beim Abrufen aller Systeme: {e}")
                return []

    def create_collection(self, name: str, description: str = "") -> int:
        """Creates a new collection. ARGS: Name: Name of the Collection Description: Optional Description Return: ID of the Created Collection Or -1 in the event of errors"""
        with self._lock:
            try:
                self.cursor.execute(
                    "INSERT INTO collections (name, description) VALUES (?, ?)",
                    (name, description)
                )

                collection_id = self.cursor.lastrowid

                if self.auto_commit:
                    self.conn.commit()

# Update cache
                if self.cache_enabled:
                    self._cache['collections'][collection_id] = {
                        'id': collection_id,
                        'name': name,
                        'description': description
                    }

                return collection_id

            except sqlite3.Error as e:
                logger.error(f"Fehler beim Erstellen der Sammlung '{name}': {e}")
                if self.auto_commit:
                    self.conn.rollback()
                return -1

    def add_rom_to_collection(self, collection_id: int, rom_id: int) -> bool:
        """Adds a rome to a collection. ARGS: Collection_ID: ID of the Collection Rom_id: Id of the Rome Return: True in the event of Success, False in the event of errors"""
        with self._lock:
            try:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO collection_roms (collection_id, rom_id) VALUES (?, ?)",
                    (collection_id, rom_id)
                )

                if self.auto_commit:
                    self.conn.commit()

                return True

            except sqlite3.Error as e:
                logger.error(f"Error adding ROM {rom_id} to collection {collection_id}: {e}")
                if self.auto_commit:
                    self.conn.rollback()
                return False

    def get_collection_roms(self, collection_id: int) -> List[Dict]:
        """Get all the roms in a collection. ARGS: Collection_ID: ID of the Collection Return: List of Rome Dictionaries"""
        with self._lock:
            try:
                self.cursor.execute('''
                SELECT r.*, s.name as system_name
                FROM roms r
                JOIN systems s ON r.system_id = s.id
                JOIN collection_roms cr ON r.id = cr.rom_id
                WHERE cr.collection_id = ?
                ORDER BY r.name
                ''', (collection_id,))

                results = self.cursor.fetchall()

# Convert results and hole metadata
                roms = []
                for rom in results:
                    rom_dict = dict(rom)
                    rom_dict['metadata'] = self.get_rom_metadata(rom_dict['id'])
                    roms.append(rom_dict)

                return roms

            except sqlite3.Error as e:
                logger.error(f"Error retrieving ROMs for collection {collection_id}: {e}")
                return []

    def get_statistics(self) -> Dict[str, Any]:
        """Collect statistics via the database. Return: Dictionary with statistics information"""
        with self._lock:
            try:
                stats = {}

# Total number of Rome
                self.cursor.execute("SELECT COUNT(*) as count FROM roms")
                stats['total_roms'] = self.cursor.fetchone()['count']

# ROMS Pro System
                self.cursor.execute('''
                SELECT s.name, COUNT(r.id) as count
                FROM systems s
                LEFT JOIN roms r ON s.id = r.system_id
                GROUP BY s.id
                ORDER BY count DESC
                ''')
                stats['roms_per_system'] = {row['name']: row['count'] for row in self.cursor.fetchall()}

# Total Size of Rome
                self.cursor.execute("SELECT SUM(size) as total_size FROM roms WHERE size IS NOT NULL")
                stats['total_size_bytes'] = self.cursor.fetchone()['total_size']

# Favorite
                self.cursor.execute("SELECT COUNT(*) as count FROM roms WHERE favorite = 1")
                stats['favorites'] = self.cursor.fetchone()['count']

# Collections
                self.cursor.execute("SELECT COUNT(*) as count FROM collections")
                stats['collections'] = self.cursor.fetchone()['count']

# Rome in collections
                self.cursor.execute("SELECT COUNT(DISTINCT rom_id) as count FROM collection_roms")
                stats['roms_in_collections'] = self.cursor.fetchone()['count']

                return stats

            except sqlite3.Error as e:
                logger.error(f"Fehler beim Sammeln von Statistiken: {e}")
                return {}

    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """Creates a backup of the database. ARGS: Backup_Path: Optional Path for the Backup (If None, A Standard Path with Time Temple is used) Return: True in the Event of Success, False In The Event of Errors"""
        if not backup_path:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.backup-{timestamp}"

        try:
            self.conn.commit()  # Make sure all changes are saved
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Datenbank-Backup erstellt: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Datenbank-Backups: {e}")
            return False

    def _update_rom_cache(self, rom_id: int, name: str, system_id: int, file_path: Optional[str],
                         size: Optional[int], crc32: Optional[str], md5: Optional[str],
                         sha1: Optional[str], metadata: Optional[Dict[str, str]]):
        """
        Aktualisiert den ROM-Cache.

        Args:
            Alle relevanten ROM-Informationen
        """
        if not crc32 or not self.cache_enabled:
            return

# Call system name
        system_name = None
        if system_id in self._cache['systems']:
            system_name = self._cache['systems'][system_id].get('name')
        else:
            system = self.get_system_by_id(system_id)
            if system:
                system_name = system.get('name')

# Update cache
        self._cache['roms'][crc32] = {
            'id': rom_id,
            'name': name,
            'system_id': system_id,
            'system_name': system_name,
            'path': file_path,
            'size': size,
            'crc32': crc32,
            'md5': md5,
            'sha1': sha1,
            'metadata': metadata or {}
        }

    def commit(self):
        """Commit all pending changes."""
        with self._lock:
            try:
                self.conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Fehler beim Commit: {e}")
                raise

    def rollback(self):
        """Rollback all pending changes."""
        with self._lock:
            try:
                self.conn.rollback()
            except sqlite3.Error as e:
                logger.error(f"Fehler beim Rollback: {e}")
                raise

    def close(self):
        """Closes the database connection."""
        with self._lock:
            try:
                if self.conn:
                    self.conn.commit()
                    self.conn.close()
                    self.conn = None
                    self.cursor = None
                    logger.debug("Datenbankverbindung geschlossen")
            except sqlite3.Error as e:
                logger.error(f"Error closing database: {e}")

    def clear_cache(self):
        """Leert den Speicher-Cache."""
        with self._lock:
            self._cache = {
                'roms': {},
                'systems': {},
                'collections': {}
            }
            logger.debug("Speicher-Cache geleert")

    def __enter__(self):
        """Context Manager Einstieg."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Ausstieg."""
        if exc_type is not None:
            logger.error(f"Exception im ROMDatabase Context: {exc_type}, {exc_val}")
            self.rollback()
        else:
            self.commit()

        self.close()

# Main Function for Testing Purposes
def main():
    """Test function for the ROM database."""
    import argparse

# Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description='ROM Datenbank Test')
    parser.add_argument('--db', help='Pfad zur Datenbank', default=DEFAULT_DB_PATH)
    parser.add_argument('--stats', action='store_true', help='Datenbankstatistiken anzeigen')

    args = parser.parse_args()

    # Open database
    db = ROMDatabase(db_path=args.db)

    if args.stats:
# Show statistics
        stats = db.get_statistics()

        print("\nROM-Datenbank Statistiken:")
        print(f"Gesamtzahl der ROMs: {stats.get('total_roms', 0)}")

        total_size = stats.get('total_size_bytes', 0)
        if total_size:
# Convert to legible format
            if total_size < 1024:
                size_str = f"{total_size} Bytes"
            elif total_size < 1024 * 1024:
                size_str = f"{total_size/1024:.1f} KB"
            elif total_size < 1024 * 1024 * 1024:
                size_str = f"{total_size/(1024*1024):.1f} MB"
            else:
                size_str = f"{total_size/(1024*1024*1024):.1f} GB"

            print(f"Total size of ROMs: {size_str}")

        print(f"Favoriten: {stats.get('favorites', 0)}")
        print(f"Sammlungen: {stats.get('collections', 0)}")
        print(f"ROMs in Sammlungen: {stats.get('roms_in_collections', 0)}")

# Show ROMS Pro system
        roms_per_system = stats.get('roms_per_system', {})
        if roms_per_system:
            print("\nROMs pro System:")
            for system, count in sorted(roms_per_system.items(), key=lambda x: x[1], reverse=True):
                print(f"  {system}: {count}")

    else:
# Show all systems
        systems = db.get_all_systems()

        print(f"\nGefundene Systeme: {len(systems)}")
        for system in systems:
            print(f"  {system['name']}: {system['extensions']}")

# Close Database
    db.close()

if __name__ == "__main__":
    main()
