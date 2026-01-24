#!/usr/bin/env python3
# -*-coding: utf-8-*-

"""ROM SARTER PRO - Integration with external metadata services This module implemented integration with external ROM databases and Metadata services to collect comprehensive information about ROMs. Features: -Calling ROM metadata from various online sources - Local caching of metadata for offline use - Safe authentication with API key management - Extraction of cover images, screenshots and descriptions"""

import os
import re
import json
import logging
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from ..config.io import load_config
import threading

# Configure logger
logger = logging.getLogger(__name__)


def _network_enabled() -> bool:
    try:
        cfg = load_config()
        if isinstance(cfg, dict):
            return bool(cfg.get("metadata", {}).get("network_enabled", False))
    except Exception:
        pass
    return False


def _get_requests():
    if not _network_enabled():
        logger.info("Metadata network access disabled by configuration.")
        return None
    try:
        import requests  # type: ignore
        return requests
    except Exception as e:
        logger.warning(f"requests not available for metadata network calls: {e}")
        return None

# Constant
_CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'config')
_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'metadata')
_API_CONFIG_FILE = os.path.join(_CONFIG_DIR, 'api_keys.json')
_METADATA_CACHE_FILE = os.path.join(_CACHE_DIR, 'metadata_cache.json')
_IMAGE_CACHE_DIR = os.path.join(_CACHE_DIR, 'images')
_CACHE_EXPIRY = 30  # Tage

def _ensure_cache_dirs() -> None:
    """Create metadata cache/config directories lazily."""
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    os.makedirs(_CACHE_DIR, exist_ok=True)
    os.makedirs(_IMAGE_CACHE_DIR, exist_ok=True)


class APIKeyManager:
    """Manages API-Key for external services."""

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        _ensure_cache_dirs()
        self._api_keys = {}
        self._load_api_keys()
        self._initialized = True

    def _load_api_keys(self):
        """Invites Api-Key from the configuration file."""
        try:
            if os.path.exists(_API_CONFIG_FILE):
                with open(_API_CONFIG_FILE, 'r') as f:
                    self._api_keys = json.load(f)
                logger.info("API-Schlüssel erfolgreich geladen")
            else:
# Create a sample configuration
                sample_config = {
                    "thegamesdb": {
                        "api_key": "YOUR_API_KEY_HERE",
                        "enabled": False
                    },
                    "mobygames": {
                        "api_key": "YOUR_API_KEY_HERE",
                        "enabled": False
                    },
                    "igdb": {
                        "client_id": "YOUR_CLIENT_ID",
                        "client_secret": "YOUR_CLIENT_SECRET",
                        "enabled": False
                    }
                }
                with open(_API_CONFIG_FILE, 'w') as f:
                    json.dump(sample_config, f, indent=2)
                logger.info(f"Beispiel-API-Konfiguration erstellt unter {_API_CONFIG_FILE}")
                self._api_keys = sample_config
        except Exception as e:
            logger.error(f"Fehler beim Laden der API-Schlüssel: {e}")
            self._api_keys = {}

    def get_api_key(self, service: str) -> Optional[Dict[str, Any]]:
        """Returns The Api Key Configuration for a Service. Args: Service: Name of the Service (e.G. 'Thegamesdb', 'Mobygames') Return: Api key configuration or none, if not available"""
        if service in self._api_keys and self._api_keys[service].get("enabled", False):
            return self._api_keys[service]
        return None

    def set_api_key(self, service: str, key_data: Dict[str, Any]) -> bool:
        """Set or update an API key. Args: Service: name of the service Key_Data: API key configuration Return: True in the event of success, false in the event of errors"""
        try:
            with self._lock:
                self._api_keys[service] = key_data

                with open(_API_CONFIG_FILE, 'w') as f:
                    json.dump(self._api_keys, f, indent=2)

                logger.info(f"API-Schlüssel für {service} aktualisiert")
                return True
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des API-Schlüssels für {service}: {e}")
            return False

    def is_service_configured(self, service: str) -> bool:
        """Check Whether a Service is configured and activated. ARGS: Service: Name of the Service Return: True When Configured and Activated, OtherWise False"""
        return service in self._api_keys and self._api_keys[service].get("enabled", False)


