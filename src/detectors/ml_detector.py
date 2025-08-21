#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""Rome Sarter Pro - Rule -Based Console Detection (ML Replacement) This version was optimized to function without external ml descendencies. It Offers a Robust Rule -Based Detection with the same api as the ML -Based version, so that existing code continues to work."""

import os
import re
import logging
import pickle
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set, Any, Union, Callable
from collections import Counter, defaultdict, deque
from functools import lru_cache

# Import basic modules
try:
    from .base_detector import BaseDetector
    from .detection_handler import DetectionResult
except ImportError:
# For direct execution
    BaseDetector = object
    class DetectionResult:
        def __init__(self, console="Unknown", confidence=0.0, method="unknown", file_path=""):
            self.console = console
            self.confidence = confidence
            self.method = method
            self.file_path = file_path

        def __str__(self):
            confidence_percent = int(self.confidence * 100)
            return f"{self.console} ({confidence_percent}%, {self.method})"

try:
    from security import validate_path, sanitize_input
except ImportError:
    def validate_path(path):
        return Path(path)
    def sanitize_input(text, max_length=255, allow_special=False):
        return text[:max_length] if isinstance(text, str) else ""

# Logger
logger = logging.getLogger(__name__)

# Constant
DEFAULT_MODEL_PATH = Path("models/enhanced_ml_detector")
DEFAULT_DATA_PATH = Path("data/ml_training")
HEADER_BYTES_TO_READ = 4096  # Wie viele Bytes vom Dateianfang gelesen werden
MAX_CACHE_SIZE = 10000  # Maximum number of elements in the cache
MIN_CONFIDENCE_THRESHOLD = 0.7  # Threshold for confidence
FEEDBACK_THRESHOLD = 20  # Anzahl neuer Feedbacks, bevor ein Modell-Update erfolgt

# File duties according to the console
FILE_EXTENSIONS = {
    ".nes": "NES",
    ".sfc": "SNES",
    ".smc": "SNES",
    ".n64": "Nintendo64",
    ".z64": "Nintendo64",
    ".v64": "Nintendo64",
    ".gb": "GameBoy",
    ".gbc": "GameBoy Color",
    ".gba": "GameBoy Advance",
    ".nds": "Nintendo DS",
    ".3ds": "Nintendo 3DS",
    ".md": "Genesis",
    ".smd": "Genesis",
    ".gen": "Genesis",
    ".sms": "MasterSystem",
    ".gg": "GameGear",
    ".32x": "Sega32X",
    ".pce": "PCEngine",
    ".cue": "SegaCD",
    ".iso": "Various",
    ".chd": "Various",
    ".zip": "Various",
    ".7z": "Various",
}

# Magic bytes for different Rome formats
MAGIC_BYTES = {
    b"NES\x1a": "NES",
    b"SEGA": "Genesis",
    b"EAGN": "Genesis",  # Manchmal verdreht
    b"\x89PNG": "Image",
    b"PK\x03\x04": "ZIP Archive",
    b"7z\xbc\xaf\x27\x1c": "7Z Archive",
    b"MComprHD": "CHD Archive",
    b"SNES-SPC700": "SNES Audio",
    b"BDR-SONY": "PlayStation",
}

# Global ML detector Cache
_ml_detector_instance = None

def get_ml_detector() -> 'MLEnhancedConsoleDetector':
    """Returns to Instance of the Mlenhanedconsoledetetector. Use a singleton pattern for efficient reuse. Return: Mlenhanconsoledetetector: to Instance of the Regular -Based Detector"""
    global _ml_detector_instance
    if _ml_detector_instance is None:
        _ml_detector_instance = MLEnhancedConsoleDetector()
# Charge existing patterns if available
        _ml_detector_instance.load_models()

    return _ml_detector_instance

def detect_console_with_ml(file_path: str) -> DetectionResult:
    """Carries Out Regular Console Detection for a Rome File. This function Serves as a Simple Interface for Console Detection and Hides the Complexity of the System. Args: File_Path: Path to the Rome File Return: Detection Result with Console and Confidence"""
    try:
# Validate the file path
        if not os.path.exists(file_path):
            return DetectionResult("Unknown", 0.0, method="detection_failed", file_path=file_path)

# Get the detector instance
        detector = get_ml_detector()

