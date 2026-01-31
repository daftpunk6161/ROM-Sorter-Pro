"""Collection Completeness Tracker - F66 Implementation.

Tracks collection completeness against DAT files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class SystemCompleteness:
    """Completeness stats for a single system."""

    system: str
    total_in_dat: int = 0
    owned_count: int = 0
    verified_count: int = 0  # Hash-verified matches
    missing_count: int = 0
    extra_count: int = 0  # Not in DAT
    percentage: float = 0.0

    # Lists of game names
    owned: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    verified: List[str] = field(default_factory=list)
    extra: List[str] = field(default_factory=list)


@dataclass
class CompletenessReport:
    """Full completeness report."""

    generated: datetime = field(default_factory=datetime.now)
    total_systems: int = 0
    total_in_dats: int = 0
    total_owned: int = 0
    total_verified: int = 0
    overall_percentage: float = 0.0
    systems: Dict[str, SystemCompleteness] = field(default_factory=dict)


class CompletenessTracker:
    """Collection completeness tracker.

    Implements F66: Collection-Completeness-Tracker

    Features:
    - Per-system completion percentage
    - Missing games list
    - DAT-based verification
    - Progress over time
    """

    CACHE_FILENAME = "completeness_cache.json"
    HISTORY_FILENAME = "completeness_history.json"

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        dat_index: Optional[Any] = None,
    ):
        """Initialize completeness tracker.

        Args:
            cache_dir: Cache directory
            dat_index: DAT index for lookups
        """
        self._cache_dir = Path(cache_dir) if cache_dir else Path("cache")
        self._dat_index = dat_index
        self._report: Optional[CompletenessReport] = None
        self._history: List[Dict[str, Any]] = []

        self._load_history()

    def _load_history(self) -> None:
        """Load history from file."""
        history_file = self._cache_dir / self.HISTORY_FILENAME

        if not history_file.exists():
            return

        try:
            with open(history_file, "r", encoding="utf-8") as f:
                self._history = json.load(f)
        except Exception:
            self._history = []

    def _save_history(self) -> None:
        """Save history to file."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        history_file = self._cache_dir / self.HISTORY_FILENAME

        # Keep last 100 entries
        history = self._history[-100:]

        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

    def _save_cache(self, report: CompletenessReport) -> None:
        """Save report to cache."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self._cache_dir / self.CACHE_FILENAME

        data = {
            "generated": report.generated.isoformat(),
            "total_systems": report.total_systems,
            "total_in_dats": report.total_in_dats,
            "total_owned": report.total_owned,
            "total_verified": report.total_verified,
            "overall_percentage": report.overall_percentage,
            "systems": {
                name: {
                    "system": sys.system,
                    "total_in_dat": sys.total_in_dat,
                    "owned_count": sys.owned_count,
                    "verified_count": sys.verified_count,
                    "missing_count": sys.missing_count,
                    "extra_count": sys.extra_count,
                    "percentage": sys.percentage,
                    "owned": sys.owned[:1000],  # Limit for cache
                    "missing": sys.missing[:1000],
                    "verified": sys.verified[:1000],
                    "extra": sys.extra[:1000],
                }
                for name, sys in report.systems.items()
            },
        }

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load_cache(self) -> Optional[CompletenessReport]:
        """Load report from cache."""
        cache_file = self._cache_dir / self.CACHE_FILENAME

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            report = CompletenessReport(
                generated=datetime.fromisoformat(data["generated"]),
                total_systems=data["total_systems"],
                total_in_dats=data["total_in_dats"],
                total_owned=data["total_owned"],
                total_verified=data["total_verified"],
                overall_percentage=data["overall_percentage"],
            )

            for name, sys_data in data.get("systems", {}).items():
                report.systems[name] = SystemCompleteness(
                    system=sys_data["system"],
                    total_in_dat=sys_data["total_in_dat"],
                    owned_count=sys_data["owned_count"],
                    verified_count=sys_data["verified_count"],
                    missing_count=sys_data["missing_count"],
                    extra_count=sys_data["extra_count"],
                    percentage=sys_data["percentage"],
                    owned=sys_data.get("owned", []),
                    missing=sys_data.get("missing", []),
                    verified=sys_data.get("verified", []),
                    extra=sys_data.get("extra", []),
                )

            return report

        except Exception:
            return None

    def calculate_completeness(
        self,
        collection: Dict[str, List[Dict[str, Any]]],
        dat_entries: Dict[str, List[Dict[str, Any]]],
    ) -> CompletenessReport:
        """Calculate completeness from collection and DAT data.

        Args:
            collection: Collection data by system {system: [{name, hash, ...}]}
            dat_entries: DAT entries by system {system: [{name, hash, ...}]}

        Returns:
            CompletenessReport
        """
        report = CompletenessReport()

        for system, dat_games in dat_entries.items():
            sys_comp = SystemCompleteness(system=system)

            # Build sets for comparison
            dat_names: Set[str] = set()
            dat_hashes: Set[str] = set()

            for game in dat_games:
                name = game.get("name", "")
                if name:
                    dat_names.add(name.lower())
                for h in ["sha1", "md5", "crc32"]:
                    if game.get(h):
                        dat_hashes.add(game[h].lower())

            sys_comp.total_in_dat = len(dat_names)

            # Check collection
            owned_names: Set[str] = set()
            verified_names: Set[str] = set()
            extra_names: Set[str] = set()

            collection_games = collection.get(system, [])
            for game in collection_games:
                name = game.get("name", "")
                name_lower = name.lower() if name else ""

                # Check hash match (verified)
                hash_match = False
                for h in ["sha1", "md5", "crc32"]:
                    if game.get(h) and game[h].lower() in dat_hashes:
                        hash_match = True
                        break

                if hash_match:
                    verified_names.add(name)
                    owned_names.add(name_lower)
                elif name_lower in dat_names:
                    owned_names.add(name_lower)
                else:
                    extra_names.add(name)

            # Calculate missing
            missing_names = dat_names - owned_names

            sys_comp.owned_count = len(owned_names)
            sys_comp.verified_count = len(verified_names)
            sys_comp.missing_count = len(missing_names)
            sys_comp.extra_count = len(extra_names)

            if sys_comp.total_in_dat > 0:
                sys_comp.percentage = (
                    sys_comp.owned_count / sys_comp.total_in_dat
                ) * 100

            # Store lists
            sys_comp.owned = sorted(owned_names)
            sys_comp.verified = sorted(verified_names)
            sys_comp.missing = sorted(missing_names)
            sys_comp.extra = sorted(extra_names)

            report.systems[system] = sys_comp

        # Calculate totals
        report.total_systems = len(report.systems)
        report.total_in_dats = sum(s.total_in_dat for s in report.systems.values())
        report.total_owned = sum(s.owned_count for s in report.systems.values())
        report.total_verified = sum(s.verified_count for s in report.systems.values())

        if report.total_in_dats > 0:
            report.overall_percentage = (
                report.total_owned / report.total_in_dats
            ) * 100

        self._report = report
        self._save_cache(report)
        self._add_to_history(report)

        return report

    def _add_to_history(self, report: CompletenessReport) -> None:
        """Add report to history."""
        entry = {
            "timestamp": report.generated.isoformat(),
            "total_owned": report.total_owned,
            "total_in_dats": report.total_in_dats,
            "overall_percentage": report.overall_percentage,
            "systems": {
                name: {"percentage": sys.percentage, "owned": sys.owned_count}
                for name, sys in report.systems.items()
            },
        }

        self._history.append(entry)
        self._save_history()

    def get_report(self, use_cache: bool = True) -> Optional[CompletenessReport]:
        """Get completeness report.

        Args:
            use_cache: Whether to use cached report

        Returns:
            CompletenessReport or None
        """
        if self._report:
            return self._report

        if use_cache:
            return self._load_cache()

        return None

    def get_system_completeness(self, system: str) -> Optional[SystemCompleteness]:
        """Get completeness for a specific system.

        Args:
            system: System name

        Returns:
            SystemCompleteness or None
        """
        report = self.get_report()
        if report and system in report.systems:
            return report.systems[system]
        return None

    def get_missing_games(
        self, system: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get list of missing games.

        Args:
            system: Optional system filter
            limit: Maximum results

        Returns:
            List of missing games
        """
        report = self.get_report()
        if not report:
            return []

        missing = []

        if system:
            if system in report.systems:
                sys_comp = report.systems[system]
                for name in sys_comp.missing[:limit]:
                    missing.append({"system": system, "name": name})
        else:
            for sys_name, sys_comp in report.systems.items():
                for name in sys_comp.missing:
                    missing.append({"system": sys_name, "name": name})
                    if len(missing) >= limit:
                        break
                if len(missing) >= limit:
                    break

        return missing

    def get_progress_over_time(
        self, system: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get progress history.

        Args:
            system: Optional system filter

        Returns:
            List of progress entries
        """
        result = []

        for entry in self._history:
            if system:
                if system in entry.get("systems", {}):
                    result.append(
                        {
                            "timestamp": entry["timestamp"],
                            "percentage": entry["systems"][system]["percentage"],
                            "owned": entry["systems"][system]["owned"],
                        }
                    )
            else:
                result.append(
                    {
                        "timestamp": entry["timestamp"],
                        "percentage": entry["overall_percentage"],
                        "owned": entry["total_owned"],
                    }
                )

        return result

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics.

        Returns:
            Summary dict
        """
        report = self.get_report()
        if not report:
            return {
                "has_data": False,
                "message": "No completeness data. Run a scan first.",
            }

        # Sort by percentage
        sorted_systems = sorted(
            report.systems.values(), key=lambda s: s.percentage, reverse=True
        )

        return {
            "has_data": True,
            "generated": report.generated.isoformat(),
            "overall_percentage": round(report.overall_percentage, 1),
            "total_owned": report.total_owned,
            "total_in_dats": report.total_in_dats,
            "total_missing": report.total_in_dats - report.total_owned,
            "total_verified": report.total_verified,
            "total_systems": report.total_systems,
            "top_systems": [
                {
                    "system": s.system,
                    "percentage": round(s.percentage, 1),
                    "owned": s.owned_count,
                    "total": s.total_in_dat,
                }
                for s in sorted_systems[:5]
            ],
            "bottom_systems": [
                {
                    "system": s.system,
                    "percentage": round(s.percentage, 1),
                    "owned": s.owned_count,
                    "total": s.total_in_dat,
                }
                for s in sorted_systems[-5:]
            ],
        }

    def export_missing_list(
        self,
        output_path: str,
        system: Optional[str] = None,
        format: str = "txt",
    ) -> bool:
        """Export missing games list.

        Args:
            output_path: Output file path
            system: Optional system filter
            format: Output format (txt, json, csv)

        Returns:
            True if successful
        """
        report = self.get_report()
        if not report:
            return False

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        missing = self.get_missing_games(system, limit=10000)

        try:
            if format == "json":
                with open(output, "w", encoding="utf-8") as f:
                    json.dump(missing, f, indent=2)

            elif format == "csv":
                import csv

                with open(output, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["system", "name"])
                    writer.writeheader()
                    writer.writerows(missing)

            else:  # txt
                with open(output, "w", encoding="utf-8") as f:
                    if system:
                        f.write(f"Missing ROMs for {system}\n")
                        f.write("=" * 50 + "\n\n")
                        for item in missing:
                            f.write(f"{item['name']}\n")
                    else:
                        current_sys = None
                        for item in missing:
                            if item["system"] != current_sys:
                                if current_sys:
                                    f.write("\n")
                                current_sys = item["system"]
                                f.write(f"=== {current_sys} ===\n")
                            f.write(f"  {item['name']}\n")

            return True

        except Exception:
            return False

    def render_progress_bar(
        self, system: str, width: int = 30
    ) -> str:
        """Render ASCII progress bar for system.

        Args:
            system: System name
            width: Bar width in characters

        Returns:
            Progress bar string
        """
        sys_comp = self.get_system_completeness(system)
        if not sys_comp:
            return f"{system}: No data"

        filled = int((sys_comp.percentage / 100) * width)
        empty = width - filled
        bar = "█" * filled + "░" * empty

        return (
            f"{system}\n"
            f"{bar}  {sys_comp.percentage:.1f}% "
            f"({sys_comp.owned_count:,} / {sys_comp.total_in_dat:,})"
        )

    def render_all_progress(self, width: int = 30) -> str:
        """Render progress bars for all systems.

        Args:
            width: Bar width

        Returns:
            Multi-line progress display
        """
        report = self.get_report()
        if not report:
            return "No completeness data available."

        lines = ["📊 Collection Completeness", "=" * 50, ""]

        sorted_systems = sorted(
            report.systems.values(), key=lambda s: s.percentage, reverse=True
        )

        for sys_comp in sorted_systems:
            filled = int((sys_comp.percentage / 100) * width)
            empty = width - filled
            bar = "█" * filled + "░" * empty

            lines.append(f"{sys_comp.system}")
            lines.append(
                f"{bar}  {sys_comp.percentage:.1f}% "
                f"({sys_comp.owned_count:,} / {sys_comp.total_in_dat:,})"
            )
            lines.append("")

        lines.append("=" * 50)
        lines.append(
            f"Overall: {report.overall_percentage:.1f}% "
            f"({report.total_owned:,} / {report.total_in_dats:,})"
        )

        return "\n".join(lines)
