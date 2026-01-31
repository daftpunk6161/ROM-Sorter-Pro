"""Collection Dashboard - F91 Implementation.

Provides statistics and visualizations for ROM collections.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SystemStats:
    """Statistics for a single system/platform."""

    name: str
    display_name: str
    rom_count: int = 0
    total_size_bytes: int = 0
    verified_count: int = 0
    unknown_count: int = 0
    regions: Dict[str, int] = field(default_factory=dict)
    years: Dict[int, int] = field(default_factory=dict)
    genres: Dict[str, int] = field(default_factory=dict)
    file_types: Dict[str, int] = field(default_factory=dict)

    @property
    def total_size_mb(self) -> float:
        """Size in MB."""
        return self.total_size_bytes / (1024 * 1024)

    @property
    def total_size_gb(self) -> float:
        """Size in GB."""
        return self.total_size_bytes / (1024 * 1024 * 1024)

    @property
    def verification_rate(self) -> float:
        """Percentage of verified ROMs."""
        if self.rom_count == 0:
            return 0.0
        return (self.verified_count / self.rom_count) * 100


@dataclass
class CollectionStats:
    """Overall collection statistics."""

    total_roms: int = 0
    total_size_bytes: int = 0
    total_systems: int = 0
    verified_roms: int = 0
    unknown_roms: int = 0
    duplicate_count: int = 0

    systems: Dict[str, SystemStats] = field(default_factory=dict)
    regions_overall: Dict[str, int] = field(default_factory=dict)
    years_overall: Dict[int, int] = field(default_factory=dict)
    genres_overall: Dict[str, int] = field(default_factory=dict)

    scan_timestamp: Optional[float] = None
    scan_duration_seconds: float = 0.0

    @property
    def total_size_gb(self) -> float:
        """Total size in GB."""
        return self.total_size_bytes / (1024 * 1024 * 1024)

    @property
    def verification_rate(self) -> float:
        """Overall verification rate."""
        if self.total_roms == 0:
            return 0.0
        return (self.verified_roms / self.total_roms) * 100

    @property
    def scan_date(self) -> Optional[datetime]:
        """Scan datetime."""
        if self.scan_timestamp:
            return datetime.fromtimestamp(self.scan_timestamp)
        return None


class CollectionDashboard:
    """Collection statistics dashboard.

    Implements F91: Sammlungs-Statistiken-Dashboard

    Features:
    - System breakdown with counts/sizes
    - Region distribution
    - Year distribution
    - Genre distribution
    - Verification status
    """

    def __init__(self, cache_path: Optional[str] = None):
        """Initialize dashboard.

        Args:
            cache_path: Path to cache stats
        """
        self._cache_path = cache_path
        self._stats: Optional[CollectionStats] = None

    def analyze(
        self,
        roms: List[Dict[str, Any]],
        include_duplicates: bool = False,
    ) -> CollectionStats:
        """Analyze ROM collection.

        Args:
            roms: List of ROM dicts with metadata
            include_duplicates: Include duplicate count

        Returns:
            CollectionStats
        """
        import time

        start_time = time.time()

        stats = CollectionStats()
        stats.scan_timestamp = start_time

        seen_hashes: set = set()
        duplicates = 0

        for rom in roms:
            # Basic counts
            stats.total_roms += 1

            size = rom.get("size", 0)
            stats.total_size_bytes += size

            # System stats
            platform = rom.get("platform", "Unknown")
            if platform not in stats.systems:
                stats.systems[platform] = SystemStats(
                    name=platform,
                    display_name=rom.get("platform_display", platform),
                )

            sys_stats = stats.systems[platform]
            sys_stats.rom_count += 1
            sys_stats.total_size_bytes += size

            # Verification status
            if rom.get("verified", False):
                stats.verified_roms += 1
                sys_stats.verified_count += 1
            elif rom.get("status") == "unknown":
                stats.unknown_roms += 1
                sys_stats.unknown_count += 1

            # Region
            region = rom.get("region", "Unknown")
            stats.regions_overall[region] = stats.regions_overall.get(region, 0) + 1
            sys_stats.regions[region] = sys_stats.regions.get(region, 0) + 1

            # Year
            year = rom.get("year") or rom.get("release_year")
            if year:
                try:
                    year_int = int(year)
                    stats.years_overall[year_int] = stats.years_overall.get(year_int, 0) + 1
                    sys_stats.years[year_int] = sys_stats.years.get(year_int, 0) + 1
                except ValueError:
                    pass

            # Genre
            genre = rom.get("genre", "")
            if genre:
                stats.genres_overall[genre] = stats.genres_overall.get(genre, 0) + 1
                sys_stats.genres[genre] = sys_stats.genres.get(genre, 0) + 1

            # File type
            extension = Path(rom.get("path", "")).suffix.lower()
            sys_stats.file_types[extension] = sys_stats.file_types.get(extension, 0) + 1

            # Duplicate detection
            if include_duplicates:
                rom_hash = rom.get("hash") or rom.get("crc32") or rom.get("sha1")
                if rom_hash:
                    if rom_hash in seen_hashes:
                        duplicates += 1
                    else:
                        seen_hashes.add(rom_hash)

        stats.total_systems = len(stats.systems)
        stats.duplicate_count = duplicates
        stats.scan_duration_seconds = time.time() - start_time

        self._stats = stats

        if self._cache_path:
            self._save_cache()

        return stats

    def get_system_ranking(
        self,
        by: str = "count",
        limit: int = 10,
    ) -> List[Tuple[str, int]]:
        """Get systems ranked by count or size.

        Args:
            by: 'count' or 'size'
            limit: Max results

        Returns:
            List of (system_name, value)
        """
        if not self._stats:
            return []

        if by == "size":
            items = [
                (name, sys.total_size_bytes)
                for name, sys in self._stats.systems.items()
            ]
        else:
            items = [
                (name, sys.rom_count)
                for name, sys in self._stats.systems.items()
            ]

        return sorted(items, key=lambda x: x[1], reverse=True)[:limit]

    def get_region_distribution(self) -> Dict[str, float]:
        """Get region distribution as percentages.

        Returns:
            Dict of region -> percentage
        """
        if not self._stats or not self._stats.regions_overall:
            return {}

        total = sum(self._stats.regions_overall.values())
        return {
            region: (count / total) * 100
            for region, count in self._stats.regions_overall.items()
        }

    def get_year_distribution(
        self,
        start_year: int = 1980,
        end_year: int = 2025,
    ) -> Dict[int, int]:
        """Get year distribution.

        Args:
            start_year: Start year filter
            end_year: End year filter

        Returns:
            Dict of year -> count
        """
        if not self._stats:
            return {}

        return {
            year: count
            for year, count in self._stats.years_overall.items()
            if start_year <= year <= end_year
        }

    def get_decade_summary(self) -> Dict[str, int]:
        """Get ROMs grouped by decade.

        Returns:
            Dict of decade -> count
        """
        if not self._stats:
            return {}

        decades: Dict[str, int] = {}
        for year, count in self._stats.years_overall.items():
            decade = f"{(year // 10) * 10}s"
            decades[decade] = decades.get(decade, 0) + count

        return dict(sorted(decades.items()))

    def get_genre_distribution(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get top genres.

        Args:
            limit: Max results

        Returns:
            List of (genre, count)
        """
        if not self._stats:
            return []

        return sorted(
            self._stats.genres_overall.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:limit]

    def generate_summary_text(self) -> str:
        """Generate text summary of collection.

        Returns:
            Summary text
        """
        if not self._stats:
            return "No collection data available."

        lines = [
            "═══════════════════════════════════════════════════",
            "           ROM COLLECTION SUMMARY",
            "═══════════════════════════════════════════════════",
            "",
            f"📊 Total ROMs: {self._stats.total_roms:,}",
            f"💾 Total Size: {self._stats.total_size_gb:.2f} GB",
            f"🎮 Systems: {self._stats.total_systems}",
            f"✅ Verified: {self._stats.verified_roms:,} ({self._stats.verification_rate:.1f}%)",
            f"❓ Unknown: {self._stats.unknown_roms:,}",
            "",
            "───────────────────────────────────────────────────",
            "          TOP SYSTEMS BY COUNT",
            "───────────────────────────────────────────────────",
        ]

        for name, count in self.get_system_ranking("count", 5):
            sys_stats = self._stats.systems.get(name)
            if sys_stats:
                lines.append(f"  {name}: {count:,} ROMs ({sys_stats.total_size_gb:.1f} GB)")

        lines.extend([
            "",
            "───────────────────────────────────────────────────",
            "          REGION DISTRIBUTION",
            "───────────────────────────────────────────────────",
        ])

        for region, pct in sorted(
            self.get_region_distribution().items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]:
            bar_len = int(pct / 5)
            bar = "█" * bar_len
            lines.append(f"  {region}: {bar} {pct:.1f}%")

        lines.extend([
            "",
            "───────────────────────────────────────────────────",
            "          DECADES",
            "───────────────────────────────────────────────────",
        ])

        for decade, count in self.get_decade_summary().items():
            lines.append(f"  {decade}: {count:,} ROMs")

        lines.append("")
        lines.append("═══════════════════════════════════════════════════")

        if self._stats.scan_date:
            lines.append(f"Generated: {self._stats.scan_date.strftime('%Y-%m-%d %H:%M')}")

        return "\n".join(lines)

    def export_json(self, path: str) -> bool:
        """Export stats as JSON.

        Args:
            path: Output path

        Returns:
            True if exported
        """
        if not self._stats:
            return False

        data = {
            "total_roms": self._stats.total_roms,
            "total_size_bytes": self._stats.total_size_bytes,
            "total_size_gb": self._stats.total_size_gb,
            "total_systems": self._stats.total_systems,
            "verified_roms": self._stats.verified_roms,
            "unknown_roms": self._stats.unknown_roms,
            "verification_rate": self._stats.verification_rate,
            "scan_timestamp": self._stats.scan_timestamp,
            "systems": {
                name: {
                    "rom_count": sys.rom_count,
                    "total_size_gb": sys.total_size_gb,
                    "verified_count": sys.verified_count,
                    "regions": sys.regions,
                    "file_types": sys.file_types,
                }
                for name, sys in self._stats.systems.items()
            },
            "regions": self._stats.regions_overall,
            "years": {str(k): v for k, v in self._stats.years_overall.items()},
            "genres": self._stats.genres_overall,
        }

        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False

    def _save_cache(self) -> None:
        """Save stats to cache."""
        if self._cache_path and self._stats:
            self.export_json(self._cache_path)

    def load_cache(self) -> bool:
        """Load stats from cache.

        Returns:
            True if loaded
        """
        if not self._cache_path or not Path(self._cache_path).exists():
            return False

        try:
            with open(self._cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Reconstruct stats
            self._stats = CollectionStats(
                total_roms=data.get("total_roms", 0),
                total_size_bytes=data.get("total_size_bytes", 0),
                total_systems=data.get("total_systems", 0),
                verified_roms=data.get("verified_roms", 0),
                unknown_roms=data.get("unknown_roms", 0),
                scan_timestamp=data.get("scan_timestamp"),
            )

            self._stats.regions_overall = data.get("regions", {})
            self._stats.years_overall = {
                int(k): v for k, v in data.get("years", {}).items()
            }
            self._stats.genres_overall = data.get("genres", {})

            # Reconstruct system stats
            for name, sys_data in data.get("systems", {}).items():
                self._stats.systems[name] = SystemStats(
                    name=name,
                    display_name=name,
                    rom_count=sys_data.get("rom_count", 0),
                    total_size_bytes=int(sys_data.get("total_size_gb", 0) * 1024 * 1024 * 1024),
                    verified_count=sys_data.get("verified_count", 0),
                    regions=sys_data.get("regions", {}),
                    file_types=sys_data.get("file_types", {}),
                )

            return True
        except Exception:
            return False

    @property
    def stats(self) -> Optional[CollectionStats]:
        """Get current stats."""
        return self._stats
