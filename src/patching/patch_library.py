"""Patch Library Manager - F80 Implementation.

Manages patch files per ROM/system with metadata.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .patcher import PatchFormat, Patcher


@dataclass
class PatchMetadata:
    """Metadata for a patch file."""

    title: str = ""
    author: str = ""
    version: str = ""
    description: str = ""
    language: str = ""  # e.g., "English", "German"
    patch_type: str = ""  # "Translation", "Hack", "Bugfix", "Improvement"
    source_url: str = ""
    release_date: str = ""
    target_rom_name: str = ""
    target_rom_crc32: str = ""
    target_rom_sha1: str = ""
    notes: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class PatchEntry:
    """A patch entry in the library."""

    patch_id: str
    file_path: str
    format: PatchFormat
    metadata: PatchMetadata
    file_size: int = 0
    file_crc32: str = ""
    added_date: str = ""
    platform_id: Optional[str] = None
    is_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "patch_id": self.patch_id,
            "file_path": self.file_path,
            "format": self.format.name,
            "metadata": asdict(self.metadata),
            "file_size": self.file_size,
            "file_crc32": self.file_crc32,
            "added_date": self.added_date,
            "platform_id": self.platform_id,
            "is_verified": self.is_verified,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PatchEntry":
        """Create from dictionary."""
        return PatchEntry(
            patch_id=data["patch_id"],
            file_path=data["file_path"],
            format=PatchFormat[data["format"]],
            metadata=PatchMetadata(**data.get("metadata", {})),
            file_size=data.get("file_size", 0),
            file_crc32=data.get("file_crc32", ""),
            added_date=data.get("added_date", ""),
            platform_id=data.get("platform_id"),
            is_verified=data.get("is_verified", False),
        )


class PatchLibrary:
    """Manages a library of ROM patches.

    Implements F80: Patch-Bibliothek-Manager

    Features:
    - Add/remove patches
    - Search by ROM, platform, type
    - Persistent storage
    - Metadata management
    """

    def __init__(self, library_path: Optional[str] = None):
        """Initialize patch library.

        Args:
            library_path: Path to library JSON file (default: patches_library.json in CWD)
        """
        self.library_path = library_path or "patches_library.json"
        self._patches: Dict[str, PatchEntry] = {}
        self._patcher = Patcher()
        self._load()

    def add_patch(
        self,
        patch_path: str,
        *,
        metadata: Optional[PatchMetadata] = None,
        platform_id: Optional[str] = None,
    ) -> Optional[PatchEntry]:
        """Add a patch to the library.

        Args:
            patch_path: Path to patch file
            metadata: Optional metadata
            platform_id: Optional platform ID

        Returns:
            PatchEntry if successful, None otherwise
        """
        path = Path(patch_path)
        if not path.exists():
            return None

        # Detect format
        patch_format = self._patcher.detect_format(patch_path)
        if patch_format == PatchFormat.UNKNOWN:
            return None

        # Calculate patch ID from file hash
        patch_id = self._calculate_patch_id(patch_path)

        # Check if already exists
        if patch_id in self._patches:
            return self._patches[patch_id]

        # Get file info
        stat = path.stat()
        file_crc32 = self._calculate_crc32(patch_path)

        # Create entry
        entry = PatchEntry(
            patch_id=patch_id,
            file_path=str(path.absolute()),
            format=patch_format,
            metadata=metadata or PatchMetadata(),
            file_size=stat.st_size,
            file_crc32=file_crc32,
            added_date=datetime.now().isoformat(),
            platform_id=platform_id,
        )

        # Auto-fill metadata from filename if empty
        if not entry.metadata.title:
            entry.metadata.title = path.stem

        self._patches[patch_id] = entry
        self._save()

        return entry

    def add_patches_from_directory(
        self,
        directory: str,
        *,
        platform_id: Optional[str] = None,
        recursive: bool = True,
    ) -> List[PatchEntry]:
        """Add all patches from a directory.

        Args:
            directory: Directory to scan
            platform_id: Platform ID to assign
            recursive: Scan subdirectories

        Returns:
            List of added PatchEntries
        """
        dir_path = Path(directory)
        if not dir_path.is_dir():
            return []

        extensions = [".ips", ".bps", ".ups"]
        pattern = "**/*" if recursive else "*"

        added = []
        for ext in extensions:
            for path in dir_path.glob(f"{pattern}{ext}"):
                entry = self.add_patch(str(path), platform_id=platform_id)
                if entry:
                    added.append(entry)

        return added

    def remove_patch(self, patch_id: str) -> bool:
        """Remove a patch from the library.

        Args:
            patch_id: Patch ID to remove

        Returns:
            True if removed
        """
        if patch_id in self._patches:
            del self._patches[patch_id]
            self._save()
            return True
        return False

    def get_patch(self, patch_id: str) -> Optional[PatchEntry]:
        """Get patch by ID.

        Args:
            patch_id: Patch ID

        Returns:
            PatchEntry or None
        """
        return self._patches.get(patch_id)

    def get_all_patches(self) -> List[PatchEntry]:
        """Get all patches in library."""
        return list(self._patches.values())

    def search_by_platform(self, platform_id: str) -> List[PatchEntry]:
        """Find patches for a platform.

        Args:
            platform_id: Platform ID

        Returns:
            List of matching patches
        """
        return [p for p in self._patches.values() if p.platform_id == platform_id]

    def search_by_type(self, patch_type: str) -> List[PatchEntry]:
        """Find patches by type.

        Args:
            patch_type: Patch type (Translation, Hack, etc.)

        Returns:
            List of matching patches
        """
        return [
            p for p in self._patches.values()
            if p.metadata.patch_type.lower() == patch_type.lower()
        ]

    def search_by_rom_crc32(self, crc32: str) -> List[PatchEntry]:
        """Find patches targeting a ROM by CRC32.

        Args:
            crc32: Target ROM CRC32

        Returns:
            List of compatible patches
        """
        return [
            p for p in self._patches.values()
            if p.metadata.target_rom_crc32.lower() == crc32.lower()
        ]

    def search_by_rom_sha1(self, sha1: str) -> List[PatchEntry]:
        """Find patches targeting a ROM by SHA1.

        Args:
            sha1: Target ROM SHA1

        Returns:
            List of compatible patches
        """
        return [
            p for p in self._patches.values()
            if p.metadata.target_rom_sha1.lower() == sha1.lower()
        ]

    def search_by_query(self, query: str) -> List[PatchEntry]:
        """Search patches by text query.

        Args:
            query: Search text

        Returns:
            List of matching patches
        """
        query_lower = query.lower()
        results = []

        for patch in self._patches.values():
            # Search in metadata fields
            if (
                query_lower in patch.metadata.title.lower()
                or query_lower in patch.metadata.description.lower()
                or query_lower in patch.metadata.author.lower()
                or query_lower in patch.metadata.target_rom_name.lower()
                or any(query_lower in tag.lower() for tag in patch.metadata.tags)
            ):
                results.append(patch)

        return results

    def update_metadata(
        self, patch_id: str, metadata: PatchMetadata
    ) -> bool:
        """Update patch metadata.

        Args:
            patch_id: Patch ID
            metadata: New metadata

        Returns:
            True if updated
        """
        if patch_id in self._patches:
            self._patches[patch_id].metadata = metadata
            self._save()
            return True
        return False

    def verify_patch(self, patch_id: str) -> bool:
        """Verify patch file exists and is valid.

        Args:
            patch_id: Patch ID

        Returns:
            True if valid
        """
        patch = self._patches.get(patch_id)
        if not patch:
            return False

        path = Path(patch.file_path)
        if not path.exists():
            return False

        # Verify CRC32
        current_crc = self._calculate_crc32(patch.file_path)
        if current_crc != patch.file_crc32:
            return False

        patch.is_verified = True
        self._save()
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get library statistics.

        Returns:
            Statistics dictionary
        """
        patches = list(self._patches.values())

        # Count by format
        by_format = {}
        for patch in patches:
            fmt = patch.format.name
            by_format[fmt] = by_format.get(fmt, 0) + 1

        # Count by type
        by_type = {}
        for patch in patches:
            ptype = patch.metadata.patch_type or "Unknown"
            by_type[ptype] = by_type.get(ptype, 0) + 1

        # Count by platform
        by_platform = {}
        for patch in patches:
            plat = patch.platform_id or "Unknown"
            by_platform[plat] = by_platform.get(plat, 0) + 1

        return {
            "total_patches": len(patches),
            "total_size_bytes": sum(p.file_size for p in patches),
            "by_format": by_format,
            "by_type": by_type,
            "by_platform": by_platform,
            "verified_count": sum(1 for p in patches if p.is_verified),
        }

    def _calculate_patch_id(self, path: str) -> str:
        """Calculate unique ID for patch file."""
        hasher = hashlib.sha1()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()[:16]

    def _calculate_crc32(self, path: str) -> str:
        """Calculate CRC32 of file."""
        import zlib
        crc = 0
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                crc = zlib.crc32(chunk, crc)
        return f"{crc & 0xFFFFFFFF:08X}"

    def _load(self) -> None:
        """Load library from disk."""
        path = Path(self.library_path)
        if not path.exists():
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for patch_data in data.get("patches", []):
                entry = PatchEntry.from_dict(patch_data)
                self._patches[entry.patch_id] = entry

        except (json.JSONDecodeError, KeyError):
            pass

    def _save(self) -> None:
        """Save library to disk."""
        data = {
            "version": "1.0",
            "updated": datetime.now().isoformat(),
            "patches": [p.to_dict() for p in self._patches.values()],
        }

        with open(self.library_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