# Guide the detection
        console, confidence, metadata = detector.predict_console(file_path)

# Create a detailed result
        metadata = metadata or {}
        metadata.update({
            "type": "rule_based",
            "model_version": detector.model_version,
            "features_used": detector.last_features_used
        })

# Create A Result Object
        result = DetectionResult(console, confidence, method="rule_based", file_path=file_path)

# Provide debug info
        logger.debug(f"Konsolenerkennung für {file_path}: {result}")

        return result

    except Exception as e:
        logger.error(f"Erkennungsfehler für {file_path}: {str(e)}")
        return DetectionResult("Unknown", 0.0, method="error", file_path=file_path)


class MLEnhancedConsoleDetector(BaseDetector):
    """Regular -Based Console Detection with Extended Heuristic. This class implements a robust console Recognition Method, that Works Without External Dependencies, but the same api as the ml-based version offer."""

    def __init__(self):
        self.feature_extractor = DefaultFeatureExtractor()
        self.model_version = "1.0.0-rule-based"
        self.feedback_buffer = deque(maxlen=FEEDBACK_THRESHOLD * 2)
        self.result_cache = {}  # Cache for detection results
        self.last_features_used = []  # For debugging and transparency

# Model metrics
        self.metrics = {
            "total_predictions": 0,
            "correct_predictions": 0,
            "accuracy": 0.0,
            "last_training": None,
            "feedback_count": 0
        }

# Lade console pattern
        self.console_patterns = self._load_console_patterns()

    def _load_console_patterns(self) -> Dict[str, List[str]]:
        """Lades extended console recognition patterns. Return: Dict with console regex patterns"""
        patterns_file = DEFAULT_MODEL_PATH / "console_patterns.json"

        if patterns_file.exists():
            try:
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Fehler beim Laden der Konsolenmuster: {e}")

# Standard pattern
        return {
            'Nintendo Entertainment System': [
                r'\.nes$', r'nesrom', r'famicom', r'nintendo_entertainment_system',
                r'\.fc$', r'\.fds$', r'_nes[\._]'
            ],
            'Super Nintendo': [
                r'\.sfc$', r'\.smc$', r'snes', r'super_nintendo', r'super_famicom',
                r'\.fig$', r'_snes[\._]', r'_snc[\._]', r'_sfc[\._]', r'_superfamicom[\._]'
            ],
            'Nintendo 64': [
                r'\.n64$', r'\.z64$', r'\.v64$', r'nintendo64', r'n64rom',
                r'_n64[\._]', r'_nintendo64[\._]'
            ],
            'GameBoy': [
                r'\.gb$', r'^(?!.*advance).*gameboy', r'^(?!.*color).*gameboy',
                r'_gb[\._]', r'_gameboy[\._]', r'\.dmg$'
            ],
            'GameBoy Color': [
                r'\.gbc$', r'gameboy_color', r'gbcolor', r'_gbc[\._]'
            ],
            'GameBoy Advance': [
                r'\.gba$', r'gameboy_advance', r'gbarom', r'_gba[\._]', r'\.agb$'
            ],
            'Nintendo DS': [
                r'\.nds$', r'nintendo_ds', r'ndsrom', r'_nds[\._]', r'_ds[\._]'
            ],
            'Nintendo 3DS': [
                r'\.3ds$', r'nintendo_3ds', r'3dsrom', r'_3ds[\._]'
            ],
            'Sega Genesis': [
                r'\.md$', r'\.gen$', r'genesis', r'megadrive', r'mega_drive',
                r'_md[\._]', r'_genesis[\._]', r'_megadrive[\._]'
            ],
            'Sega Saturn': [
                r'\.ss$', r'\.sat$', r'sega_saturn', r'saturnrom',
                r'_saturn[\._]', r'_segasaturn[\._]', r'_sat[\._]'
            ],
            'Sega CD': [
                r'segacd', r'mega_cd', r'_segacd[\._]', r'_megacd[\._]'
            ],
            'PlayStation': [
                r'\.bin$', r'\.cue$', r'\.psf$', r'^(?!.*2)(?!.*3)(?!.*4).*playstation',
                r'^(?!.*2)(?!.*3)(?!.*4).*\.ps$', r'_psx[\._]', r'_psone[\._]',
                r'_ps1[\._]', r'_playstation[\._]'
            ],
            'PlayStation 2': [
                r'\.iso$', r'playstation2', r'playstation_2', r'ps2rom',
                r'_ps2[\._]', r'_playstation2[\._]'
            ]
        }

    def predict_console(self, file_path: str) -> Tuple[str, float, Dict[str, Any]]:
        """Carries out the rule -based console detection. Args: File_Path: path to the Rome file Return: Tuble consisting of (console name, confidence, metadata)"""
        file_path_obj = validate_path(file_path)

