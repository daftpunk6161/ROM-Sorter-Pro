"""Wishlist Manager - F92 Implementation.

Tracks missing ROMs and manages wishlists.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class WishlistPriority(Enum):
    """Wishlist item priority."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class WishlistItem:
    """A wishlist item (missing ROM)."""

    name: str
    platform: str
    region: str = ""
    year: str = ""
    genre: str = ""
    priority: WishlistPriority = WishlistPriority.MEDIUM
    notes: str = ""
    added_date: float = 0.0
    source: str = ""  # DAT file, manual, etc.
    dat_entry: Optional[Dict[str, Any]] = None

    @property
    def added_datetime(self) -> datetime:
        """Get added datetime."""
        return datetime.fromtimestamp(self.added_date) if self.added_date else datetime.now()

    @property
    def display_name(self) -> str:
        """Get display name with region."""
        if self.region:
            return f"{self.name} ({self.region})"
        return self.name


@dataclass
class WishlistExport:
    """Wishlist export result."""

    success: bool
    path: str = ""
    item_count: int = 0
    error: str = ""


class WishlistManager:
    """Manages ROM wishlists.

    Implements F92: Wunschlisten-Manager

    Features:
    - Track missing ROMs from DAT comparisons
    - Manual wishlist management
    - Priority sorting
    - Export capabilities
    """

    def __init__(self, storage_path: str):
        """Initialize wishlist manager.

        Args:
            storage_path: Path to wishlist storage
        """
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._wishlists: Dict[str, List[WishlistItem]] = {}
        self._load_wishlists()

    def _get_wishlist_file(self, list_name: str) -> Path:
        """Get path to wishlist file."""
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in list_name)
        return self._storage_path / f"{safe_name}.json"

    def _load_wishlists(self) -> None:
        """Load all wishlists from storage."""
        for file in self._storage_path.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                list_name = data.get("name", file.stem)
                items = []

                for item_data in data.get("items", []):
                    items.append(WishlistItem(
                        name=item_data.get("name", ""),
                        platform=item_data.get("platform", ""),
                        region=item_data.get("region", ""),
                        year=item_data.get("year", ""),
                        genre=item_data.get("genre", ""),
                        priority=WishlistPriority(item_data.get("priority", 2)),
                        notes=item_data.get("notes", ""),
                        added_date=item_data.get("added_date", 0),
                        source=item_data.get("source", ""),
                    ))

                self._wishlists[list_name] = items

            except Exception:
                pass

    def _save_wishlist(self, list_name: str) -> bool:
        """Save a wishlist to storage."""
        if list_name not in self._wishlists:
            return False

        items = self._wishlists[list_name]
        data = {
            "name": list_name,
            "updated": datetime.now().isoformat(),
            "items": [
                {
                    "name": item.name,
                    "platform": item.platform,
                    "region": item.region,
                    "year": item.year,
                    "genre": item.genre,
                    "priority": item.priority.value,
                    "notes": item.notes,
                    "added_date": item.added_date,
                    "source": item.source,
                }
                for item in items
            ],
        }

        try:
            with open(self._get_wishlist_file(list_name), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False

    def create_wishlist(self, name: str) -> bool:
        """Create a new wishlist.

        Args:
            name: Wishlist name

        Returns:
            True if created
        """
        if name in self._wishlists:
            return False

        self._wishlists[name] = []
        return self._save_wishlist(name)

    def delete_wishlist(self, name: str) -> bool:
        """Delete a wishlist.

        Args:
            name: Wishlist name

        Returns:
            True if deleted
        """
        if name not in self._wishlists:
            return False

        del self._wishlists[name]

        file_path = self._get_wishlist_file(name)
        if file_path.exists():
            file_path.unlink()

        return True

    def get_wishlists(self) -> List[str]:
        """Get all wishlist names.

        Returns:
            List of names
        """
        return list(self._wishlists.keys())

    def add_item(
        self,
        list_name: str,
        item: WishlistItem,
        save: bool = True,
    ) -> bool:
        """Add item to wishlist.

        Args:
            list_name: Wishlist name
            item: Item to add
            save: Save immediately

        Returns:
            True if added
        """
        if list_name not in self._wishlists:
            self.create_wishlist(list_name)

        # Check for duplicate
        for existing in self._wishlists[list_name]:
            if (
                existing.name == item.name
                and existing.platform == item.platform
                and existing.region == item.region
            ):
                return False  # Already exists

        if not item.added_date:
            item.added_date = datetime.now().timestamp()

        self._wishlists[list_name].append(item)

        if save:
            self._save_wishlist(list_name)

        return True

    def remove_item(
        self,
        list_name: str,
        item_name: str,
        platform: str = "",
        save: bool = True,
    ) -> bool:
        """Remove item from wishlist.

        Args:
            list_name: Wishlist name
            item_name: Item name
            platform: Platform filter
            save: Save immediately

        Returns:
            True if removed
        """
        if list_name not in self._wishlists:
            return False

        original_len = len(self._wishlists[list_name])
        self._wishlists[list_name] = [
            item
            for item in self._wishlists[list_name]
            if not (
                item.name == item_name
                and (not platform or item.platform == platform)
            )
        ]

        if len(self._wishlists[list_name]) < original_len:
            if save:
                self._save_wishlist(list_name)
            return True

        return False

    def get_items(
        self,
        list_name: str,
        platform: str = "",
        priority: Optional[WishlistPriority] = None,
        sort_by: str = "priority",
    ) -> List[WishlistItem]:
        """Get wishlist items.

        Args:
            list_name: Wishlist name
            platform: Filter by platform
            priority: Filter by priority
            sort_by: 'priority', 'name', 'date', 'platform'

        Returns:
            List of items
        """
        if list_name not in self._wishlists:
            return []

        items = self._wishlists[list_name]

        # Apply filters
        if platform:
            items = [i for i in items if i.platform.lower() == platform.lower()]

        if priority:
            items = [i for i in items if i.priority == priority]

        # Sort
        if sort_by == "priority":
            items = sorted(items, key=lambda x: x.priority.value, reverse=True)
        elif sort_by == "name":
            items = sorted(items, key=lambda x: x.name.lower())
        elif sort_by == "date":
            items = sorted(items, key=lambda x: x.added_date, reverse=True)
        elif sort_by == "platform":
            items = sorted(items, key=lambda x: (x.platform, x.name.lower()))

        return items

    def import_from_dat_comparison(
        self,
        list_name: str,
        missing_entries: List[Dict[str, Any]],
        source_dat: str = "",
    ) -> int:
        """Import missing ROMs from DAT comparison.

        Args:
            list_name: Target wishlist
            missing_entries: List of missing ROM entries
            source_dat: Source DAT name

        Returns:
            Number of items added
        """
        if list_name not in self._wishlists:
            self.create_wishlist(list_name)

        added = 0
        for entry in missing_entries:
            item = WishlistItem(
                name=entry.get("name", ""),
                platform=entry.get("platform", ""),
                region=entry.get("region", ""),
                year=entry.get("year", ""),
                genre=entry.get("genre", ""),
                source=source_dat,
                dat_entry=entry,
            )

            if self.add_item(list_name, item, save=False):
                added += 1

        if added > 0:
            self._save_wishlist(list_name)

        return added

    def mark_as_found(
        self,
        list_name: str,
        found_roms: List[Dict[str, Any]],
    ) -> int:
        """Mark ROMs as found (remove from wishlist).

        Args:
            list_name: Wishlist name
            found_roms: List of found ROMs

        Returns:
            Number removed
        """
        if list_name not in self._wishlists:
            return 0

        removed = 0
        found_names = {rom.get("name", "").lower() for rom in found_roms}

        original_items = self._wishlists[list_name]
        self._wishlists[list_name] = [
            item
            for item in original_items
            if item.name.lower() not in found_names
        ]

        removed = len(original_items) - len(self._wishlists[list_name])

        if removed > 0:
            self._save_wishlist(list_name)

        return removed

    def export_txt(self, list_name: str, path: str) -> WishlistExport:
        """Export wishlist as TXT.

        Args:
            list_name: Wishlist name
            path: Output path

        Returns:
            WishlistExport
        """
        if list_name not in self._wishlists:
            return WishlistExport(success=False, error="Wishlist not found")

        items = self.get_items(list_name, sort_by="platform")

        lines = [
            f"# Wishlist: {list_name}",
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"# Total: {len(items)} items",
            "",
        ]

        current_platform = ""
        for item in items:
            if item.platform != current_platform:
                current_platform = item.platform
                lines.append(f"\n=== {current_platform} ===")

            priority_marker = "!" * item.priority.value
            lines.append(f"[{priority_marker}] {item.display_name}")

        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            return WishlistExport(
                success=True,
                path=path,
                item_count=len(items),
            )
        except Exception as e:
            return WishlistExport(success=False, error=str(e))

    def export_json(self, list_name: str, path: str) -> WishlistExport:
        """Export wishlist as JSON.

        Args:
            list_name: Wishlist name
            path: Output path

        Returns:
            WishlistExport
        """
        if list_name not in self._wishlists:
            return WishlistExport(success=False, error="Wishlist not found")

        items = self._wishlists[list_name]
        data = {
            "name": list_name,
            "exported": datetime.now().isoformat(),
            "total": len(items),
            "items": [
                {
                    "name": item.name,
                    "platform": item.platform,
                    "region": item.region,
                    "year": item.year,
                    "genre": item.genre,
                    "priority": item.priority.name,
                    "notes": item.notes,
                }
                for item in items
            ],
        }

        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            return WishlistExport(
                success=True,
                path=path,
                item_count=len(items),
            )
        except Exception as e:
            return WishlistExport(success=False, error=str(e))

    def export_csv(self, list_name: str, path: str) -> WishlistExport:
        """Export wishlist as CSV.

        Args:
            list_name: Wishlist name
            path: Output path

        Returns:
            WishlistExport
        """
        if list_name not in self._wishlists:
            return WishlistExport(success=False, error="Wishlist not found")

        items = self._wishlists[list_name]

        lines = ["Name,Platform,Region,Year,Genre,Priority,Notes"]
        for item in items:
            # Escape commas and quotes
            name = item.name.replace('"', '""')
            notes = item.notes.replace('"', '""')

            lines.append(
                f'"{name}","{item.platform}","{item.region}",'
                f'"{item.year}","{item.genre}","{item.priority.name}","{notes}"'
            )

        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            return WishlistExport(
                success=True,
                path=path,
                item_count=len(items),
            )
        except Exception as e:
            return WishlistExport(success=False, error=str(e))

    def get_statistics(self, list_name: str) -> Dict[str, Any]:
        """Get wishlist statistics.

        Args:
            list_name: Wishlist name

        Returns:
            Statistics dict
        """
        if list_name not in self._wishlists:
            return {}

        items = self._wishlists[list_name]

        platforms: Dict[str, int] = {}
        priorities: Dict[str, int] = {}

        for item in items:
            platforms[item.platform] = platforms.get(item.platform, 0) + 1
            priorities[item.priority.name] = priorities.get(item.priority.name, 0) + 1

        return {
            "total_items": len(items),
            "platforms": platforms,
            "priorities": priorities,
            "top_platforms": sorted(
                platforms.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }
