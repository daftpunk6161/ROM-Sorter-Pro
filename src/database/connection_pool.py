#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""Rome Sarter Pro - Database Connection Pool This modules Offers A Secure Connection Pool for Database Operations. It ensures that All Connections are Properly Closed."""

import os
import sqlite3
import threading
import time
import logging
from collections import deque
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from ..security.security_utils import sanitize_path
from .db_paths import get_rom_db_path

logger = logging.getLogger(__name__)

# Standard path to the Rome database
ROM_DATABASE_PATH = get_rom_db_path()

class DatabaseConnectionPool:
    """Safe and efficient database connection pool."""

    _instance = None
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls, db_path: str = ROM_DATABASE_PATH, max_connections: int = 10):
        """Gives back the singleton instance of the connecting pool."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = DatabaseConnectionPool(db_path, max_connections)
            return cls._instance

    def __init__(self, db_path: str, max_connections: int = 10):
        """Initialized the connecting pool with security validation."""
# Validate the database path
        self.db_path = str(sanitize_path(db_path))

        if max_connections <= 0 or max_connections > 50:
            raise ValueError("max_connections muss zwischen 1 und 50 liegen")

        self.max_connections = max_connections
        self._pool = deque()
        self._active_connections = 0

    def get_connection(self) -> sqlite3.Connection:
        """Get a Database Connection from the pool with security checks."""
        with self._lock:
            if self._pool:
                return self._pool.popleft()

            if self._active_connections < self.max_connections:
                conn = self._create_connection()
                self._active_connections += 1
                return conn

# WAIT A SHORT TIME AND TRY AGAIN
            time.sleep(0.01)
            if self._pool:
                return self._pool.popleft()

# Create A New Connection in an Emergency
            return self._create_connection()

    def return_connection(self, conn: sqlite3.Connection):
        """Gives Back a Connection to the pool."""
        with self._lock:
            try:
# Check whether the connection is still valid
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()

# If valid, add it to the pool or close it
                if len(self._pool) < self.max_connections:
                    self._pool.append(conn)
                else:
                    conn.close()
                    self._active_connections -= 1
            except (sqlite3.Error, sqlite3.ProgrammingError):
# In the event of errors: close the connection and reduce counter
                try:
                    conn.close()
                except:
                    pass  # Ignore mistakes when closing
                self._active_connections -= 1

    def _create_connection(self) -> sqlite3.Connection:
        """Creates a Secure and Optimized Database Connection."""
        try:
            conn = sqlite3.connect(
                self.db_path,
                isolation_level=None,  # AutoCommit mode for better performance
                check_same_thread=False,  # Allows thread cross-use use
                timeout=30.0
            )

# Set safe SQlite pragmas
            cursor = conn.cursor()
            secure_pragmas = [
                "PRAGMA journal_mode=WAL",
                "PRAGMA synchronous=NORMAL",
                "PRAGMA cache_size=10000",
                "PRAGMA temp_store=MEMORY",
                "PRAGMA mmap_size=268435456",  # 256MB
                "PRAGMA foreign_keys=ON",
                "PRAGMA secure_delete=ON",
                "PRAGMA trusted_schema=OFF"
            ]

            for pragma in secure_pragmas:
                cursor.execute(pragma)

            cursor.close()
            return conn

        except Exception as e:
            logger.error(f"Fehler beim Erstellen einer sicheren Datenbankverbindung: {e}")
            raise

    def close_all(self):
        """Closes all connections in the pool."""
        with self._lock:
            while self._pool:
                conn = self._pool.popleft()
                try:
                    conn.close()
                except:
                    pass  # Ignore mistakes when closing
            self._active_connections = 0


@contextmanager
def database_connection(db_path: str = ROM_DATABASE_PATH):
    """Context manager for secure database connections. Use: With database_connection () as Conn: Cursor = Conn.cursor () # Carry Out SQL Operations cursor.execute ("select * from table") The connection is automatically returned to the pool when the block is left."""
    pool = DatabaseConnectionPool.get_instance(db_path)
    conn = None
    try:
        conn = pool.get_connection()
        yield conn
    finally:
        if conn is not None:
            pool.return_connection(conn)