class MetadataCache:
    """Manage the caching of ROM metadata."""

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        _ensure_cache_dirs()
        self._cache = {}
        self._load_cache()
        self._initialized = True

    def _load_cache(self):
        """Loads the metadata cache from the file."""
        try:
            if os.path.exists(_METADATA_CACHE_FILE):
                with open(_METADATA_CACHE_FILE, 'r') as f:
                    self._cache = json.load(f)
                logger.info(f"Metadaten-Cache mit {len(self._cache)} Einträgen geladen")
            else:
                self._cache = {
                    "metadata": {},
                    "last_updated": datetime.now().isoformat()
                }
                self._save_cache()
        except Exception as e:
            logger.error(f"Fehler beim Laden des Metadaten-Cache: {e}")
            self._cache = {
                "metadata": {},
                "last_updated": datetime.now().isoformat()
            }

    def _save_cache(self):
        """Save the metadata cache in the file."""
        try:
            with self._lock:
                with open(_METADATA_CACHE_FILE, 'w') as f:
                    json.dump(self._cache, f, indent=2)
                logger.debug("Metadaten-Cache gespeichert")
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Metadaten-Cache: {e}")

    def get_metadata(self, rom_id: str) -> Optional[Dict[str, Any]]:
        """Gives back cached metadata for a rome. ARGS: ROM_ID: Clear Id of the Rome (Typical Aally a hash) Return: Metadata dictionary or none, if not in the cache or expired"""
        with self._lock:
            if rom_id in self._cache["metadata"]:
                entry = self._cache["metadata"][rom_id]

# Check whether the cache has expired
                cache_date = datetime.fromisoformat(entry.get("cached_at", "2000-01-01"))
                if datetime.now() - cache_date > timedelta(days=_CACHE_EXPIRY):
                    logger.debug(f"Cache für ROM {rom_id} abgelaufen")
                    return None

                return entry
            return None

    def add_metadata(self, rom_id: str, metadata: Dict[str, Any]) -> bool:
        """Add metadata to the cache. Args: ROM_ID: Clear ID of the Rome Metadata: Metadata dictionary Return: True in the event of success, false in the event of errors"""
        try:
            with self._lock:
# Add caching information
                metadata["cached_at"] = datetime.now().isoformat()

# Save in the cache
                self._cache["metadata"][rom_id] = metadata
                self._cache["last_updated"] = datetime.now().isoformat()

# Save the cache regularly
                if len(self._cache["metadata"]) % 10 == 0:  # Save after each 10.
                    self._save_cache()

                return True
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen von Metadaten zum Cache: {e}")
            return False

    def save_image(self, rom_id: str, image_url: str, image_type: str = "cover") -> Optional[str]:
        """Lades Down a picture and save it in the cache. ARGS: ROM_ID: Clear Id of the Rome Image_url: Url of the Picture Image_Type: Type of the image (Cover, Screenshot, Banner, etc.) Return: Path to the Saved Picture Or None in the event of errors"""
        try:
# Create a Directory for Rome
            rom_image_dir = os.path.join(_IMAGE_CACHE_DIR, rom_id)
            os.makedirs(rom_image_dir, exist_ok=True)

# Extract or generate the file name from URL
            image_filename = f"{image_type}_{os.path.basename(image_url)}"
            if '?' in image_filename:
                image_filename = image_filename.split('?')[0]
            if not image_filename or len(image_filename) < 5:
                image_filename = f"{image_type}_{hashlib.md5(image_url.encode()).hexdigest()}.jpg"

            image_path = os.path.join(rom_image_dir, image_filename)

# Check whether the picture already exists
            if os.path.exists(image_path):
                return image_path

