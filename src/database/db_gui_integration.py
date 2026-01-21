"""
ROM Sorter Pro - Database-GUI Integration v2.1.8

Additional database functions for the GUI class.
"""

import os
import platform
import sqlite3
import logging

from .db_paths import get_rom_db_path

# Configure logger
logger = logging.getLogger(__name__)

# Database schema definition (from update_rom_database.py)
DB_SCHEMA = """
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
);

CREATE INDEX IF NOT EXISTS idx_roms_md5 ON roms(md5);
CREATE INDEX IF NOT EXISTS idx_roms_crc ON roms(crc);
CREATE INDEX IF NOT EXISTS idx_roms_sha1 ON roms(sha1);
CREATE INDEX IF NOT EXISTS idx_roms_name ON roms(name);
CREATE INDEX IF NOT EXISTS idx_roms_console ON roms(console);
"""

def initialize_database(db_path):
    """Initializes the database and creates all the necessary tables. Args: db_path: path to the SQLite database Return: True in the event of success, false in the event of errors"""
    try:
# Make sure the database folder exists
        db_dir = os.path.dirname(db_path)
        logger.info(f"Erstelle Datenbankverzeichnis: {db_dir}")
        os.makedirs(db_dir, exist_ok=True)

# Provide writer
        if not os.access(db_dir, os.W_OK):
            logger.error(f"Keine Schreibberechtigungen für Verzeichnis: {db_dir}")
            return False

        logger.info(f"Initialisiere Datenbank: {db_path}")

# Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

# Perform the scheme
        logger.info("Führe Datenbankschema aus...")
        cursor.executescript(DB_SCHEMA)

# Check whether the tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        logger.info(f"Erstellte Tabellen: {tables}")

# Commit and close
        conn.commit()
        conn.close()

        logger.info(f"Datenbank erfolgreich initialisiert: {db_path}")
        return True
    except sqlite3.Error as e:
        logger.error(f"SQLite-Fehler bei der Datenbankinitialisierung: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Allgemeiner Fehler bei der Datenbankinitialisierung: {e}", exc_info=True)
        return False

def get_database_path():
    """Gives back the standard path to the database."""
    return get_rom_db_path()

def _display_database_status(self):
    """Displays the status of the Rome database in the Status Leisle."""
    try:
# Import the debug function
        from .db_debug import debug_database_initialization

# Check whether the database exists
        db_path = get_database_path()
        logger.info(f"Prüfe Datenbank unter Pfad: {db_path}")

# Carry out detailed examination
        debug_result = debug_database_initialization(db_path)

        if not os.path.exists(db_path):
            logger.info(f"Datenbank nicht gefunden unter: {db_path}")
# Try to initialize the database
            if initialize_database(db_path):
                logger.info(f"Datenbank erfolgreich initialisiert: {db_path}")
                self.status_bar.config(text="ROM-Datenbank wurde initialisiert. Bereit für Datenimport.")
            else:
                logger.error(f"Datenbank konnte nicht initialisiert werden: {db_path}")
                self.status_bar.config(text="ROM-Datenbank konnte nicht initialisiert werden.")
            return

# Connect to the database and show statistics
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM roms")
            rom_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT console) FROM roms")
            console_count = cursor.fetchone()[0]

            self.status_bar.config(
                text=f"ROM-Datenbank aktiv: {rom_count:,} ROMs für {console_count} Konsolen verfügbar"
            )
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
# The table does not exist, initialize the database
                logger.warning("Tabelle 'roms' nicht gefunden, initialisiere Datenbank...")
                conn.close()
                initialize_database(db_path)
                self.status_bar.config(text="ROM-Datenbank wurde initialisiert. Bereit für Datenimport.")
            else:
                logger.error(f"Datenbankfehler: {e}", exc_info=True)
                self.status_bar.config(text=f"Datenbankfehler: {e}")
        except Exception as e:
            logger.error(f"Unerwarteter Fehler: {e}", exc_info=True)
            self.status_bar.config(text=f"Fehler: {e}")
        finally:
            conn.close()

    except Exception as e:
        print(f"Fehler beim Abrufen des Datenbankstatus: {e}")
        self.status_bar.config(text="ROM Sorter Pro v2.1.4 - Memory Optimized")