# Check the cache
        file_hash = self._get_file_hash(file_path_obj)
        if file_hash in self.result_cache:
            logger.debug(f"Cache-Treffer für {file_path_obj.name}")
            return self.result_cache[file_hash]

# Extract features
        features = self.feature_extractor.extract_features(file_path_obj)
        self.last_features_used = list(features.keys())

# Perform rule -based detection
        console, confidence, method = self._rule_based_detection(file_path_obj.name, features)

# Metadata for transparency
        metadata = {
            "method": method,
            "features_used": self.last_features_used,
            "detected_patterns": [],
        }

# Special pattern matches for transparency
        if method == "pattern_match":
            for pattern_name, match_value in features.items():
                if pattern_name.startswith('has_') and match_value:
                    metadata["detected_patterns"].append(pattern_name[4:])  # Entferne 'has_'

        result = (console, confidence, metadata)
        self.result_cache[file_hash] = result

# Update statistics
        self.metrics["total_predictions"] += 1

        return result

    def _rule_based_detection(self, filename: str, features: Dict[str, Any]) -> Tuple[str, float, str]:
        """Rule -based detection with several methods. Args: Filename: File name of the Rome file Features: Extracted features Return: Tuble from (console name, confidence, identification method)"""
# 1. Check Magic Bytes first (highest confidence)
        identified_format = features.get('identified_format')
        if identified_format and identified_format != "Various":
            return identified_format, 0.95, "magic_bytes"

# 2. Check header signatures for known formats
        if features.get('has_genesis_header'):
            return "Genesis", 0.95, "header_signature"
        if features.get('has_nes_header'):
            return "NES", 0.95, "header_signature"
        if features.get('has_snes_header'):
            return "SNES", 0.95, "header_signature"

# 3. Check the file extension
        extension = features.get('extension', '').lower()
        if extension in FILE_EXTENSIONS:
            console = FILE_EXTENSIONS[extension]
            if console != "Various":
                return console, 0.9, "file_extension"

# 4. Rule -based sample search with regular expressions
        filename_lower = filename.lower()
        best_match = None
        best_confidence = 0.0

        for console, patterns in self.console_patterns.items():
            matches = 0
            for pattern in patterns:
                if re.search(pattern, filename_lower, re.IGNORECASE):
                    matches += 1

            if matches > 0:
# Calculate confidence based on matches
                confidence = min(0.85, 0.6 + (matches / max(1, len(patterns))) * 0.25)

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = console

        if best_match:
            return best_match, best_confidence, "pattern_match"

# 5. Keyword -based detection in the file name
        console_keywords = {
            "NES": ["nes", "nintendo entertainment system", "famicom"],
            "SNES": ["snes", "super nintendo", "super famicom"],
            "Nintendo64": ["n64", "nintendo 64"],
            "GameBoy": ["gb", "game boy", "gameboy"],
            "GameBoy Color": ["gbc", "game boy color", "gameboy color"],
            "GameBoy Advance": ["gba", "game boy advance", "gameboy advance"],
            "Nintendo DS": ["nds", "nintendo ds", "ds rom"],
            "Genesis": ["genesis", "mega drive", "sega genesis"],
            "Saturn": ["saturn", "sega saturn"],
            "Dreamcast": ["dreamcast", "sega dreamcast"],
            "PlayStation": ["ps1", "psx", "playstation", "play station"],
            "PlayStation 2": ["ps2", "playstation 2", "play station 2"],
            "PCEngine": ["pc engine", "pc-engine", "turbografx"],
            "WonderSwan": ["wonderswan", "wonder swan"]
        }

        for console, keywords in console_keywords.items():
            for keyword in keywords:
                if keyword in filename_lower:
                    return console, 0.7, "keyword_match"