# Download the picture
            req = _get_requests()
            if req is None:
                return None
            response = req.get(image_url, stream=True, timeout=10)
            if response.status_code == 200:
                with open(image_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.debug(f"Bild für ROM {rom_id} gespeichert: {image_path}")
                return image_path
            else:
                logger.warning(f"Fehler beim Herunterladen des Bildes: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Fehler beim Speichern des Bildes: {e}")
            return None

    def get_image_path(self, rom_id: str, image_type: str = "cover") -> Optional[str]:
        """Gives Back the Path to a Caight Picture. ARGS: ROM_ID: Clear Id of the Rome Image_Type: Type of the Picture Return: Path to the Picture Or None, if not Available"""
        rom_image_dir = os.path.join(_IMAGE_CACHE_DIR, rom_id)
        if not os.path.exists(rom_image_dir):
            return None

# Search for pictures of the specified type
        for filename in os.listdir(rom_image_dir):
            if filename.startswith(f"{image_type}_"):
                return os.path.join(rom_image_dir, filename)

        return None


class TheGamesDBAPI:
    """Integration with ThegamesDB API for ROM metadata."""

    def __init__(self):
        """Initializes the Thegamesdb API integration."""
        self.api_manager = APIKeyManager()
        self.cache = MetadataCache()
        self.api_config = self.api_manager.get_api_key("thegamesdb")
        self.base_url = "https://api.thegamesdb.net/v1"

# Console mapping for ThegamesDB
        self.console_mapping = {
            "Nintendo Entertainment System": 7,
            "Super Nintendo": 6,
            "Nintendo 64": 3,
            "GameBoy": 4,
            "GameBoy Color": 41,
            "GameBoy Advance": 5,
            "Nintendo DS": 8,
            "PlayStation": 10,
            "PlayStation 2": 11,
            "Sega Genesis": 18,
            "Sega Saturn": 17,
            "Sega CD": 20,
            "Sega 32X": 33,
            "Sega Master System": 36
        }

    def is_available(self) -> bool:
        """Check whether the API is available."""
        return self.api_config is not None and "api_key" in self.api_config

    def search_game(self, name: str, platform_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Looking for a Game in the Thegamesdb. ARGS: Name: Name of the Game Platform_ID: ID of the Platform (optional) Return: List of Search Results"""
        if not self.is_available():
            logger.warning("TheGamesDB API ist nicht konfiguriert")
            return []

        try:
# Create the parameters for the API request
            params = {
                "apikey": self.api_config["api_key"],
                "name": name,
                "fields": "game_title,release_date,developers,publishers,overview",
                "include": "boxart,platform"
            }

            if platform_id:
                params["platform"] = platform_id

# Send the request
            req = _get_requests()
            if req is None:
                return None
            response = req.get(f"{self.base_url}/Games/ByGameName", params=params)
            if response.status_code == 200:
                data = response.json()

# Process the data
                if "data" in data and "games" in data["data"]:
                    return data["data"]["games"]
                else:
                    logger.debug(f"Keine Spiele für '{name}' gefunden")
                    return []
            else:
                logger.warning(f"TheGamesDB API-Fehler: HTTP {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Fehler bei der TheGamesDB-Suche: {e}")
            return []

    def get_game_metadata(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Calls detailed metadata for a game. Args: Game_ID: ID of the Game in Thegamesdb Return: Metadata Dictionary or None in the event of errors"""
        if not self.is_available():
            logger.warning("TheGamesDB API ist nicht konfiguriert")
            return None

        try:
# Create the parameters for the API request
            params = {
                "apikey": self.api_config["api_key"],
                "id": game_id,
                "fields": "game_title,overview,release_date,developers,publishers,genres,players",
                "include": "boxart,platform"
            }

# Send the request
            req = _get_requests()
            if req is None:
                return None
            response = req.get(f"{self.base_url}/Games/ByGameID", params=params)
            if response.status_code == 200:
                data = response.json()

# Process the data
                if "data" in data and "games" in data["data"] and len(data["data"]["games"]) > 0:
                    game_data = data["data"]["games"][0]

# Create a Structured Metadata Dictionary
                    metadata = {
                        "title": game_data.get("game_title", ""),
                        "overview": game_data.get("overview", ""),
                        "release_date": game_data.get("release_date", ""),
                        "developers": game_data.get("developers", []),
                        "publishers": game_data.get("publishers", []),
                        "genres": game_data.get("genres", []),
                        "players": game_data.get("players", ""),
                        "platform": game_data.get("platform", ""),
                        "images": {},
                        "source": "thegamesdb",
                        "source_id": str(game_id)
                    }

# Processed pictures
                    if "boxart" in data.get("include", {}):
                        for image_type, images in data["include"]["boxart"].items():
                            for image in images:
                                if image["id"] == game_id:
                                    image_url = image["filename"]
                                    metadata["images"][image["side"]] = image_url

                    return metadata
                else:
                    logger.debug(f"Keine Metadaten für Spiel-ID {game_id} gefunden")
                    return None
            else:
                logger.warning(f"TheGamesDB API-Fehler: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Fehler beim Abrufen der TheGamesDB-Metadaten: {e}")
            return None


class MobyGamesAPI:
    """Integration with MobyGames API for extensive game metadata."""

    def __init__(self):
        """Initialized the Mobygames API integration."""
        self.api_manager = APIKeyManager()
        self.cache = MetadataCache()
        self.api_config = self.api_manager.get_api_key("mobygames")
        self.base_url = "https://api.mobygames.com/v1"

# Console mapping for Mobygames
        self.console_mapping = {
            "Nintendo Entertainment System": "nes",
            "Super Nintendo": "snes",
            "Nintendo 64": "n64",
            "GameBoy": "gameboy",
            "GameBoy Color": "gbc",
            "GameBoy Advance": "gba",
            "Nintendo DS": "ds",
            "PlayStation": "psx",
            "PlayStation 2": "ps2",
            "Sega Genesis": "genesis",
            "Sega Saturn": "saturn",
            "Sega CD": "segacd",
            "Sega 32X": "sega32x",
            "Sega Master System": "sms"
        }

    def is_available(self) -> bool:
        """Check whether the API is available."""
        return self.api_config is not None and "api_key" in self.api_config

    def search_game(self, name: str, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """Looking for a Game in Mobygames. ARGS: Name: Name of the Game Platform: Platform ID (optional) Return: List of Search Results"""
        if not self.is_available():
            logger.warning("MobyGames API ist nicht konfiguriert")
            return []

        try:
# Create the parameters for the API request
            params = {
                "api_key": self.api_config["api_key"],
                "title": name,
                "format": "normal"
            }

            if platform:
                params["platform"] = platform

# Send the request
            req = _get_requests()
            if req is None:
                return None
            response = req.get(f"{self.base_url}/games", params=params)
            if response.status_code == 200:
                data = response.json()

# Process the data
                if "games" in data:
                    return data["games"]
                else:
                    logger.debug(f"Keine Spiele für '{name}' gefunden")
                    return []
            else:
                logger.warning(f"MobyGames API-Fehler: HTTP {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Fehler bei der MobyGames-Suche: {e}")
            return []

    def get_game_metadata(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Calls detailed metadata for a game. Args: Game_ID: Id of the Game in Mobygames Return: Metadata Dictionary Or None in the event of errors"""
        if not self.is_available():
            logger.warning("MobyGames API ist nicht konfiguriert")
            return None

        try:
# Create the parameters for the API request
            params = {
                "api_key": self.api_config["api_key"],
                "format": "normal"
            }

# Send the request
            req = _get_requests()
            if req is None:
                return None
            response = req.get(f"{self.base_url}/games/{game_id}", params=params)
            if response.status_code == 200:
                game_data = response.json()

# Create a Structured Metadata Dictionary
                metadata = {
                    "title": game_data.get("title", ""),
                    "description": game_data.get("description", ""),
                    "genres": [genre["genre_name"] for genre in game_data.get("genres", [])],
                    "platforms": [platform["platform_name"] for platform in game_data.get("platforms", [])],
                    "release_date": "",  # Is extracted from the release request
                    "developers": [],    # Is extracted from the credits
                    "publishers": [],    # Is extracted from the release request
                    "images": {},
                    "source": "mobygames",
                    "source_id": str(game_id)
                }

# Call screenshots from
                req = _get_requests()
                if req is None:
                    return None
                screenshots_response = req.get(
                    f"{self.base_url}/games/{game_id}/screenshots",
                    params=params
                )

                if screenshots_response.status_code == 200:
                    screenshots_data = screenshots_response.json()
                    if "screenshots" in screenshots_data and screenshots_data["screenshots"]:
                        metadata["images"]["screenshots"] = [
                            screenshot["image_url"]
                            for screenshot in screenshots_data["screenshots"][:5]  # Begrenzen auf 5 Screenshots
                        ]

# Cover cover pictures
                req = _get_requests()
                if req is None:
                    return None
                covers_response = req.get(
                    f"{self.base_url}/games/{game_id}/covers",
                    params=params
                )

                if covers_response.status_code == 200:
                    covers_data = covers_response.json()
                    if "covers" in covers_data and covers_data["covers"]:
                        for cover in covers_data["covers"]:
                            cover_type = cover.get("scan_of", "").lower()
                            if cover_type in ["front cover", "front"]:
                                metadata["images"]["front"] = cover["image_url"]
                            elif cover_type in ["back cover", "back"]:
                                metadata["images"]["back"] = cover["image_url"]

# Call release information from (for publishers and release date)
                req = _get_requests()
                if req is None:
                    return None
                releases_response = req.get(
                    f"{self.base_url}/games/{game_id}/releases",
                    params=params
                )

                if releases_response.status_code == 200:
                    releases_data = releases_response.json()
                    if "releases" in releases_data and releases_data["releases"]:
                        first_release = releases_data["releases"][0]
                        metadata["release_date"] = first_release.get("date", "")

                        if "companies" in first_release:
                            for company in first_release["companies"]:
                                if company.get("role", "") == "Published by":
                                    metadata["publishers"].append(company["company_name"])

# Call credits from (for developers)
                req = _get_requests()
                if req is None:
                    return None
                credits_response = req.get(
                    f"{self.base_url}/games/{game_id}/credits",
                    params=params
                )

                if credits_response.status_code == 200:
                    credits_data = credits_response.json()
                    if "credits" in credits_data:
# Extract developer companies
                        developers = set()
                        for credit in credits_data["credits"]:
                            if credit.get("role_category", "") == "Development":
                                for developer in credit.get("companies", []):
                                    developers.add(developer)

                        metadata["developers"] = list(developers)

                return metadata
            else:
                logger.warning(f"MobyGames API-Fehler: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Fehler beim Abrufen der MobyGames-Metadaten: {e}")
            return None


class MetadataManager:
    """Central class for managing and querying ROM metadata from various sources."""

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialized the metadata manager with all available sources."""
        if self._initialized:
            return

        self.cache = MetadataCache()
        self.api_manager = APIKeyManager()

# Initialize the API clients
        self.tgdb_api = TheGamesDBAPI()
        self.mobygames_api = MobyGamesAPI()

        self._initialized = True

    def get_metadata_for_rom(self, rom_name: str, console: str,
                           rom_content: Optional[bytes] = None) -> Optional[Dict[str, Any]]:
        """Calls Metadata for a rome, with local caching. ARGS: ROM_NAME: Name of the Rome File Console: Name of the Console Platform Rom_Content: Optional Rome Content for Hash Calculation Return: Metadata Dictionary Or None In The Event"""
# Generates A Clear ID for Rome
        if rom_content:
            rom_id = hashlib.md5(rom_content[:4096]).hexdigest()
        else:
            rom_id = hashlib.md5(f"{rom_name}_{console}".encode()).hexdigest()

# Attempts to load caught metadata
        cached_metadata = self.cache.get_metadata(rom_id)
        if cached_metadata:
            logger.info(f"Gecachte Metadaten für '{rom_name}' gefunden")
            return cached_metadata

# Adjust the Rome name for the search
        search_name = self._clean_rom_name(rom_name)
        logger.debug(f"Suche nach Metadaten für '{search_name}' ({console})")

# Attempts to get metadata from different sources
        metadata = None

# 1. Attempts Thegamesdb
        if self.tgdb_api.is_available():
            platform_id = self.tgdb_api.console_mapping.get(console)
            if platform_id:
                search_results = self.tgdb_api.search_game(search_name, platform_id)
                if search_results:
                    game_id = search_results[0]["id"]
                    metadata = self.tgdb_api.get_game_metadata(game_id)

# 2. Try MobyGames if Thegamesdb does not provide any results
        if not metadata and self.mobygames_api.is_available():
            platform = self.mobygames_api.console_mapping.get(console)
            if platform:
                search_results = self.mobygames_api.search_game(search_name, platform)
                if search_results:
                    game_id = search_results[0]["game_id"]
                    metadata = self.mobygames_api.get_game_metadata(game_id)

# When metadata has been found, save it in the cache
        if metadata:
            logger.info(f"Metadaten für '{rom_name}' gefunden")
            self.cache.add_metadata(rom_id, metadata)

# Charge and save pictures in the cache
            if "images" in metadata:
                for image_type, image_url in metadata["images"].items():
                    if isinstance(image_url, str):
                        self.cache.save_image(rom_id, image_url, image_type)
                    elif isinstance(image_url, list):
                        for i, url in enumerate(image_url):
                            self.cache.save_image(rom_id, url, f"{image_type}_{i}")

            return metadata
        else:
            logger.info(f"Keine Metadaten für '{rom_name}' gefunden")
            return None

    def _clean_rom_name(self, rom_name: str) -> str:
        """Adjusted a Rom name for the search. ARGS: ROM_NAME: Original Rome Name Return: Adjusted Name for the Search"""
# Remove the extension of the file
        name = os.path.splitext(rom_name)[0]

# Remove frequent ROM names and brackets
        patterns = [
            r'\([^\)]*\)',  # Text in Klammern
            r'\[[^\]]*\]',  # Text in eckigen Klammern
            r'[Rr][Ee][Vv][\s\._-]*[0-9]+',  # REV/Revision with number
            r'[Vv][0-9\.]+',  # Versionsnummer
            r'[\._-]*(EUR|USA|JPN|JAP|NTSC|PAL|[Uu]nleashed|ROM|[Cc]lean)',  # Regions and tags
            r'[\._-]*([Hh]ack|[Bb]eta|[Dd]emo|[Pp]rototype|[Ff]inal)',  # Statusbezeichnungen
        ]

        for pattern in patterns:
            name = re.sub(pattern, '', name)

# Replace special characters and multiple spaces
        name = re.sub(r'[\._-]+', ' ', name)
        name = re.sub(r'\s+', ' ', name)

        return name.strip()


def get_metadata_manager() -> MetadataManager:
    """Gives back an instance of the metadada manager. Return: An instance of the metadadamanager"""
    return MetadataManager()


def get_rom_metadata(rom_name: str, console: str, rom_content: Optional[bytes] = None) -> Optional[Dict[str, Any]]:
    """High level function for retrieving ROM metadata. Args: ROM_Name: Name of the Rome file Console: name of the console platform ROM_Content: Optional ROM content for hash calculation Return: Metadata dictionary or none in the event of errors"""
    manager = get_metadata_manager()
    return manager.get_metadata_for_rom(rom_name, console, rom_content)


def get_rom_image(rom_name: str, console: str, image_type: str = "front",
                rom_content: Optional[bytes] = None) -> Optional[str]:
    """Gives Back the Path to a Crashed Rome Picture. ARGS: ROM_NAME: Name of the Rome File Console: Name of the Console Platform Image_Type: Type of image (Front, Back, Screenshot, etc.) Rom_Content: Optional Rom Content for Hash Calculation Return: Path to the Picture Or None, if not Available"""
    cache = MetadataCache()

# Generates A Clear ID for Rome
    if rom_content:
        rom_id = hashlib.md5(rom_content[:4096]).hexdigest()
    else:
        rom_id = hashlib.md5(f"{rom_name}_{console}".encode()).hexdigest()

    return cache.get_image_path(rom_id, image_type)
