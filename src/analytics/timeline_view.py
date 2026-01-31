"""Timeline View - F93 Implementation.

Visualizes ROMs by release year.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TimelinePeriod(Enum):
    """Timeline grouping period."""

    YEAR = "year"
    DECADE = "decade"
    ERA = "era"  # e.g., 8-bit, 16-bit, 3D


@dataclass
class TimelineEntry:
    """A single timeline entry."""

    year: int
    rom_count: int = 0
    total_size_bytes: int = 0
    platforms: Dict[str, int] = field(default_factory=dict)
    genres: Dict[str, int] = field(default_factory=dict)
    top_roms: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def display_label(self) -> str:
        """Get display label."""
        return str(self.year)


@dataclass
class TimelineDecade:
    """Decade grouping."""

    decade: str  # e.g., "1990s"
    start_year: int
    end_year: int
    rom_count: int = 0
    total_size_bytes: int = 0
    platforms: Dict[str, int] = field(default_factory=dict)
    entries: List[TimelineEntry] = field(default_factory=list)


@dataclass
class TimelineEra:
    """Gaming era grouping."""

    name: str
    description: str
    start_year: int
    end_year: int
    rom_count: int = 0
    platforms: List[str] = field(default_factory=list)


# Gaming era definitions
GAMING_ERAS = [
    TimelineEra(
        name="8-bit Era",
        description="NES, Master System, early computers",
        start_year=1983,
        end_year=1989,
        platforms=["nes", "sms", "c64", "atari7800"],
    ),
    TimelineEra(
        name="16-bit Era",
        description="SNES, Genesis, TurboGrafx",
        start_year=1988,
        end_year=1995,
        platforms=["snes", "genesis", "pce", "neogeo"],
    ),
    TimelineEra(
        name="32/64-bit Era",
        description="PlayStation, N64, Saturn",
        start_year=1994,
        end_year=2001,
        platforms=["psx", "n64", "saturn", "3do"],
    ),
    TimelineEra(
        name="6th Generation",
        description="PS2, Dreamcast, GameCube, Xbox",
        start_year=1998,
        end_year=2006,
        platforms=["ps2", "dc", "gc", "xbox"],
    ),
    TimelineEra(
        name="7th Generation",
        description="PS3, Wii, Xbox 360",
        start_year=2005,
        end_year=2013,
        platforms=["ps3", "wii", "xbox360"],
    ),
    TimelineEra(
        name="Handheld Golden Age",
        description="Game Boy to DS era",
        start_year=1989,
        end_year=2010,
        platforms=["gb", "gbc", "gba", "nds", "psp"],
    ),
]


class TimelineView:
    """Timeline visualization for ROM collections.

    Implements F93: Timeline-View

    Features:
    - Year-by-year breakdown
    - Decade grouping
    - Gaming era classification
    - Platform trends
    """

    def __init__(self):
        """Initialize timeline view."""
        self._entries: Dict[int, TimelineEntry] = {}
        self._roms: List[Dict[str, Any]] = []

    def analyze(self, roms: List[Dict[str, Any]]) -> Dict[int, TimelineEntry]:
        """Analyze ROMs and build timeline.

        Args:
            roms: List of ROM dicts with 'year' or 'release_year'

        Returns:
            Dict of year -> TimelineEntry
        """
        self._roms = roms
        self._entries.clear()

        for rom in roms:
            year = self._extract_year(rom)
            if not year:
                continue

            if year not in self._entries:
                self._entries[year] = TimelineEntry(year=year)

            entry = self._entries[year]
            entry.rom_count += 1
            entry.total_size_bytes += rom.get("size", 0)

            # Track platform
            platform = rom.get("platform", "unknown")
            entry.platforms[platform] = entry.platforms.get(platform, 0) + 1

            # Track genre
            genre = rom.get("genre", "")
            if genre:
                entry.genres[genre] = entry.genres.get(genre, 0) + 1

            # Track top ROMs (by some metric, e.g., rating or just first seen)
            if len(entry.top_roms) < 10:
                entry.top_roms.append({
                    "name": rom.get("name", ""),
                    "platform": platform,
                })

        return self._entries

    def _extract_year(self, rom: Dict[str, Any]) -> Optional[int]:
        """Extract year from ROM data."""
        year = rom.get("year") or rom.get("release_year") or rom.get("releasedate", "")

        if isinstance(year, int):
            return year if 1970 <= year <= 2030 else None

        if isinstance(year, str):
            # Try to parse various formats
            year_str = year.strip()

            # Full date format YYYYMMDD
            if len(year_str) >= 4:
                try:
                    return int(year_str[:4])
                except ValueError:
                    pass

            # Just year
            try:
                y = int(year_str)
                return y if 1970 <= y <= 2030 else None
            except ValueError:
                pass

        return None

    def get_year_range(self) -> Tuple[int, int]:
        """Get min/max years in collection.

        Returns:
            (min_year, max_year)
        """
        if not self._entries:
            return (1980, 2020)

        years = list(self._entries.keys())
        return (min(years), max(years))

    def get_entries_range(
        self,
        start_year: int,
        end_year: int,
    ) -> List[TimelineEntry]:
        """Get entries for year range.

        Args:
            start_year: Start year (inclusive)
            end_year: End year (inclusive)

        Returns:
            List of entries
        """
        entries = []
        for year in range(start_year, end_year + 1):
            if year in self._entries:
                entries.append(self._entries[year])
            else:
                # Empty year
                entries.append(TimelineEntry(year=year))

        return entries

    def get_by_decade(self) -> List[TimelineDecade]:
        """Group entries by decade.

        Returns:
            List of decade groupings
        """
        if not self._entries:
            return []

        min_year, max_year = self.get_year_range()
        start_decade = (min_year // 10) * 10
        end_decade = (max_year // 10) * 10

        decades = []

        for decade_start in range(start_decade, end_decade + 10, 10):
            decade = TimelineDecade(
                decade=f"{decade_start}s",
                start_year=decade_start,
                end_year=decade_start + 9,
            )

            for year in range(decade_start, decade_start + 10):
                if year in self._entries:
                    entry = self._entries[year]
                    decade.rom_count += entry.rom_count
                    decade.total_size_bytes += entry.total_size_bytes
                    decade.entries.append(entry)

                    for platform, count in entry.platforms.items():
                        decade.platforms[platform] = decade.platforms.get(platform, 0) + count

            if decade.rom_count > 0:
                decades.append(decade)

        return decades

    def get_by_era(self) -> List[Dict[str, Any]]:
        """Group entries by gaming era.

        Returns:
            List of era groupings with counts
        """
        results = []

        for era in GAMING_ERAS:
            era_data = {
                "name": era.name,
                "description": era.description,
                "start_year": era.start_year,
                "end_year": era.end_year,
                "rom_count": 0,
                "matching_platforms": [],
            }

            for year, entry in self._entries.items():
                if era.start_year <= year <= era.end_year:
                    era_data["rom_count"] += entry.rom_count

                    for platform in entry.platforms:
                        if platform.lower() in era.platforms:
                            if platform not in era_data["matching_platforms"]:
                                era_data["matching_platforms"].append(platform)

            results.append(era_data)

        return [r for r in results if r["rom_count"] > 0]

    def get_platform_trends(self) -> Dict[str, List[Tuple[int, int]]]:
        """Get platform popularity over time.

        Returns:
            Dict of platform -> [(year, count), ...]
        """
        trends: Dict[str, List[Tuple[int, int]]] = defaultdict(list)

        for year in sorted(self._entries.keys()):
            entry = self._entries[year]
            for platform, count in entry.platforms.items():
                trends[platform].append((year, count))

        return dict(trends)

    def get_peak_years(self, limit: int = 5) -> List[Tuple[int, int]]:
        """Get years with most ROMs.

        Args:
            limit: Max results

        Returns:
            List of (year, count)
        """
        if not self._entries:
            return []

        sorted_years = sorted(
            self._entries.items(),
            key=lambda x: x[1].rom_count,
            reverse=True,
        )

        return [(year, entry.rom_count) for year, entry in sorted_years[:limit]]

    def generate_ascii_chart(
        self,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        width: int = 60,
    ) -> str:
        """Generate ASCII bar chart of timeline.

        Args:
            start_year: Start year
            end_year: End year
            width: Chart width

        Returns:
            ASCII chart string
        """
        if not self._entries:
            return "No timeline data available."

        min_y, max_y = self.get_year_range()
        start = start_year or min_y
        end = end_year or max_y

        entries = self.get_entries_range(start, end)
        max_count = max((e.rom_count for e in entries), default=1)

        lines = [
            "Timeline View",
            "═" * width,
            "",
        ]

        for entry in entries:
            if entry.rom_count == 0:
                continue

            bar_len = int((entry.rom_count / max_count) * (width - 15))
            bar = "█" * bar_len

            lines.append(f"{entry.year} │{bar} {entry.rom_count:,}")

        lines.extend([
            "",
            "═" * width,
            f"Total: {sum(e.rom_count for e in entries):,} ROMs",
            f"Range: {start} - {end}",
        ])

        return "\n".join(lines)

    def export_data(self) -> Dict[str, Any]:
        """Export timeline data.

        Returns:
            Exportable dict
        """
        return {
            "year_range": self.get_year_range(),
            "total_roms": sum(e.rom_count for e in self._entries.values()),
            "entries": {
                year: {
                    "count": entry.rom_count,
                    "size_bytes": entry.total_size_bytes,
                    "platforms": entry.platforms,
                    "genres": entry.genres,
                }
                for year, entry in self._entries.items()
            },
            "decades": [
                {
                    "name": d.decade,
                    "count": d.rom_count,
                    "platforms": d.platforms,
                }
                for d in self.get_by_decade()
            ],
            "peak_years": self.get_peak_years(),
        }
