"""ROM Database Update Script (compatibility shim).

Provides minimal DB setup/migration helpers used by MVP tests and controller.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from typing import Optional

logger = logging.getLogger(__name__)


def setup_database(db_path: str) -> sqlite3.Connection:
    """Setup the ROM database with initial structure."""
    logger.info("Setting up database at: %s", db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS roms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        filename TEXT NOT NULL,
        console TEXT NOT NULL,
        path TEXT NOT NULL,
        filesize INTEGER NOT NULL,
        size INTEGER,
        crc TEXT,
        md5 TEXT,
        sha1 TEXT,
        hash TEXT,
        metadata TEXT,
        source TEXT,
        confidence REAL DEFAULT 1.0,
        system_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    _ensure_rom_columns(cursor)

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS consoles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        folder TEXT NOT NULL,
        extensions TEXT NOT NULL,
        enabled INTEGER DEFAULT 1,
        detection_priority INTEGER DEFAULT 100
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS systems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        extensions TEXT NOT NULL,
        description TEXT,
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    _ensure_rom_columns(cursor)
    _ensure_system_id_column(cursor)
    _sync_systems_from_consoles(cursor)
    _backfill_system_ids(cursor)

    conn.commit()
    logger.info("Database structure setup complete")
    return conn


def update_rom_database(db_path: str) -> bool:
    """Update the ROM database structure to latest version."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT value FROM settings WHERE key='db_version'")
            version = cursor.fetchone()
            current_version = int(version[0]) if version else 0
        except (sqlite3.OperationalError, TypeError):
            current_version = 0

        latest_version = 3

        if current_version >= latest_version:
            logger.info("Database already at latest version %s", latest_version)
            conn.close()
            return True

        logger.info("Updating database from version %s to %s", current_version, latest_version)

        if current_version < 1:
            try:
                cursor.execute("ALTER TABLE roms ADD COLUMN verified INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

        if current_version < 2:
            try:
                cursor.execute("ALTER TABLE roms ADD COLUMN rating INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

        if current_version < 3:
            try:
                cursor.execute("ALTER TABLE consoles ADD COLUMN custom_path TEXT")
            except sqlite3.OperationalError:
                pass

        _ensure_rom_columns(cursor)
        _ensure_system_id_column(cursor)
        _sync_systems_from_consoles(cursor)
        _backfill_system_ids(cursor)

        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('db_version', ?)",
            (str(latest_version),),
        )

        conn.commit()
        conn.close()

        logger.info("Database updated to version %s", latest_version)
        return True

    except Exception as exc:
        logger.error("Database update failed: %s", exc)
        return False


def scan_directory(conn: sqlite3.Connection, directory: str, recursive: bool = True) -> int:
    """Scan a directory for ROM files and add them to the database."""
    logger.info("Scanning directory: %s, recursive: %s", directory, recursive)

    cursor = conn.cursor()
    count = 0

    cursor.execute("SELECT extensions FROM consoles")
    all_extensions: list[str] = []
    for row in cursor.fetchall():
        extensions = row[0].split(",")
        all_extensions.extend([ext.strip().lower() for ext in extensions])

    all_extensions = list(set(all_extensions))

    for root, _dirs, files in os.walk(directory):
        for filename in files:
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in all_extensions:
                full_path = os.path.join(root, filename)
                file_size = os.path.getsize(full_path)

                cursor.execute("SELECT name FROM consoles WHERE extensions LIKE ?", (f"%{file_ext}%",))
                console_row = cursor.fetchone()
                console = console_row[0] if console_row else "Unknown"

                system_id = None
                try:
                    cursor.execute("SELECT id FROM systems WHERE name = ?", (console,))
                    row = cursor.fetchone()
                    if row:
                        system_id = row[0]
                except sqlite3.Error:
                    system_id = None

                cursor.execute(
                    "INSERT INTO roms (name, filename, console, path, filesize, size, system_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (filename, filename, console, full_path, file_size, file_size, system_id),
                )
                count += 1

        if not recursive:
            break

    conn.commit()
    logger.info("Added %s ROMs to database", count)
    return count


def import_dat_file(conn: sqlite3.Connection, dat_file: str) -> int:
    """Import ROM metadata from a DAT file into the database."""
    import re
    import xml.etree.ElementTree as ET

    logger.info("Importing DAT file: %s", dat_file)

    try:
        cursor = conn.cursor()
        count = 0

        tree = ET.parse(dat_file)
        root = tree.getroot()

        header = root.find("header")
        if header is not None:
            name_elem = header.find("name")
            console_name = name_elem.text if name_elem is not None else "Unknown"
        else:
            console_name = os.path.splitext(os.path.basename(dat_file))[0]

        for game in root.findall(".//game"):
            name = game.get("name", "")

            for rom in game.findall("rom"):
                rom_name = rom.get("name", "")
                rom_size = rom.get("size", "0")
                rom_crc = rom.get("crc", "")

                cursor.execute(
                    "UPDATE roms SET metadata = json_set(COALESCE(metadata, '{}'), '$.original_name', ?, '$.crc', ?), crc = ? "
                    "WHERE filename LIKE ? OR filename = ?",
                    (name, rom_crc, rom_crc, f"%{rom_name}%", rom_name),
                )

                if cursor.rowcount > 0:
                    count += cursor.rowcount

        conn.commit()
        logger.info("Updated %s ROMs with metadata from DAT file", count)
        return count

    except Exception as exc:
        logger.error("Error importing DAT file: %s", exc)
        return 0


def _ensure_rom_columns(cursor: sqlite3.Cursor) -> None:
    columns = {
        "name": "TEXT",
        "size": "INTEGER",
        "crc": "TEXT",
        "md5": "TEXT",
        "sha1": "TEXT",
        "source": "TEXT",
        "confidence": "REAL DEFAULT 1.0",
    }
    for column, ddl in columns.items():
        try:
            cursor.execute(f"ALTER TABLE roms ADD COLUMN {column} {ddl}")
        except sqlite3.OperationalError:
            pass


def _ensure_system_id_column(cursor: sqlite3.Cursor) -> None:
    try:
        cursor.execute("ALTER TABLE roms ADD COLUMN system_id INTEGER")
    except sqlite3.OperationalError:
        pass


def _sync_systems_from_consoles(cursor: sqlite3.Cursor) -> None:
    try:
        cursor.execute("SELECT name, extensions FROM consoles")
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        return

    for name, extensions in rows:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO systems (name, extensions, description) VALUES (?, ?, ?)",
                (name, extensions, None),
            )
        except sqlite3.OperationalError:
            continue


def _backfill_system_ids(cursor: sqlite3.Cursor) -> None:
    try:
        cursor.execute(
            "UPDATE roms SET system_id = (SELECT id FROM systems WHERE systems.name = roms.console) "
            "WHERE system_id IS NULL AND console IS NOT NULL"
        )
    except sqlite3.OperationalError:
        pass