def _show_database_manager(self):
    """Opens the dialogue to manage the ROM database."""
    try:
        from .database_gui import DatabaseManagerDialog
        dialog = DatabaseManagerDialog(self.root)

# Update status after closing the dialogue
        self.root.wait_window(dialog.dialog)
        self._display_database_status()

    except Exception as e:
        try:
            from tkinter import messagebox
            messagebox.showerror("Fehler", f"Fehler beim Öffnen des Datenbank-Managers: {e}")
        except Exception:
            logger.error("Fehler beim Öffnen des Datenbank-Managers: %s", e)

def _show_database_docs(self):
    """Displays the documentation to databases."""
    try:
        doc_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'docs', 'ERWEITERTE_ERKENNUNG.md')

        if os.path.exists(doc_path):
# Open the documentation file
            if platform.system() == 'Windows':
                os.startfile(doc_path)
            elif platform.system() == 'Darwin':  # macOS
                os.system(f'open "{doc_path}"')
            else:  # Linux and others
                os.system(f'xdg-open "{doc_path}"')
        else:
            try:
                from tkinter import messagebox
                messagebox.showinfo(
                    "Dokumentation",
                    "Die ROM-Datenbank ermöglicht eine präzise Erkennung durch Vergleich von "
                    "Hash-Werten mit bekannten ROMs aus No-Intro und Redump. "
                    "Verwenden Sie den Datenbank-Manager, um eigene ROMs zu scannen oder "
                    "DAT-Dateien zu importieren."
                )
            except Exception:
                logger.info("Dokumentation nicht verfügbar: %s", doc_path)
    except Exception as e:
        try:
            from tkinter import messagebox
            messagebox.showerror("Fehler", f"Fehler beim Öffnen der Dokumentation: {e}")
        except Exception:
            logger.error("Fehler beim Öffnen der Dokumentation: %s", e)

def _open_log_file(self):
    """Opens the current log file."""
    try:
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')

# Find the latest log file
        if os.path.exists(log_path):
            log_files = [f for f in os.listdir(log_path) if f.startswith('rom_sorter_')]
            if log_files:
                log_files.sort(reverse=True)  # Neueste zuerst
                latest_log = os.path.join(log_path, log_files[0])

# Open the log file
                if platform.system() == 'Windows':
                    os.startfile(latest_log)
                elif platform.system() == 'Darwin':  # macOS
                    os.system(f'open "{latest_log}"')
                else:  # Linux and others
                    os.system(f'xdg-open "{latest_log}"')
                return

        try:
            from tkinter import messagebox
            messagebox.showinfo("Info", "Keine Log-Datei gefunden.")
        except Exception:
            logger.info("Keine Log-Datei gefunden.")
    except Exception as e:
        try:
            from tkinter import messagebox
            messagebox.showerror("Fehler", f"Fehler beim Öffnen der Log-Datei: {e}")
        except Exception:
            logger.error("Fehler beim Öffnen der Log-Datei: %s", e)

# Add the functions to the GUI class
def add_database_methods_to_gui(cls):
    """Add the database methods to the GUI class."""
# Initialize the database at the start
    db_path = get_database_path()

# Diagnose and repair the database
    from .db_debug import debug_database_initialization
    debug_database_initialization(db_path)

    db_dir = os.path.dirname(db_path)

# Make sure the database directory exists
    if not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Datenbankverzeichnis erstellt: {db_dir}")
        except Exception as e:
            logger.error(f"Konnte Datenbankverzeichnis nicht erstellen: {e}", exc_info=True)

# Create the database if it does not exist
    if not os.path.exists(db_path):
        try:
            logger.info("Erstelle initiale Datenbank...")
            if initialize_database(db_path):
                logger.info(f"Datenbank erfolgreich erstellt: {db_path}")
            else:
                logger.error(f"Datenbank konnte nicht initialisiert werden: {db_path}")
        except Exception as e:
            logger.error(f"Konnte initiale Datenbank nicht erstellen: {e}", exc_info=True)

# Add the methods
    setattr(cls, '_display_database_status', _display_database_status)
    setattr(cls, '_show_database_manager', _show_database_manager)
    setattr(cls, '_show_database_docs', _show_database_docs)
    setattr(cls, '_open_log_file', _open_log_file)
    return cls
