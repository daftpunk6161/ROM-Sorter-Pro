"""Rome Sarter Pro - Central Detector Interface This File Provides A Central Interface for All Rome Detectors, to Offer a Consistent API for Console Detection. Features: - uniform api for all identification methods - automatic fallback mechanism - Performance optimization through caching - context -conscious detection - Specialized detectors for certain formats (CHD, archive) - database integration for maximum accuracy (no -intro & redump) use: from detectors import detect_console console, confidence = detect_console (file name, file_path)"""
# ruff: noqa: E402

import os
import sqlite3
from typing import Dict, Tuple, Optional, Any, Callable, Type
from functools import lru_cache
import logging

# Import Detection Methods from Specialized Module
from .console_detector import detect_console_fast
from ..core.file_utils import calculate_file_hash

# Alias for downward compatibility
calculate_md5_fast = calculate_file_hash

# Import Specialized Detectors
from .console_detector import detect_console_enhanced
from .archive_detector import detect_console_from_archive, is_archive_file
from .chd_detector import detect_console_from_chd, is_chd_file
from .detection_result import DetectionResult
ML_ENABLED = os.environ.get("ROM_SORTER_ENABLE_ML", "").strip() == "1"


class _MLEnhancedConsoleDetector:
    pass


def get_ml_detector() -> Optional[Any]:
    return None

if ML_ENABLED:
    try:
        from . import ml_detector as _ml_detector
        detect_console_with_ml = _ml_detector.detect_console_with_ml
        MLEnhancedConsoleDetector = _ml_detector.MLEnhancedConsoleDetector
        get_ml_detector = _ml_detector.get_ml_detector
        ML_AVAILABLE = True
    except Exception:
        ML_AVAILABLE = False

        def detect_console_with_ml(file_path: str) -> "DetectionResult":
            return DetectionResult(
                "Unknown",
                0.0,
                method="ml",
                file_path=file_path,
                metadata={"error": "ml_unavailable"},
            )

        MLEnhancedConsoleDetector = _MLEnhancedConsoleDetector
else:
    ML_AVAILABLE = False

    def detect_console_with_ml(file_path: str) -> "DetectionResult":
        return DetectionResult(
            "Unknown",
            0.0,
            method="ml",
            file_path=file_path,
            metadata={"error": "ml_disabled"},
        )

    MLEnhancedConsoleDetector = _MLEnhancedConsoleDetector

# Database connections
from ..database.connection_pool import ROM_DATABASE_PATH

# Configure logger
logger = logging.getLogger(__name__)

# Import database initialization
try:
    from ..database.db_gui_integration import initialize_database
except ImportError:
# Fallback implementation if DB_Gui_integration is not available
    def initialize_database(db_path):
        """Fallback initialization of the database."""
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
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
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_roms_md5 ON roms(md5)")
            conn.commit()
            conn.close()
            logger.info(f"Datenbank initialisiert: {db_path}")
            return True
        except Exception as e:
            logger.error(f"Fehler bei der Datenbankinitialisierung: {e}")
            return False

# Try to import the database module
try:
    from ..database.db_debug import debug_database_initialization
