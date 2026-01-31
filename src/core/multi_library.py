"""Multi-Library Workspace - F63 Implementation.

Manages multiple ROM collections in parallel.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Library:
    """A ROM library/collection."""

    id: str
    name: str
    path: str
    description: str = ""
    created_at: float = 0.0
    last_scanned: Optional[float] = None
    rom_count: int = 0
    total_size_bytes: int = 0
    systems: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    color: str = "#3498db"  # UI accent color
    icon: str = "📁"
    is_active: bool = True


@dataclass
class LibraryStats:
    """Statistics for a library."""

    library_id: str
    rom_count: int = 0
    total_size_bytes: int = 0
    systems_count: int = 0
    last_scanned: Optional[str] = None
    completeness_percent: float = 0.0


class MultiLibraryManager:
    """Multi-library workspace manager.

    Implements F63: Multi-Library-Workspace

    Features:
    - Multiple collections
    - Quick switching
    - Per-library settings
    - Aggregate views
    """

    CONFIG_FILENAME = "libraries.json"

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize multi-library manager.

        Args:
            config_dir: Configuration directory
        """
        self._config_dir = Path(config_dir) if config_dir else Path("config")
        self._libraries: Dict[str, Library] = {}
        self._active_library_id: Optional[str] = None
        self._callbacks: List[Callable[[str, Library], None]] = []

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        config_file = self._config_dir / self.CONFIG_FILENAME

        if not config_file.exists():
            return

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._active_library_id = data.get("active_library_id")

            for lib_data in data.get("libraries", []):
                lib = Library(
                    id=lib_data["id"],
                    name=lib_data["name"],
                    path=lib_data["path"],
                    description=lib_data.get("description", ""),
                    created_at=lib_data.get("created_at", 0),
                    last_scanned=lib_data.get("last_scanned"),
                    rom_count=lib_data.get("rom_count", 0),
                    total_size_bytes=lib_data.get("total_size_bytes", 0),
                    systems=lib_data.get("systems", []),
                    tags=lib_data.get("tags", []),
                    color=lib_data.get("color", "#3498db"),
                    icon=lib_data.get("icon", "📁"),
                    is_active=lib_data.get("is_active", True),
                )
                self._libraries[lib.id] = lib

        except Exception:
            pass

    def _save_config(self) -> None:
        """Save configuration to file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        config_file = self._config_dir / self.CONFIG_FILENAME

        data = {
            "active_library_id": self._active_library_id,
            "libraries": [
                {
                    "id": lib.id,
                    "name": lib.name,
                    "path": lib.path,
                    "description": lib.description,
                    "created_at": lib.created_at,
                    "last_scanned": lib.last_scanned,
                    "rom_count": lib.rom_count,
                    "total_size_bytes": lib.total_size_bytes,
                    "systems": lib.systems,
                    "tags": lib.tags,
                    "color": lib.color,
                    "icon": lib.icon,
                    "is_active": lib.is_active,
                }
                for lib in self._libraries.values()
            ],
        }

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _notify_callbacks(self, event: str, library: Library) -> None:
        """Notify registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(event, library)
            except Exception:
                pass

    def create_library(
        self,
        name: str,
        path: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        color: str = "#3498db",
        icon: str = "📁",
    ) -> Library:
        """Create a new library.

        Args:
            name: Library name
            path: Path to ROM collection
            description: Optional description
            tags: Optional tags
            color: UI accent color
            icon: Display icon

        Returns:
            New Library
        """
        library = Library(
            id=str(uuid.uuid4()),
            name=name,
            path=path,
            description=description,
            created_at=datetime.now().timestamp(),
            tags=tags or [],
            color=color,
            icon=icon,
        )

        self._libraries[library.id] = library

        # Set as active if first library
        if len(self._libraries) == 1:
            self._active_library_id = library.id

        self._save_config()
        self._notify_callbacks("created", library)

        return library

    def delete_library(self, library_id: str) -> bool:
        """Delete a library (config only, not files).

        Args:
            library_id: Library ID

        Returns:
            True if deleted
        """
        if library_id not in self._libraries:
            return False

        library = self._libraries[library_id]
        del self._libraries[library_id]

        # Update active if deleted
        if self._active_library_id == library_id:
            self._active_library_id = (
                next(iter(self._libraries.keys())) if self._libraries else None
            )

        self._save_config()
        self._notify_callbacks("deleted", library)

        return True

    def update_library(
        self,
        library_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> Optional[Library]:
        """Update library settings.

        Args:
            library_id: Library ID
            name: New name
            description: New description
            tags: New tags
            color: New color
            icon: New icon

        Returns:
            Updated Library or None
        """
        if library_id not in self._libraries:
            return None

        library = self._libraries[library_id]

        if name is not None:
            library.name = name
        if description is not None:
            library.description = description
        if tags is not None:
            library.tags = tags
        if color is not None:
            library.color = color
        if icon is not None:
            library.icon = icon

        self._save_config()
        self._notify_callbacks("updated", library)

        return library

    def set_active(self, library_id: str) -> bool:
        """Set active library.

        Args:
            library_id: Library ID

        Returns:
            True if set
        """
        if library_id not in self._libraries:
            return False

        self._active_library_id = library_id
        self._save_config()
        self._notify_callbacks("activated", self._libraries[library_id])

        return True

    def get_library(self, library_id: str) -> Optional[Library]:
        """Get library by ID.

        Args:
            library_id: Library ID

        Returns:
            Library or None
        """
        return self._libraries.get(library_id)

    def get_active_library(self) -> Optional[Library]:
        """Get currently active library.

        Returns:
            Active Library or None
        """
        if self._active_library_id:
            return self._libraries.get(self._active_library_id)
        return None

    def get_all_libraries(self) -> List[Library]:
        """Get all libraries.

        Returns:
            List of Libraries
        """
        return list(self._libraries.values())

    def get_libraries_by_tag(self, tag: str) -> List[Library]:
        """Get libraries with a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of Libraries
        """
        return [lib for lib in self._libraries.values() if tag in lib.tags]

    def update_scan_stats(
        self,
        library_id: str,
        rom_count: int,
        total_size_bytes: int,
        systems: List[str],
    ) -> bool:
        """Update library scan statistics.

        Args:
            library_id: Library ID
            rom_count: Number of ROMs
            total_size_bytes: Total size
            systems: Detected systems

        Returns:
            True if updated
        """
        if library_id not in self._libraries:
            return False

        library = self._libraries[library_id]
        library.rom_count = rom_count
        library.total_size_bytes = total_size_bytes
        library.systems = systems
        library.last_scanned = datetime.now().timestamp()

        self._save_config()
        self._notify_callbacks("scanned", library)

        return True

    def get_aggregate_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics across all libraries.

        Returns:
            Stats dict
        """
        total_roms = sum(lib.rom_count for lib in self._libraries.values())
        total_size = sum(lib.total_size_bytes for lib in self._libraries.values())

        all_systems: set[str] = set()
        for lib in self._libraries.values():
            all_systems.update(lib.systems)

        return {
            "library_count": len(self._libraries),
            "total_roms": total_roms,
            "total_size_bytes": total_size,
            "total_size_gb": total_size / (1024**3),
            "unique_systems": len(all_systems),
            "systems": sorted(all_systems),
        }

    def search_across_libraries(
        self, query: str, library_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search for ROMs across libraries.

        Args:
            query: Search query
            library_ids: Optional library filter

        Returns:
            Search results with library context
        """
        results = []
        query_lower = query.lower()

        libraries_to_search = (
            [self._libraries[id] for id in library_ids if id in self._libraries]
            if library_ids
            else self._libraries.values()
        )

        for library in libraries_to_search:
            lib_path = Path(library.path)
            if not lib_path.exists():
                continue

            # Simple file search
            for file_path in lib_path.rglob("*"):
                if file_path.is_file() and query_lower in file_path.name.lower():
                    results.append(
                        {
                            "library_id": library.id,
                            "library_name": library.name,
                            "path": str(file_path),
                            "name": file_path.name,
                        }
                    )

                    if len(results) >= 100:
                        return results

        return results

    def import_library_config(self, config_path: str) -> Optional[Library]:
        """Import library from external config.

        Args:
            config_path: Path to config file

        Returns:
            Imported Library or None
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return self.create_library(
                name=data.get("name", "Imported Library"),
                path=data.get("path", ""),
                description=data.get("description", ""),
                tags=data.get("tags", []),
            )

        except Exception:
            return None

    def export_library_config(self, library_id: str, output_path: str) -> bool:
        """Export library config.

        Args:
            library_id: Library ID
            output_path: Output file path

        Returns:
            True if exported
        """
        if library_id not in self._libraries:
            return False

        library = self._libraries[library_id]

        try:
            data = {
                "name": library.name,
                "path": library.path,
                "description": library.description,
                "tags": library.tags,
                "systems": library.systems,
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            return True

        except Exception:
            return False

    def register_callback(
        self, callback: Callable[[str, Library], None]
    ) -> None:
        """Register event callback.

        Args:
            callback: Callback(event, library)
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(
        self, callback: Callable[[str, Library], None]
    ) -> None:
        """Unregister callback.

        Args:
            callback: Callback to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
