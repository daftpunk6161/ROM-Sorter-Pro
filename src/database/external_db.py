#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Externes Datenbankmanagement

Dieses Modul enthält Funktionen zur Verwaltung externer ROM-Datenbanken wie No-Intro,
TOSEC und Redump. Es bietet Funktionen zum Importieren, Aktualisieren und Abfragen
dieser Datenbanken.
"""

import os
import re
import xml.etree.ElementTree as ET
import threading
import sqlite3
import logging
import urllib.request
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from datetime import datetime

# Logger
logger = logging.getLogger(__name__)


class ExternalDatabaseManager:
    """Verwaltet externe ROM-Datenbanken (No-Intro, TOSEC, etc.)."""

    def __init__(self, db_path: str = "rom_databases"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(exist_ok=True)
        self.sqlite_db = self.db_path / "rom_database.sqlite"
        self._init_database()

# Database Urls for updates
        self.database_urls = {
            "no_intro": "https://datomatic.no-intro.org/index.php?page=download",
            "tosec": "https://www.tosecdev.org/downloads/category/37-datfiles",
            "redump": "http://redump.org/downloads/"
        }

        self._cached_lookups = {}
        self._cache_lock = threading.RLock()

    def _init_database(self):
        """Initialisiert SQLite-Datenbank für ROM-Lookups."""
        try:
            with sqlite3.connect(self.sqlite_db) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS rom_entries (
                        id INTEGER PRIMARY KEY,
                        filename TEXT NOT NULL,
                        console TEXT NOT NULL,
                        region TEXT,
                        language TEXT,
                        rom_size INTEGER,
                        crc32 TEXT,
                        md5 TEXT,
                        sha1 TEXT,
                        database_source TEXT NOT NULL,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_filename ON rom_entries (filename)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_console ON rom_entries (console)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_crc32 ON rom_entries (crc32)
                """)

                logger.info("Externe ROM-Datenbank initialisiert")
        except sqlite3.Error as e:
            logger.error(f"SQLite-Fehler beim Initialisieren der Datenbank: {e}")

    def import_dat_file(self, dat_file_path: Union[str, Path], database_source: str = "unknown") -> int:
        """
        Importiert eine DAT-Datei in die SQLite-Datenbank.

        Args:
            dat_file_path: Pfad zur DAT-Datei
            database_source: Quelle der Datenbank (no_intro, tosec, etc.)

        Returns:
            Anzahl der importierten Einträge
        """
        try:
            dat_path = Path(dat_file_path)
            if not dat_path.exists():
                logger.error(f"DAT-Datei existiert nicht: {dat_file_path}")
                return 0

            tree = ET.parse(dat_path)
            root = tree.getroot()

# Determine the format (no-intro, Tosec, etc.)
            if database_source == "unknown":
                if "tosec" in dat_path.name.lower():
                    database_source = "tosec"
                elif "no-intro" in dat_path.name.lower():
                    database_source = "no_intro"
                elif "redump" in dat_path.name.lower():
                    database_source = "redump"

# Attempts to determine the console name
            console_name = "Unknown"
            header = root.find("header")
            if header is not None:
                name = header.find("name")
                if name is not None and name.text:
                    console_match = re.search(r"\((.*?)\)", name.text)
                    if console_match:
                        console_name = console_match.group(1)

            count = 0
            with sqlite3.connect(self.sqlite_db) as conn:
                for game in root.findall(".//game"):
                    name = game.get("name", "")
                    if not name:
                        continue

                    rom_element = game.find("rom")
                    if rom_element is None:
                        continue

                    rom_data = {
                        "filename": name,
                        "console": console_name,
                        "region": self._extract_region(name),
                        "language": self._extract_language(name),
                        "rom_size": int(rom_element.get("size", "0")),
                        "crc32": rom_element.get("crc", ""),
                        "md5": rom_element.get("md5", ""),
                        "sha1": rom_element.get("sha1", ""),
                        "database_source": database_source
                    }

                    conn.execute("""
                        INSERT INTO rom_entries
                        (filename, console, region, language, rom_size, crc32, md5, sha1, database_source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rom_data["filename"],
                        rom_data["console"],
                        rom_data["region"],
                        rom_data["language"],
                        rom_data["rom_size"],
                        rom_data["crc32"],
                        rom_data["md5"],
                        rom_data["sha1"],
                        rom_data["database_source"]
                    ))
                    count += 1

            logger.info(f"{count} ROM-Einträge aus {dat_file_path} importiert")
            return count

        except ET.ParseError as e:
            logger.error(f"XML-Parsing-Fehler beim Import von {dat_file_path}: {e}")
            return 0
        except sqlite3.Error as e:
            logger.error(f"SQLite-Fehler beim Import von {dat_file_path}: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim Import von {dat_file_path}: {e}")
            return 0

    def lookup_rom_by_name(self, rom_name: str) -> Optional[Dict[str, Any]]:
        """
        Sucht einen ROM-Eintrag anhand des Namens.

        Args:
            rom_name: Name der ROM-Datei

        Returns:
            ROM-Eintrag als Dict oder None, wenn nicht gefunden
        """
        try:
            # Cache-Lookup
            cache_key = f"name:{rom_name}"
            with self._cache_lock:
                if cache_key in self._cached_lookups:
                    return self._cached_lookups[cache_key]

            with sqlite3.connect(self.sqlite_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM rom_entries
                    WHERE filename LIKE ?
                    ORDER BY last_updated DESC
                    LIMIT 1
                """, (f"%{rom_name}%",))

                result = cursor.fetchone()
                if result:
# Convert to dict
                    rom_data = {key: result[key] for key in result.keys()}
# Save in the cache
                    with self._cache_lock:
                        self._cached_lookups[cache_key] = rom_data
                    return rom_data
                return None

        except sqlite3.Error as e:
            logger.error(f"SQLite-Fehler beim ROM-Lookup für '{rom_name}': {e}")
            return None

    def lookup_rom_by_hash(self, hash_value: str, hash_type: str = "crc32") -> Optional[Dict[str, Any]]:
        """
        Sucht einen ROM-Eintrag anhand eines Hashwerts.

        Args:
            hash_value: CRC32, MD5 oder SHA1-Hashwert
            hash_type: Art des Hashes ("crc32", "md5" oder "sha1")

        Returns:
            ROM-Eintrag als Dict oder None, wenn nicht gefunden
        """
        try:
# Validate hash type
            if hash_type not in ["crc32", "md5", "sha1"]:
                logger.error(f"Ungültiger Hash-Typ: {hash_type}")
                return None

            # Cache-Lookup
            cache_key = f"{hash_type}:{hash_value}"
            with self._cache_lock:
                if cache_key in self._cached_lookups:
                    return self._cached_lookups[cache_key]

            with sqlite3.connect(self.sqlite_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(f"""
                    SELECT * FROM rom_entries
                    WHERE {hash_type} = ?
                    LIMIT 1
                """, (hash_value,))

                result = cursor.fetchone()
                if result:
# Convert to dict
                    rom_data = {key: result[key] for key in result.keys()}
# Save in the cache
                    with self._cache_lock:
                        self._cached_lookups[cache_key] = rom_data
                    return rom_data
                return None

        except sqlite3.Error as e:
            logger.error(f"SQLite-Fehler beim Hash-Lookup für '{hash_value}': {e}")
            return None

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Gibt Statistiken über die ROM-Datenbank zurück.

        Returns:
            Dict mit Datenbankstatistiken
        """
        try:
            with sqlite3.connect(self.sqlite_db) as conn:
                cursor = conn.cursor()

# Total number of entries
                cursor.execute("SELECT COUNT(*) FROM rom_entries")
                total_entries = cursor.fetchone()[0]

# Entries per database source
                cursor.execute("""
                    SELECT database_source, COUNT(*) as count
                    FROM rom_entries
                    GROUP BY database_source
                """)
                sources = {row[0]: row[1] for row in cursor.fetchall()}

# Entries per console
                cursor.execute("""
                    SELECT console, COUNT(*) as count
                    FROM rom_entries
                    GROUP BY console
                """)
                consoles = {row[0]: row[1] for row in cursor.fetchall()}

# Last update
                cursor.execute("""
                    SELECT MAX(last_updated) FROM rom_entries
                """)
                last_updated = cursor.fetchone()[0]

                return {
                    "total_entries": total_entries,
                    "by_source": sources,
                    "by_console": consoles,
                    "last_updated": last_updated,
                    "database_file": str(self.sqlite_db),
                    "database_size_mb": os.path.getsize(self.sqlite_db) / (1024 * 1024) if os.path.exists(self.sqlite_db) else 0
                }

        except sqlite3.Error as e:
            logger.error(f"SQLite-Fehler beim Abrufen von Datenbankstatistiken: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim Abrufen von Datenbankstatistiken: {e}")
            return {"error": str(e)}

    def _extract_region(self, filename: str) -> Optional[str]:
        """
        Extrahiert die Region aus einem ROM-Namen.

        Args:
            filename: ROM-Dateiname

        Returns:
            Extrahierte Region oder None
        """
# Typical regions in brackets, e.g. "(USA)", "(Europe)"
        region_match = re.search(r"\((USA|Europe|Japan|World|Germany|France|Spain|Italy|Australia)\)", filename)
        if region_match:
            return region_match.group(1)
        return None

    def _extract_language(self, filename: str) -> Optional[str]:
        """
        Extrahiert die Sprache aus einem ROM-Namen.

        Args:
            filename: ROM-Dateiname

        Returns:
            Extrahierte Sprache oder None
        """
# Typical language codes in brackets, e.g. "(en, fr, de)", "yes)"
        lang_match = re.search(r"\(([A-Za-z]{2}(?:,[A-Za-z]{2})*)\)", filename)
        if lang_match:
            return lang_match.group(1)
        return None

    def clear_cache(self) -> None:
        """Leert den Cache der Datenbankabfragen."""
        with self._cache_lock:
            self._cached_lookups.clear()
            logger.debug("Datenbank-Cache geleert")

    def download_database_update(self, source: str) -> bool:
        """
        Lädt ein Datenbank-Update von der angegebenen Quelle herunter.

        Diese Funktion ist ein Platzhalter und müsste für jede spezifische Datenquelle
        implementiert werden, da die meisten ROM-Datenbanken keine direkten Download-Links anbieten.

        Args:
            source: Datenbank-Quelle ("no_intro", "tosec", "redump")

        Returns:
            True bei Erfolg, False bei Fehler
        """
# This function would have to be implemented for each specific data source
        logger.warning(f"Automatische Downloads für {source} sind nicht implementiert")
        return False