# 6. Size -based heuristics for certain consoles
        file_size_mb = features.get('file_size_mb', 0)
        if 0.01 <= file_size_mb <= 0.5:  # 10KB - 500KB
            return "GameBoy", 0.4, "size_heuristic"
        elif 0.5 < file_size_mb <= 3:    # 500KB - 3MB
            return "SNES", 0.3, "size_heuristic"
        elif 3 < file_size_mb <= 12:     # 3MB - 12MB
            return "Nintendo64", 0.3, "size_heuristic"
        elif file_size_mb > 500:         # > 500MB
            return "PlayStation 2", 0.3, "size_heuristic"

# When nothing was found
        return "Unknown", 0.0, "no_match"

    def load_models(self):
        """Loads the console patterns from the JSON file. This method is for API compatibility with the ML version."""
        model_path = Path(DEFAULT_MODEL_PATH)
        patterns_file = model_path / "console_patterns.json"

        if patterns_file.exists():
            try:
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    self.console_patterns = json.load(f)
                logger.info(f"Konsolenmuster aus {patterns_file} geladen")
            except Exception as e:
                logger.error(f"Fehler beim Laden der Konsolenmuster: {e}")

    def save_models(self):
        """Saves the Console Patterns in A Json File. This method is for api compatibility with the ml version."""
        model_path = Path(DEFAULT_MODEL_PATH)
        model_path.mkdir(parents=True, exist_ok=True)

        patterns_file = model_path / "console_patterns.json"
        try:
            with open(patterns_file, 'w', encoding='utf-8') as f:
                json.dump(self.console_patterns, f, indent=2)
            logger.info(f"Konsolenmuster in {patterns_file} gespeichert")
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Konsolenmuster: {e}")

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate a file hash for the cache. ONLY A Part is Read for Larger Files to Improve Performance."""
        try:
            file_size = file_path.stat().st_size
            if file_size > 1024 * 1024:  # For files> 1 MB
                with open(file_path, 'rb') as f:
# Read the first 64k and then jump to the middle and to the end
                    start_bytes = f.read(65536)
                    f.seek(file_size // 2)
                    middle_bytes = f.read(65536)
                    f.seek(max(0, file_size - 65536))
                    end_bytes = f.read(65536)

                hash_obj = hashlib.md5(start_bytes + middle_bytes + end_bytes)
            else:
                with open(file_path, 'rb') as f:
                    hash_obj = hashlib.md5(f.read())

            return hash_obj.hexdigest()
        except Exception as e:
            logger.warning(f"Fehler beim Berechnen des Datei-Hashs: {e}")
            return f"{file_path.name}_{file_path.stat().st_size}"


class DefaultFeatureExtractor:
    """Feature extractor for ROM files. This class is responsible for the extraction of features from Rome files."""

    def __init__(self):
        self.n_gram_range = (1, 3)  # Uni, bi- and trigrams
        self._keyword_patterns = self._compile_keyword_patterns()

    def _compile_keyword_patterns(self) -> Dict[str, re.Pattern]:
        """Compiled regex pattern for keywords."""
        return {
            'region': re.compile(r'\((USA|EUR|JPN|World|Europe|Japan|Germany|France|Italy|Spain|Australia|Korea)\)'),
            'version': re.compile(r'\b(v[0-9.]+|rev[0-9.]+|final|beta|alpha|demo|prototype|sample)\b', re.IGNORECASE),
            'console_marker': re.compile(r'\b(NES|SNES|N64|GBA|GBC|GB|Genesis|MD|SMS|PCE|DC|PS1|PS2)\b', re.IGNORECASE),
            'release_group': re.compile(r'\[(.*?)\]'),
            'rom_hack': re.compile(r'\b(hack|translation|enhanced|mod|fixed)\b', re.IGNORECASE)
        }

    def extract_features(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Extract all available features from a rome file. ARGS: File_Path: Path to the Rome File Return: Dict With Extracted Features"""
        file_path = validate_path(file_path)
        features = {}

# File name features
        features.update(self._extract_filename_features(file_path))

# Header features
        features.update(self._extract_header_features(file_path))