except ImportError:
    def debug_database_initialization(db_path):
        """Fallback for Debug-Function."""
        logger.debug(f"Überprüfe Datenbank: {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            logger.debug(f"Vorhandene Tabellen: {tables}")
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Fehler bei der Datenbankprüfung: {e}")
            return False

# Constant
CACHE_SIZE = 10000
HIGH_CONFIDENCE_THRESHOLD = 0.85
ACCEPTABLE_CONFIDENCE_THRESHOLD = 0.65
DATABASE_ENABLED = True  # Switch for database functionality

@lru_cache(maxsize=CACHE_SIZE)
def detect_console_by_database(file_path: str) -> Tuple[str, float]:
    """Recognits the Console of a Rome by Comparing the Rome Database. This function calculates the MD5-Hash of the File and Compares It The Entries in the Database. In the event of a hit, The Corresponding Console Returned with the Highest Confidence. ARGS: File_Path: Complete Path to the Rome File Return: Tube from (Console_Name, Confidence_Score)"""
    if not DATABASE_ENABLED or not file_path or not os.path.exists(file_path):
        return "Unknown", 0.0

    try:
# Check whether the database exists
        if not os.path.exists(ROM_DATABASE_PATH):
            logger.info("ROM-Datenbank nicht gefunden. Initialisiere neue Datenbank unter: %s", ROM_DATABASE_PATH)
            if not initialize_database(ROM_DATABASE_PATH):
                return "Unknown", 0.0

# For additional diagnosis
            from ..database.db_debug import debug_database_initialization
            debug_database_initialization(ROM_DATABASE_PATH)

# Calculate hash values for the file
        md5_hash = calculate_md5_fast(file_path)
        if not md5_hash:
            return "Unknown", 0.0

# Use the secure context manager for database connections
        from ..database.connection_pool import database_connection

        try:
            with database_connection(ROM_DATABASE_PATH) as conn:
                cursor = conn.cursor()
# Search for MD5-Hash
                cursor.execute("SELECT console, name, confidence FROM roms WHERE md5=?", (md5_hash,))
                result = cursor.fetchone()

                if result:
                    console, name, db_confidence = result
                    logger.info(f"ROM in Datenbank gefunden: {name} ({console})")
# Use the confidence stored in the database, but at least 0.95
                    return console, max(float(db_confidence), 0.95)

# If necessary, query additional hash types
# SHA1, CRC32 etc. (can be implemented here)

        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
# Table does not exist, initialize the database
                logger.warning("Tabelle 'roms' nicht gefunden, initialisiere Datenbank...")
                initialize_database(ROM_DATABASE_PATH)
# Try again after initialization
                try:
                    with database_connection(ROM_DATABASE_PATH) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT console, name, confidence FROM roms WHERE md5=?", (md5_hash,))
                        result = cursor.fetchone()

                        if result:
                            console, name, db_confidence = result
                            logger.info(f"ROM in Datenbank gefunden: {name} ({console})")
                            return console, max(float(db_confidence), 0.95)
                except Exception as retry_error:
                    logger.error(f"Fehler beim zweiten Versuch der Datenbankabfrage: {retry_error}")
            else:
                logger.error(f"Datenbankfehler: {e}")

        return "Unknown", 0.0

    except Exception as e:
        logger.warning(f"Fehler bei der Datenbank-Erkennung: {e}")
        return "Unknown", 0.0


# Constants for the detector configuration
HIGH_CONFIDENCE_THRESHOLD = 0.85
ACCEPTABLE_CONFIDENCE_THRESHOLD = 0.65
DATABASE_ENABLED = True
CACHE_SIZE = 1000


 


class DetectionManager:
    """Central Manager Class for the Administration and Coordination of All Detectors. Implements the singleton pattern to offer a global access point."""

    _instance = None

    @classmethod
    def get_instance(cls):
        """Gives back the singleton instance."""
        if cls._instance is None:
            cls._instance = DetectionManager()
        return cls._instance

    def __init__(self):
        """Initializes the detection manager with the standard detectors."""
# Cache for results
        self._cache = {}
        self._cache_size = CACHE_SIZE

# statistics
        self.stats: Dict[str, float] = {
            "total_detections": 0.0,
            "cache_hits": 0.0,
            "cache_misses": 0.0,
            "high_confidence": 0.0,
            "acceptable_confidence": 0.0,
            "low_confidence": 0.0,
            "unknown": 0.0,
            "archive_detections": 0.0,
            "chd_detections": 0.0,
            "standard_detections": 0.0,
        }

    def detect_console(self, filename: str, file_path: Optional[str] = None) -> Tuple[str, float]:
        """Recognize the Console for A File by Automatically Selecting The Right Detector. ARGS: Filename: Name of the Rome File File_Path: Optional Full File Path for Context Analysis Return: Tuble from (Console Name, Confidence Value)"""
        result = self.detect_console_with_metadata(filename, file_path)
        return result.console, result.confidence

    def detect_console_with_metadata(self, filename: str, file_path: Optional[str] = None) -> DetectionResult:
        """Recognize the Console for a File with Complete Metadata. ARGS: Filename: Name of the Rome File File_Path: Optional Full File Path for Context Analysis Return: Detection Result Object With Console, Confidence and Metadata"""
        try:
# Update statistics
            self.stats["total_detections"] += 1.0

# Check cache
            cache_key = f"{filename}|{file_path}"
            if cache_key in self._cache:
                self.stats["cache_hits"] += 1.0
                return self._cache[cache_key]
            self.stats["cache_misses"] += 1.0

# Recognize the file type
            file_path_str = str(file_path) if file_path else None

# Check on archive files
            if file_path_str and is_archive_file(file_path_str):
                self.stats["archive_detections"] += 1.0
                console, confidence = detect_console_from_archive(file_path_str)
                result = DetectionResult(console, confidence, metadata={"type": "archive"})

# Check on CHD files
            elif file_path_str and is_chd_file(file_path_str):
                self.stats["chd_detections"] += 1.0
                console, confidence = detect_console_from_chd(file_path_str)
                result = DetectionResult(console, confidence, metadata={"type": "chd"})

# Database-based recognition (maximum priority)
            elif DATABASE_ENABLED and file_path_str and os.path.exists(file_path_str):
                db_console, db_confidence = detect_console_by_database(file_path_str)
                if db_confidence > 0.9:  # Very high confidence in database hits
                    result = DetectionResult(db_console, db_confidence, method="database", file_path=(file_path_str or ""))
                else:
# Try AI-based detection (newly implemented)
                    self.stats["ml_detections"] = float(self.stats.get("ml_detections", 0.0)) + 1.0
                    ml_result = detect_console_with_ml(file_path_str)

# If the AI detection has high confidence, use it
                    if ml_result.confidence >= 0.8:
                        return ml_result

# Otherwise standard detection for normal ROM files
                    self.stats["standard_detections"] += 1.0
                    console, confidence = detect_console_enhanced(filename, file_path_str)

# Combine both results at medium confidence
                    if 0.5 <= ml_result.confidence < 0.8 and 0.5 <= confidence < 0.9:
# When the same console has been recognized, the confidence increases
                        if ml_result.console == console:
                            combined_confidence = min(0.95, ml_result.confidence + 0.1)
                            result = DetectionResult(
                                console, combined_confidence,
                                method="ml_enhanced_combined", file_path=(file_path_str or "")
                            )
                        elif ml_result.confidence > confidence:
                            result = ml_result
                        else:
                            result = DetectionResult(console, confidence, method="enhanced", file_path=(file_path_str or ""))
# If low confidence, also try standard detection
                    elif confidence < ACCEPTABLE_CONFIDENCE_THRESHOLD:
                        std_console, std_confidence = detect_console_fast(filename, file_path_str)
                        if std_confidence > confidence and std_confidence > ml_result.confidence:
                            result = DetectionResult(std_console, std_confidence, method="standard_fallback", file_path=(file_path_str or ""))
                        elif ml_result.confidence > confidence:
                            result = ml_result
                        else:
                            result = DetectionResult(console, confidence, method="enhanced", file_path=(file_path_str or ""))
                    else:
                        result = DetectionResult(console, confidence, method="enhanced", file_path=(file_path_str or ""))
            else:
# Try AI-based detection if the file exists
                if file_path_str and os.path.exists(file_path_str):
                    self.stats["ml_detections"] = float(self.stats.get("ml_detections", 0.0)) + 1.0
                    ml_result = detect_console_with_ml(file_path_str)

                    if ml_result.confidence >= 0.7:
                        return ml_result

# Standard Detection Without A Database
                self.stats["standard_detections"] += 1.0
                console, confidence = detect_console_enhanced(filename, file_path_str)
                result = DetectionResult(console, confidence, method="enhanced", file_path=(file_path_str or ""))

# Update confidence statistics
            if result.is_unknown:
                self.stats["unknown"] += 1.0
            elif result.is_confident:
                self.stats["high_confidence"] += 1.0
            elif result.is_acceptable:
                self.stats["acceptable_confidence"] += 1.0
            else:
                self.stats["low_confidence"] += 1.0

# Result cachen
            if len(self._cache) >= self._cache_size:
# Cache cleaning: Remove the oldest entry
                try:
                    self._cache.pop(next(iter(self._cache)))
                except (StopIteration, KeyError):
                    pass

            self._cache[cache_key] = result

            return result
        except Exception as e:
            logger.error(f"Fehler bei der Konsolenerkennung: {e}")
            return DetectionResult("Unknown", 0.0, metadata={"error": str(e)})

    def get_statistics(self) -> Dict[str, Any]:
        """Returns the current identification statistics."""
        stats = dict(self.stats)
        total = max(1, int(stats.get("total_detections", 0)))
        stats["cache_hit_rate"] = float(stats.get("cache_hits", 0)) / total
        return stats

    def clear_cache(self) -> None:
        """Leert den Ergebniscache."""
        self._cache.clear()
        logger.debug("Detektorcache geleert")


# Simple API function for downward compatibility
def detect_console(filename: str, file_path: Optional[str] = None) -> Tuple[str, float]:
    """Central function for console detection, which automatically selects the suitable detector. Args: Filename: Name of the Rome file File_Path: Optional full file path for context analysis Return: Tuble from (console name, confidence value)"""
    return DetectionManager.get_instance().detect_console(filename, file_path)


def detect_console_with_metadata(filename: str, file_path: Optional[str] = None) -> DetectionResult:
    """Central function for console detection returning full metadata."""
    return DetectionManager.get_instance().detect_console_with_metadata(filename, file_path)


def detect_rom_type(filename: str, file_path: Optional[str] = None) -> DetectionResult:
    """Backward compatible alias for full detection result."""
    return detect_console_with_metadata(filename, file_path)


def get_console_list() -> Dict[str, Dict[str, Any]]:
    """Provides A Comprehensive List of Supported Consoles with Metadata. Return: Dictionary with console Names and Associated Metadata"""
    try:
# First try to use the new console database
        from ..database.console_db import get_console_metadata_all
        return get_console_metadata_all()
    except ImportError:
# Fallback to the old console database
        try:
            from ..utils import ENHANCED_CONSOLE_DATABASE

# Convert the console database into a dictionary
            consoles: Dict[str, Dict[str, Any]] = {}
            for console_name, meta in ENHANCED_CONSOLE_DATABASE.items():
                if isinstance(meta, dict):
                    consoles[console_name] = {
                        'display_name': console_name,
                        'extensions': meta.get('extensions', []),
                        'manufacturer': meta.get('manufacturer', 'Unknown'),
                        'year': meta.get('release_year', meta.get('year', 'Unknown')),
                        'type': meta.get('console_type', 'Unknown')
                    }
                else:
                    consoles[console_name] = {
                        'display_name': console_name,
                        'extensions': meta.extensions if hasattr(meta, 'extensions') else [],
                        'manufacturer': meta.manufacturer if hasattr(meta, 'manufacturer') else 'Unknown',
                        'year': meta.release_year if hasattr(meta, 'release_year') else 'Unknown',
                        'type': meta.console_type if hasattr(meta, 'console_type') else 'Unknown'
                    }
            return consoles
        except Exception as e:
            logger.error(f"Fehler beim Laden der Konsolendatenbank: {e}")
            return {}
