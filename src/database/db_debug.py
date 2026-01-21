"""Debug functions for the Rome database."""

import os
import sqlite3
import logging

from .db_paths import get_rom_db_path

logger = logging.getLogger(__name__)

def debug_database_initialization(db_path):
    """Check the database and report its status."""

    logger.info(f"Überprüfe Datenbank: {db_path}")

# Check whether the file exists
    if not os.path.exists(db_path):
        logger.error(f"Datenbank-Datei existiert nicht: {db_path}")
        return False

# Check the permissions
    try:
        if not os.access(os.path.dirname(db_path), os.W_OK):
            logger.error(f"Keine Schreibberechtigung im Verzeichnis: {os.path.dirname(db_path)}")
            return False
    except Exception as e:
        logger.error(f"Fehler bei der Berechtigungsprüfung: {e}")

# Try to open the database and check tables
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

# List tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        logger.info(f"Vorhandene Tabellen: {tables}")

# Check whether ROMS exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='roms';")
        if cursor.fetchone():
            logger.info("Tabelle 'roms' existiert.")

# Check the columns
            cursor.execute("PRAGMA table_info(roms);")
            columns = cursor.fetchall()
            logger.info(f"Spalten in der Tabelle 'roms': {columns}")

# Check number of entries
            cursor.execute("SELECT COUNT(*) FROM roms;")
            count = cursor.fetchone()[0]
            logger.info(f"Anzahl der Einträge in 'roms': {count}")
        else:
            logger.error("Tabelle 'roms' existiert nicht!")

# Try to create the table
            try:
                cursor.execute('''
                CREATE TABLE roms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    console TEXT NOT NULL,
                    filename TEXT,
                    crc TEXT,
                    md5 TEXT,
                    sha1 TEXT,
                    size INTEGER,
                    metadata TEXT,
                    source TEXT,
                    confidence REAL DEFAULT 1.0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                ''')

# Create indices
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_roms_md5 ON roms(md5);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_roms_crc ON roms(crc);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_roms_sha1 ON roms(sha1);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_roms_name ON roms(name);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_roms_console ON roms(console);")

                conn.commit()
                logger.info("Tabelle 'roms' wurde erstellt.")
            except Exception as e:
                logger.error(f"Fehler beim Erstellen der Tabelle 'roms': {e}")

        conn.close()
        return True
    except Exception as e:
        logger.error(f"Datenbankfehler: {e}")
        return False

def get_db_connection(db_path=None):
    """Establish a connection to the database and create tables if necessary."""

    if db_path is None:
        # Use canonical path from config/db_paths
        db_path = get_rom_db_path()

# Make sure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    logger.info(f"Verbinde zur Datenbank: {db_path}")

    try:
# Make the SQLite connection
        conn = sqlite3.connect(db_path)

# Create tables
        cursor = conn.cursor()

# Create ROMS table, if not available
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS roms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            console TEXT NOT NULL,
            filename TEXT,
            crc TEXT,
            md5 TEXT,
            sha1 TEXT,
            size INTEGER,
            metadata TEXT,
            source TEXT,
            confidence REAL DEFAULT 1.0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')

# Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_roms_md5 ON roms(md5);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_roms_crc ON roms(crc);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_roms_sha1 ON roms(sha1);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_roms_name ON roms(name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_roms_console ON roms(console);")

        conn.commit()
        logger.info("Datenbankverbindung erfolgreich hergestellt und Tabellen überprüft.")
        return conn
    except Exception as e:
        logger.error(f"Fehler bei der Datenbankverbindung: {e}", exc_info=True)
        raise
