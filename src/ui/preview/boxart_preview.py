"""Screenshot/Boxart Preview - F67 Implementation.

Provides visual identification through screenshots and box art.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MediaAsset:
    """A media asset (screenshot, boxart, etc.)."""

    rom_hash: str
    asset_type: str  # screenshot, boxart, title, fanart
    url: str = ""
    local_path: str = ""
    width: int = 0
    height: int = 0
    source: str = ""  # screenscraper, launchbox, etc.


@dataclass
class RomMedia:
    """Media collection for a ROM."""

    rom_hash: str
    rom_name: str
    system: str
    boxart: Optional[MediaAsset] = None
    screenshot: Optional[MediaAsset] = None
    title_screen: Optional[MediaAsset] = None
    fanart: Optional[MediaAsset] = None


class BoxartPreview:
    """Screenshot and boxart preview system.

    Implements F67: Screenshot-/Boxart-Preview

    Features:
    - Local media cache
    - Multiple sources
    - Hash-based lookup
    - Lazy loading
    """

    CACHE_DIRNAME = "media_cache"
    INDEX_FILENAME = "media_index.json"

    # Supported image extensions
    IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".webp"]

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        media_dirs: Optional[List[str]] = None,
    ):
        """Initialize boxart preview.

        Args:
            cache_dir: Cache directory
            media_dirs: Additional media directories to scan
        """
        self._cache_dir = Path(cache_dir) if cache_dir else Path("cache")
        self._media_cache = self._cache_dir / self.CACHE_DIRNAME
        self._media_dirs = [Path(d) for d in (media_dirs or [])]
        self._index: Dict[str, RomMedia] = {}

        self._media_cache.mkdir(parents=True, exist_ok=True)
        self._load_index()

    def _load_index(self) -> None:
        """Load media index from file."""
        index_file = self._media_cache / self.INDEX_FILENAME

        if not index_file.exists():
            return

        try:
            with open(index_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for hash_key, media_data in data.items():
                rom_media = RomMedia(
                    rom_hash=media_data["rom_hash"],
                    rom_name=media_data["rom_name"],
                    system=media_data.get("system", ""),
                )

                for asset_type in ["boxart", "screenshot", "title_screen", "fanart"]:
                    if asset_type in media_data:
                        asset_data = media_data[asset_type]
                        asset = MediaAsset(
                            rom_hash=hash_key,
                            asset_type=asset_type,
                            url=asset_data.get("url", ""),
                            local_path=asset_data.get("local_path", ""),
                            width=asset_data.get("width", 0),
                            height=asset_data.get("height", 0),
                            source=asset_data.get("source", ""),
                        )
                        setattr(rom_media, asset_type, asset)

                self._index[hash_key] = rom_media

        except Exception:
            pass

    def _save_index(self) -> None:
        """Save media index to file."""
        index_file = self._media_cache / self.INDEX_FILENAME

        data = {}
        for hash_key, rom_media in self._index.items():
            media_data: Dict[str, Any] = {
                "rom_hash": rom_media.rom_hash,
                "rom_name": rom_media.rom_name,
                "system": rom_media.system,
            }

            for asset_type in ["boxart", "screenshot", "title_screen", "fanart"]:
                asset = getattr(rom_media, asset_type, None)
                if asset:
                    media_data[asset_type] = {
                        "url": asset.url,
                        "local_path": asset.local_path,
                        "width": asset.width,
                        "height": asset.height,
                        "source": asset.source,
                    }

            data[hash_key] = media_data

        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _find_local_media(
        self, rom_name: str, system: str
    ) -> Dict[str, Optional[str]]:
        """Find local media files.

        Args:
            rom_name: ROM name
            system: System name

        Returns:
            Dict of asset_type to local path
        """
        found: Dict[str, Optional[str]] = {
            "boxart": None,
            "screenshot": None,
            "title_screen": None,
            "fanart": None,
        }

        # Clean ROM name for matching
        clean_name = re.sub(r"\s*\([^)]*\)", "", rom_name)
        clean_name = re.sub(r"\s*\[[^\]]*\]", "", clean_name)
        clean_name = clean_name.strip()

        search_patterns = [
            clean_name,
            rom_name,
            clean_name.replace(" ", "_"),
            clean_name.replace(" ", "-"),
        ]

        # Search in media directories
        for media_dir in self._media_dirs:
            if not media_dir.exists():
                continue

            # Check system subdirectory
            system_dirs = [
                media_dir / system,
                media_dir / system.lower(),
                media_dir / system.replace(" ", "_"),
            ]

            for sys_dir in system_dirs:
                if not sys_dir.exists():
                    continue

                # Check asset type subdirectories
                asset_subdirs = {
                    "boxart": ["boxart", "box", "covers", "cover"],
                    "screenshot": ["screenshot", "screenshots", "snap", "snaps"],
                    "title_screen": ["title", "titles", "titlescreen"],
                    "fanart": ["fanart", "fan_art", "artwork"],
                }

                for asset_type, subdirs in asset_subdirs.items():
                    if found[asset_type]:
                        continue

                    for subdir in subdirs:
                        asset_dir = sys_dir / subdir
                        if not asset_dir.exists():
                            continue

                        # Search for matching files
                        for pattern in search_patterns:
                            for ext in self.IMAGE_EXTENSIONS:
                                candidates = [
                                    asset_dir / f"{pattern}{ext}",
                                    asset_dir / f"{pattern.lower()}{ext}",
                                ]

                                for candidate in candidates:
                                    if candidate.exists():
                                        found[asset_type] = str(candidate)
                                        break

                                if found[asset_type]:
                                    break

                            if found[asset_type]:
                                break

        return found

    def get_media(self, rom_hash: str) -> Optional[RomMedia]:
        """Get media for a ROM by hash.

        Args:
            rom_hash: ROM hash (SHA1, MD5, or CRC32)

        Returns:
            RomMedia or None
        """
        return self._index.get(rom_hash)

    def get_boxart_path(self, rom_hash: str) -> Optional[str]:
        """Get boxart path for a ROM.

        Args:
            rom_hash: ROM hash

        Returns:
            Path or None
        """
        media = self._index.get(rom_hash)
        if media and media.boxart and media.boxart.local_path:
            if Path(media.boxart.local_path).exists():
                return media.boxart.local_path
        return None

    def get_screenshot_path(self, rom_hash: str) -> Optional[str]:
        """Get screenshot path for a ROM.

        Args:
            rom_hash: ROM hash

        Returns:
            Path or None
        """
        media = self._index.get(rom_hash)
        if media and media.screenshot and media.screenshot.local_path:
            if Path(media.screenshot.local_path).exists():
                return media.screenshot.local_path
        return None

    def register_rom(
        self,
        rom_hash: str,
        rom_name: str,
        system: str,
        scan_local: bool = True,
    ) -> RomMedia:
        """Register a ROM for media lookup.

        Args:
            rom_hash: ROM hash
            rom_name: ROM name
            system: System name
            scan_local: Scan local directories

        Returns:
            RomMedia
        """
        if rom_hash in self._index:
            return self._index[rom_hash]

        rom_media = RomMedia(
            rom_hash=rom_hash,
            rom_name=rom_name,
            system=system,
        )

        # Scan local media
        if scan_local:
            local_media = self._find_local_media(rom_name, system)

            if local_media["boxart"]:
                rom_media.boxart = MediaAsset(
                    rom_hash=rom_hash,
                    asset_type="boxart",
                    local_path=local_media["boxart"],
                    source="local",
                )

            if local_media["screenshot"]:
                rom_media.screenshot = MediaAsset(
                    rom_hash=rom_hash,
                    asset_type="screenshot",
                    local_path=local_media["screenshot"],
                    source="local",
                )

            if local_media["title_screen"]:
                rom_media.title_screen = MediaAsset(
                    rom_hash=rom_hash,
                    asset_type="title_screen",
                    local_path=local_media["title_screen"],
                    source="local",
                )

            if local_media["fanart"]:
                rom_media.fanart = MediaAsset(
                    rom_hash=rom_hash,
                    asset_type="fanart",
                    local_path=local_media["fanart"],
                    source="local",
                )

        self._index[rom_hash] = rom_media
        self._save_index()

        return rom_media

    def set_media_path(
        self,
        rom_hash: str,
        asset_type: str,
        local_path: str,
        source: str = "manual",
    ) -> bool:
        """Set media path for a ROM.

        Args:
            rom_hash: ROM hash
            asset_type: Asset type
            local_path: Local file path
            source: Source identifier

        Returns:
            True if set
        """
        if rom_hash not in self._index:
            return False

        if not Path(local_path).exists():
            return False

        rom_media = self._index[rom_hash]
        asset = MediaAsset(
            rom_hash=rom_hash,
            asset_type=asset_type,
            local_path=local_path,
            source=source,
        )

        if asset_type == "boxart":
            rom_media.boxart = asset
        elif asset_type == "screenshot":
            rom_media.screenshot = asset
        elif asset_type == "title_screen":
            rom_media.title_screen = asset
        elif asset_type == "fanart":
            rom_media.fanart = asset
        else:
            return False

        self._save_index()
        return True

    def add_media_directory(self, path: str) -> bool:
        """Add a media directory to scan.

        Args:
            path: Directory path

        Returns:
            True if added
        """
        media_path = Path(path)
        if not media_path.exists():
            return False

        if media_path not in self._media_dirs:
            self._media_dirs.append(media_path)

        return True

    def scan_all_roms(
        self, roms: List[Dict[str, Any]]
    ) -> Dict[str, RomMedia]:
        """Scan media for multiple ROMs.

        Args:
            roms: List of ROM dicts with hash, name, system

        Returns:
            Dict of hash to RomMedia
        """
        result = {}

        for rom in roms:
            rom_hash = rom.get("hash") or rom.get("sha1") or rom.get("md5", "")
            rom_name = rom.get("name", "")
            system = rom.get("system", "")

            if rom_hash and rom_name:
                media = self.register_rom(rom_hash, rom_name, system)
                result[rom_hash] = media

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get media cache statistics.

        Returns:
            Stats dict
        """
        total = len(self._index)
        with_boxart = sum(1 for m in self._index.values() if m.boxart)
        with_screenshot = sum(1 for m in self._index.values() if m.screenshot)

        return {
            "total_roms": total,
            "with_boxart": with_boxart,
            "with_screenshot": with_screenshot,
            "boxart_percent": (with_boxart / total * 100) if total > 0 else 0,
            "screenshot_percent": (with_screenshot / total * 100) if total > 0 else 0,
            "media_directories": len(self._media_dirs),
        }

    def clear_cache(self) -> None:
        """Clear media cache."""
        self._index.clear()
        self._save_index()