# Size features
        features.update(self._extract_size_features(file_path))

        return features

    def _extract_filename_features(self, file_path: Path) -> Dict[str, Any]:
        """Extract features from the file name."""
        filename = file_path.name
        stem = file_path.stem  # Name without expansion
        extension = file_path.suffix.lower()

        features = {
            'filename': stem,
            'extension': extension,
            'filename_length': len(stem),
            'has_brackets': '[' in filename and ']' in filename,
            'has_parentheses': '(' in filename and ')' in filename,
        }

# N-grams from the file name
        features['n_grams'] = self._extract_n_grams(stem.lower())

# Regex-based features
        for pattern_name, pattern in self._keyword_patterns.items():
            match = pattern.search(filename)
            features[f'has_{pattern_name}'] = bool(match)
            if match:
                features[f'{pattern_name}_value'] = match.group(0)

        return features

    def _extract_n_grams(self, text: str) -> List[str]:
        """Extracts n-grams from a text."""
        text = re.sub(r'[^\w\s]', ' ', text)  # Entferne Satzzeichen
        words = text.split()

        n_grams = []
        for n in range(self.n_gram_range[0], self.n_gram_range[1] + 1):
            for i in range(len(words) - n + 1):
                n_grams.append('_'.join(words[i:i+n]))

        return n_grams

    def _extract_header_features(self, file_path: Path) -> Dict[str, Any]:
        """Extract features from the file header."""
        features = {
            'header_signature': None,
            'identified_format': None,
            'magic_bytes_hex': None,
        }

        try:
            with open(file_path, 'rb') as f:
                header = f.read(HEADER_BYTES_TO_READ)

            if not header:
                return features

# Hex display of the Magic Bytes
            features['magic_bytes_hex'] = header[:8].hex()

# Search for well -known Magic bytes
            for magic, format_name in MAGIC_BYTES.items():
                if header.startswith(magic):
                    features['identified_format'] = format_name
                    features['header_signature'] = magic.hex()
                    break

# Special header detection for different formats
            if b'SEGA GENESIS' in header[:0x100] or b'SEGA MEGA DRIVE' in header[:0x100]:
                features['identified_format'] = 'Genesis'
                features['has_genesis_header'] = True

            if header[:4] == b'NES\x1a':
                features['identified_format'] = 'NES'
                features['prg_rom_size'] = header[4]
                features['chr_rom_size'] = header[5]
                features['has_nes_header'] = True

            if len(header) > 0x8000 and b'SUPER NINTENDO' in header[0x7FC0:0x8000]:
                features['identified_format'] = 'SNES'
                features['has_snes_header'] = True

        except (IOError, PermissionError) as e:
            logger.warning(f"Konnte Header für {file_path} nicht lesen: {e}")

        return features

    def _extract_size_features(self, file_path: Path) -> Dict[str, Any]:
        """Extract features based on the file size."""
        features = {}

        try:
            file_size = file_path.stat().st_size
            features['file_size'] = file_size
            features['file_size_kb'] = file_size / 1024
            features['file_size_mb'] = file_size / (1024 * 1024)

# Size rank for different consoles
            features['is_small'] = file_size < 1024 * 1024  # < 1 MB
            features['is_medium'] = 1024 * 1024 <= file_size < 10 * 1024 * 1024  # 1-10 MB
            features['is_large'] = file_size >= 10 * 1024 * 1024  # > 10 MB

        except (IOError, PermissionError) as e:
            logger.warning(f"Konnte Größe für {file_path} nicht bestimmen: {e}")

        return features


# Alias functions for compatibility with older API calls
def train_model(*args, **kwargs):
    """Dummy Function for API compatibility."""
    logger.info("ML-Training nicht verfügbar in der regelbasierten Version")
    return {"success": False, "reason": "ML-Training nicht verfügbar"}

def evaluate_model(*args, **kwargs):
    """Dummy Function for API compatibility."""
    logger.info("ML-Evaluation nicht verfügbar in der regelbasierten Version")
    return {"accuracy": 0.0, "model_type": "rule-based"}


# Fast cache function for repeated views
@lru_cache(maxsize=1000)
def cached_detect_console(file_path: str) -> Tuple[str, float]:
    """Cached version of console detection for better performance. Args: File_Path: path to the Rome file Return: Tuple with (console name, confidence)"""
    result = detect_console_with_ml(file_path)
    return result.console, result.confidence
