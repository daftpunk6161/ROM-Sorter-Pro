"""
ROM Database Update Script
Compatibility wrapper for database operations to avoid import errors.
"""

import os
import sqlite3
import logging
from typing import Optional, Union

logger = logging.getLogger(__name__)

def setup_database(db_path: str) -> sqlite3.Connection:
    """
    Setup the ROM database with initial structure.

    Args:
        db_path (str): Path to the database file

    Returns:
        sqlite3.Connection: Open connection to the database
    """
    logger.info(f"Setting up database at: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create ROM table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS roms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        console TEXT NOT NULL,
        path TEXT NOT NULL,
        filesize INTEGER NOT NULL,
        hash TEXT,
        metadata TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create console table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS consoles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        folder TEXT NOT NULL,
        extensions TEXT NOT NULL,
        enabled INTEGER DEFAULT 1,
        detection_priority INTEGER DEFAULT 100
    )
    ''')

    # Create settings table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Commit the changes
    conn.commit()
    logger.info("Database structure setup complete")

    return conn

def update_rom_database(db_path: str) -> bool:
    """
    Update the ROM database structure to latest version.

    Args:
        db_path (str): Path to the database file

    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Check database version
        try:
            cursor.execute("SELECT value FROM settings WHERE key='db_version'")
            version = cursor.fetchone()
            current_version = int(version[0]) if version else 0
        except (sqlite3.OperationalError, TypeError):
            current_version = 0

        # Latest version
        latest_version = 3

        if current_version >= latest_version:
            logger.info(f"Database already at latest version {latest_version}")
            conn.close()
            return True

        logger.info(f"Updating database from version {current_version} to {latest_version}")

        # Apply migrations sequentially
        if current_version < 1:
            # Version 1 migration
            try:
                cursor.execute("ALTER TABLE roms ADD COLUMN verified INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Column might already exist

        if current_version < 2:
            # Version 2 migration
            try:
                cursor.execute("ALTER TABLE roms ADD COLUMN rating INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

        if current_version < 3:
            # Version 3 migration
            try:
                cursor.execute("ALTER TABLE consoles ADD COLUMN custom_path TEXT")
            except sqlite3.OperationalError:
                pass

        # Update the version
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('db_version', ?)",
            (str(latest_version),)
        )

        conn.commit()
        conn.close()

        logger.info(f"Database updated to version {latest_version}")
        return True

    except Exception as e:
        logger.error(f"Database update failed: {e}")
        return False


def scan_directory(conn: sqlite3.Connection, directory: str, recursive: bool = True) -> int:
    """
    Scan a directory for ROM files and add them to the database.

    Args:
        conn (sqlite3.Connection): Database connection
        directory (str): Directory path to scan
        recursive (bool): Whether to scan subdirectories recursively

    Returns:
        int: Number of ROMs added to database
    """
    import os
    from pathlib import Path

    logger.info(f"Scanning directory: {directory}, recursive: {recursive}")

    cursor = conn.cursor()
    count = 0

    # Get known extensions for ROMs
    cursor.execute("SELECT extensions FROM consoles")
    all_extensions = []
    for row in cursor.fetchall():
        extensions = row[0].split(',')
        all_extensions.extend([ext.strip().lower() for ext in extensions])

    # Remove duplicates
    all_extensions = list(set(all_extensions))

    # Walk through directory
    for root, dirs, files in os.walk(directory):
        for filename in files:
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in all_extensions:
                full_path = os.path.join(root, filename)
                file_size = os.path.getsize(full_path)

                # Determine console based on extension
                cursor.execute("SELECT name FROM consoles WHERE extensions LIKE ?", (f"%{file_ext}%",))
                console_row = cursor.fetchone()
                console = console_row[0] if console_row else "Unknown"

                # Add to database
                cursor.execute(
                    "INSERT INTO roms (filename, console, path, filesize) VALUES (?, ?, ?, ?)",
                    (filename, console, full_path, file_size)
                )
                count += 1

        if not recursive:
            break

    conn.commit()
    logger.info(f"Added {count} ROMs to database")
    return count


def import_dat_file(conn: sqlite3.Connection, dat_file: str) -> int:
    """
    Import ROM metadata from a DAT file into the database.

    Args:
        conn (sqlite3.Connection): Database connection
        dat_file (str): Path to the DAT file

    Returns:
        int: Number of ROMs updated in the database
    """
    import xml.etree.ElementTree as ET
    import re

    logger.info(f"Importing DAT file: {dat_file}")

    try:
        cursor = conn.cursor()
        count = 0

        # Parse the DAT file (XML format)
        tree = ET.parse(dat_file)
        root = tree.getroot()

        # Extract console name from DAT file
        header = root.find('header')
        if header is not None:
            console_name = header.find('name').text if header.find('name') is not None else "Unknown"
        else:
            console_name = os.path.splitext(os.path.basename(dat_file))[0]

        # Process each game/ROM entry
        for game in root.findall('.//game'):
            name = game.get('name', '')

            # Process ROMs within the game entry
            for rom in game.findall('rom'):
                rom_name = rom.get('name', '')
                rom_size = rom.get('size', '0')
                rom_crc = rom.get('crc', '')

                # Try to match with existing ROMs in database
                cursor.execute(
                    "UPDATE roms SET metadata = json_set(COALESCE(metadata, '{}'), '$.original_name', ?, '$.crc', ?) "
                    "WHERE filename LIKE ? OR filename = ?",
                    (name, rom_crc, f"%{rom_name}%", rom_name)
                )

                if cursor.rowcount > 0:
                    count += cursor.rowcount

        conn.commit()
        logger.info(f"Updated {count} ROMs with metadata from DAT file")
        return count

    except Exception as e:
        logger.error(f"Error importing DAT file: {e}")
        return 0
