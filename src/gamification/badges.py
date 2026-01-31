"""Gamification Progress Badges - F68 Implementation.

Provides milestone badges and achievements for ROM collection management.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class BadgeCategory(Enum):
    """Badge categories."""

    COLLECTION = auto()  # Collection milestones
    SORTING = auto()  # Sorting achievements
    DISCOVERY = auto()  # Discovery/scanning
    QUALITY = auto()  # Collection quality
    COMPLETIONIST = auto()  # Completeness goals
    SPECIAL = auto()  # Special achievements


class BadgeTier(Enum):
    """Badge tiers."""

    BRONZE = 1
    SILVER = 2
    GOLD = 3
    PLATINUM = 4
    DIAMOND = 5


@dataclass
class Badge:
    """A badge definition."""

    id: str
    name: str
    description: str
    category: BadgeCategory
    tier: BadgeTier = BadgeTier.BRONZE
    icon: str = "🏆"
    requirement: int = 1  # Target value
    hidden: bool = False  # Hidden until unlocked


@dataclass
class BadgeProgress:
    """Progress towards a badge."""

    badge_id: str
    current_value: int = 0
    unlocked: bool = False
    unlocked_at: Optional[float] = None
    notified: bool = False


# Built-in badge definitions
BADGES: List[Badge] = [
    # Collection Milestones
    Badge(
        id="first_rom",
        name="First Steps",
        description="Add your first ROM to the collection",
        category=BadgeCategory.COLLECTION,
        tier=BadgeTier.BRONZE,
        icon="🎮",
        requirement=1,
    ),
    Badge(
        id="roms_100",
        name="Growing Collection",
        description="Reach 100 ROMs in your collection",
        category=BadgeCategory.COLLECTION,
        tier=BadgeTier.BRONZE,
        icon="📦",
        requirement=100,
    ),
    Badge(
        id="roms_500",
        name="Serious Collector",
        description="Reach 500 ROMs in your collection",
        category=BadgeCategory.COLLECTION,
        tier=BadgeTier.SILVER,
        icon="🗃️",
        requirement=500,
    ),
    Badge(
        id="roms_1000",
        name="ROM Hoarder",
        description="Reach 1,000 ROMs in your collection",
        category=BadgeCategory.COLLECTION,
        tier=BadgeTier.GOLD,
        icon="🏛️",
        requirement=1000,
    ),
    Badge(
        id="roms_5000",
        name="Digital Archivist",
        description="Reach 5,000 ROMs in your collection",
        category=BadgeCategory.COLLECTION,
        tier=BadgeTier.PLATINUM,
        icon="🏆",
        requirement=5000,
    ),
    Badge(
        id="roms_10000",
        name="Legendary Curator",
        description="Reach 10,000 ROMs in your collection",
        category=BadgeCategory.COLLECTION,
        tier=BadgeTier.DIAMOND,
        icon="💎",
        requirement=10000,
    ),
    # Sorting Achievements
    Badge(
        id="first_sort",
        name="Organized!",
        description="Complete your first sorting operation",
        category=BadgeCategory.SORTING,
        tier=BadgeTier.BRONZE,
        icon="📁",
        requirement=1,
    ),
    Badge(
        id="sorts_10",
        name="Getting Tidy",
        description="Complete 10 sorting operations",
        category=BadgeCategory.SORTING,
        tier=BadgeTier.SILVER,
        icon="🧹",
        requirement=10,
    ),
    Badge(
        id="sorts_50",
        name="Organization Pro",
        description="Complete 50 sorting operations",
        category=BadgeCategory.SORTING,
        tier=BadgeTier.GOLD,
        icon="✨",
        requirement=50,
    ),
    Badge(
        id="sorts_100",
        name="Sorting Master",
        description="Complete 100 sorting operations",
        category=BadgeCategory.SORTING,
        tier=BadgeTier.PLATINUM,
        icon="👑",
        requirement=100,
    ),
    # Discovery/Scanning
    Badge(
        id="first_scan",
        name="Explorer",
        description="Complete your first scan",
        category=BadgeCategory.DISCOVERY,
        tier=BadgeTier.BRONZE,
        icon="🔍",
        requirement=1,
    ),
    Badge(
        id="systems_5",
        name="Multi-Platform",
        description="Have ROMs from 5 different systems",
        category=BadgeCategory.DISCOVERY,
        tier=BadgeTier.SILVER,
        icon="🎯",
        requirement=5,
    ),
    Badge(
        id="systems_10",
        name="Console Connoisseur",
        description="Have ROMs from 10 different systems",
        category=BadgeCategory.DISCOVERY,
        tier=BadgeTier.GOLD,
        icon="🌟",
        requirement=10,
    ),
    Badge(
        id="systems_20",
        name="Platform Master",
        description="Have ROMs from 20 different systems",
        category=BadgeCategory.DISCOVERY,
        tier=BadgeTier.PLATINUM,
        icon="🎪",
        requirement=20,
    ),
    # Quality Achievements
    Badge(
        id="verified_100",
        name="Quality Conscious",
        description="Have 100 verified ROMs (hash-matched)",
        category=BadgeCategory.QUALITY,
        tier=BadgeTier.BRONZE,
        icon="✅",
        requirement=100,
    ),
    Badge(
        id="verified_500",
        name="Authenticity Expert",
        description="Have 500 verified ROMs",
        category=BadgeCategory.QUALITY,
        tier=BadgeTier.SILVER,
        icon="🔐",
        requirement=500,
    ),
    Badge(
        id="no_bad_dumps",
        name="Clean Collection",
        description="Remove all bad dumps from collection",
        category=BadgeCategory.QUALITY,
        tier=BadgeTier.GOLD,
        icon="🛡️",
        requirement=1,
    ),
    # Completionist
    Badge(
        id="system_complete_50",
        name="Halfway There",
        description="Reach 50% completion for any system",
        category=BadgeCategory.COMPLETIONIST,
        tier=BadgeTier.SILVER,
        icon="📊",
        requirement=50,
    ),
    Badge(
        id="system_complete_75",
        name="Almost Complete",
        description="Reach 75% completion for any system",
        category=BadgeCategory.COMPLETIONIST,
        tier=BadgeTier.GOLD,
        icon="📈",
        requirement=75,
    ),
    Badge(
        id="system_complete_100",
        name="Completionist",
        description="Reach 100% completion for any system",
        category=BadgeCategory.COMPLETIONIST,
        tier=BadgeTier.PLATINUM,
        icon="🏅",
        requirement=100,
    ),
    Badge(
        id="full_set",
        name="Full Set Collector",
        description="Complete a full verified set for a system",
        category=BadgeCategory.COMPLETIONIST,
        tier=BadgeTier.DIAMOND,
        icon="💎",
        requirement=1,
    ),
    # Special
    Badge(
        id="night_owl",
        name="Night Owl",
        description="Use ROM-Sorter after midnight",
        category=BadgeCategory.SPECIAL,
        tier=BadgeTier.BRONZE,
        icon="🦉",
        requirement=1,
        hidden=True,
    ),
    Badge(
        id="speed_demon",
        name="Speed Demon",
        description="Sort 1000+ ROMs in under 5 minutes",
        category=BadgeCategory.SPECIAL,
        tier=BadgeTier.GOLD,
        icon="⚡",
        requirement=1,
        hidden=True,
    ),
    Badge(
        id="retro_enthusiast",
        name="Retro Enthusiast",
        description="Have ROMs from consoles released before 1990",
        category=BadgeCategory.SPECIAL,
        tier=BadgeTier.SILVER,
        icon="📼",
        requirement=5,
    ),
]


class BadgeManager:
    """Badge and achievement manager.

    Implements F68: Gamification-Progress-Badges

    Features:
    - Progress tracking
    - Badge unlocking
    - Notifications
    - Statistics
    """

    CONFIG_FILENAME = "badges.json"

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize badge manager.

        Args:
            config_dir: Configuration directory
        """
        self._config_dir = Path(config_dir) if config_dir else Path("config")
        self._badges = {badge.id: badge for badge in BADGES}
        self._progress: Dict[str, BadgeProgress] = {}
        self._callbacks: List[Callable[[Badge], None]] = []

        self._load_progress()

    def _load_progress(self) -> None:
        """Load progress from file."""
        config_file = self._config_dir / self.CONFIG_FILENAME

        if not config_file.exists():
            # Initialize progress for all badges
            for badge_id in self._badges:
                self._progress[badge_id] = BadgeProgress(badge_id=badge_id)
            return

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for badge_id, progress_data in data.get("progress", {}).items():
                self._progress[badge_id] = BadgeProgress(
                    badge_id=badge_id,
                    current_value=progress_data.get("current_value", 0),
                    unlocked=progress_data.get("unlocked", False),
                    unlocked_at=progress_data.get("unlocked_at"),
                    notified=progress_data.get("notified", False),
                )

            # Add any new badges
            for badge_id in self._badges:
                if badge_id not in self._progress:
                    self._progress[badge_id] = BadgeProgress(badge_id=badge_id)

        except Exception:
            for badge_id in self._badges:
                self._progress[badge_id] = BadgeProgress(badge_id=badge_id)

    def _save_progress(self) -> None:
        """Save progress to file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        config_file = self._config_dir / self.CONFIG_FILENAME

        data = {
            "progress": {
                badge_id: {
                    "current_value": progress.current_value,
                    "unlocked": progress.unlocked,
                    "unlocked_at": progress.unlocked_at,
                    "notified": progress.notified,
                }
                for badge_id, progress in self._progress.items()
            }
        }

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _notify_unlock(self, badge: Badge) -> None:
        """Notify callbacks of badge unlock."""
        for callback in self._callbacks:
            try:
                callback(badge)
            except Exception:
                pass

    def update_progress(self, badge_id: str, value: int) -> Optional[Badge]:
        """Update progress for a badge.

        Args:
            badge_id: Badge ID
            value: New value

        Returns:
            Badge if newly unlocked, None otherwise
        """
        if badge_id not in self._badges or badge_id not in self._progress:
            return None

        badge = self._badges[badge_id]
        progress = self._progress[badge_id]

        # Already unlocked
        if progress.unlocked:
            return None

        progress.current_value = value

        # Check if unlocked
        if value >= badge.requirement:
            progress.unlocked = True
            progress.unlocked_at = time.time()
            progress.notified = False

            self._save_progress()
            self._notify_unlock(badge)

            return badge

        self._save_progress()
        return None

    def increment_progress(self, badge_id: str, amount: int = 1) -> Optional[Badge]:
        """Increment progress for a badge.

        Args:
            badge_id: Badge ID
            amount: Amount to increment

        Returns:
            Badge if newly unlocked
        """
        if badge_id not in self._progress:
            return None

        current = self._progress[badge_id].current_value
        return self.update_progress(badge_id, current + amount)

    def check_collection_badges(
        self, rom_count: int, systems_count: int, verified_count: int
    ) -> List[Badge]:
        """Check and update collection-related badges.

        Args:
            rom_count: Total ROM count
            systems_count: Number of systems
            verified_count: Number of verified ROMs

        Returns:
            List of newly unlocked badges
        """
        unlocked = []

        # ROM count badges
        rom_badges = ["first_rom", "roms_100", "roms_500", "roms_1000", "roms_5000", "roms_10000"]
        for badge_id in rom_badges:
            result = self.update_progress(badge_id, rom_count)
            if result:
                unlocked.append(result)

        # Systems badges
        system_badges = ["systems_5", "systems_10", "systems_20"]
        for badge_id in system_badges:
            result = self.update_progress(badge_id, systems_count)
            if result:
                unlocked.append(result)

        # Verified badges
        verified_badges = ["verified_100", "verified_500"]
        for badge_id in verified_badges:
            result = self.update_progress(badge_id, verified_count)
            if result:
                unlocked.append(result)

        return unlocked

    def check_completeness_badges(self, completion_percent: float) -> List[Badge]:
        """Check completion-related badges.

        Args:
            completion_percent: Completion percentage

        Returns:
            List of newly unlocked badges
        """
        unlocked = []

        if completion_percent >= 50:
            result = self.update_progress("system_complete_50", int(completion_percent))
            if result:
                unlocked.append(result)

        if completion_percent >= 75:
            result = self.update_progress("system_complete_75", int(completion_percent))
            if result:
                unlocked.append(result)

        if completion_percent >= 100:
            result = self.update_progress("system_complete_100", 100)
            if result:
                unlocked.append(result)

        return unlocked

    def check_special_badges(self) -> List[Badge]:
        """Check special/time-based badges.

        Returns:
            List of newly unlocked badges
        """
        unlocked = []

        # Night owl - after midnight
        current_hour = datetime.now().hour
        if 0 <= current_hour < 5:
            result = self.update_progress("night_owl", 1)
            if result:
                unlocked.append(result)

        return unlocked

    def record_scan(self) -> Optional[Badge]:
        """Record a scan operation.

        Returns:
            Badge if first scan unlocked
        """
        return self.increment_progress("first_scan")

    def record_sort(self) -> List[Badge]:
        """Record a sort operation.

        Returns:
            List of newly unlocked badges
        """
        unlocked = []

        result = self.increment_progress("first_sort")
        if result:
            unlocked.append(result)

        result = self.increment_progress("sorts_10")
        if result:
            unlocked.append(result)

        result = self.increment_progress("sorts_50")
        if result:
            unlocked.append(result)

        result = self.increment_progress("sorts_100")
        if result:
            unlocked.append(result)

        return unlocked

    def get_badge(self, badge_id: str) -> Optional[Badge]:
        """Get badge definition.

        Args:
            badge_id: Badge ID

        Returns:
            Badge or None
        """
        return self._badges.get(badge_id)

    def get_progress(self, badge_id: str) -> Optional[BadgeProgress]:
        """Get badge progress.

        Args:
            badge_id: Badge ID

        Returns:
            BadgeProgress or None
        """
        return self._progress.get(badge_id)

    def get_all_badges(self, include_hidden: bool = False) -> List[Dict[str, Any]]:
        """Get all badges with progress.

        Args:
            include_hidden: Include hidden badges

        Returns:
            List of badge info dicts
        """
        result = []

        for badge_id, badge in self._badges.items():
            if badge.hidden and not include_hidden:
                progress = self._progress.get(badge_id)
                if not progress or not progress.unlocked:
                    continue

            progress = self._progress.get(badge_id, BadgeProgress(badge_id=badge_id))

            result.append(
                {
                    "id": badge.id,
                    "name": badge.name,
                    "description": badge.description,
                    "category": badge.category.name,
                    "tier": badge.tier.name,
                    "icon": badge.icon,
                    "requirement": badge.requirement,
                    "current_value": progress.current_value,
                    "progress_percent": min(
                        100, (progress.current_value / badge.requirement) * 100
                    ),
                    "unlocked": progress.unlocked,
                    "unlocked_at": (
                        datetime.fromtimestamp(progress.unlocked_at).isoformat()
                        if progress.unlocked_at
                        else None
                    ),
                    "hidden": badge.hidden,
                }
            )

        return result

    def get_unlocked_badges(self) -> List[Badge]:
        """Get all unlocked badges.

        Returns:
            List of unlocked Badges
        """
        return [
            self._badges[badge_id]
            for badge_id, progress in self._progress.items()
            if progress.unlocked and badge_id in self._badges
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get badge statistics.

        Returns:
            Stats dict
        """
        total = len(self._badges)
        unlocked = sum(1 for p in self._progress.values() if p.unlocked)

        by_category: Dict[str, Dict[str, int]] = {}
        for badge in self._badges.values():
            cat = badge.category.name
            if cat not in by_category:
                by_category[cat] = {"total": 0, "unlocked": 0}
            by_category[cat]["total"] += 1

            progress = self._progress.get(badge.id)
            if progress and progress.unlocked:
                by_category[cat]["unlocked"] += 1

        return {
            "total_badges": total,
            "unlocked_badges": unlocked,
            "unlock_percent": (unlocked / total * 100) if total > 0 else 0,
            "by_category": by_category,
        }

    def register_unlock_callback(self, callback: Callable[[Badge], None]) -> None:
        """Register callback for badge unlocks.

        Args:
            callback: Callback(badge)
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_unlock_callback(self, callback: Callable[[Badge], None]) -> None:
        """Unregister callback.

        Args:
            callback: Callback to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def mark_notified(self, badge_id: str) -> None:
        """Mark badge as notified.

        Args:
            badge_id: Badge ID
        """
        if badge_id in self._progress:
            self._progress[badge_id].notified = True
            self._save_progress()

    def get_unnotified_unlocks(self) -> List[Badge]:
        """Get badges unlocked but not yet notified.

        Returns:
            List of unnotified Badges
        """
        return [
            self._badges[badge_id]
            for badge_id, progress in self._progress.items()
            if progress.unlocked
            and not progress.notified
            and badge_id in self._badges
        ]
