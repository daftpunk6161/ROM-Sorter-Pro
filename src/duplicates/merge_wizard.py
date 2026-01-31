"""Duplicate Merge Wizard - F77 Implementation.

Intelligent merging of duplicate ROM files with configurable strategies.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from .hash_duplicate_finder import DuplicateGroup, DuplicateEntry
from .fuzzy_duplicate_finder import FuzzyGroup, FuzzyMatch


class MergeStrategy(Enum):
    """Strategy for selecting which duplicate to keep."""

    KEEP_FIRST = auto()  # Keep first file alphabetically
    KEEP_LARGEST = auto()  # Keep largest file
    KEEP_SMALLEST = auto()  # Keep smallest file
    KEEP_VERIFIED = auto()  # Keep [!] verified if available
    KEEP_USA = auto()  # Prefer USA region
    KEEP_EUROPE = auto()  # Prefer Europe region
    KEEP_JAPAN = auto()  # Prefer Japan region
    KEEP_SHORTEST_PATH = auto()  # Keep file with shortest path
    KEEP_NEWEST = auto()  # Keep most recently modified
    KEEP_OLDEST = auto()  # Keep oldest file
    MANUAL = auto()  # User selects manually


class MergeAction(Enum):
    """Action to take for duplicate files."""

    DELETE = auto()  # Delete duplicate files
    MOVE = auto()  # Move duplicates to a folder
    SYMLINK = auto()  # Replace with symlinks (where supported)
    HARDLINK = auto()  # Replace with hardlinks (same filesystem)
    NONE = auto()  # Just report, no action


@dataclass
class MergeDecision:
    """A decision for a specific duplicate group."""

    group_id: str
    keep_path: str
    remove_paths: List[str] = field(default_factory=list)
    action: MergeAction = MergeAction.NONE
    strategy_used: MergeStrategy = MergeStrategy.KEEP_FIRST
    reason: str = ""


@dataclass
class MergeResult:
    """Result of a merge operation."""

    total_groups: int = 0
    processed_groups: int = 0
    files_kept: int = 0
    files_removed: int = 0
    files_moved: int = 0
    files_linked: int = 0
    bytes_reclaimed: int = 0
    errors: List[str] = field(default_factory=list)
    decisions: List[MergeDecision] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class MergeWizard:
    """Wizard for merging duplicate ROMs.

    Implements F77: Duplikat-Merge-Wizard

    Supports multiple strategies and actions for handling duplicates.
    """

    # Region priority for KEEP_USA, KEEP_EUROPE, KEEP_JAPAN strategies
    REGION_PRIORITY_USA = ["USA", "World", "Europe", "Japan", "Unknown"]
    REGION_PRIORITY_EUR = ["Europe", "World", "USA", "Japan", "Unknown"]
    REGION_PRIORITY_JPN = ["Japan", "World", "USA", "Europe", "Unknown"]

    def __init__(
        self,
        strategy: MergeStrategy = MergeStrategy.KEEP_VERIFIED,
        action: MergeAction = MergeAction.NONE,
        move_target: Optional[str] = None,
    ):
        """Initialize merge wizard.

        Args:
            strategy: Strategy for selecting files to keep
            action: Action to take with duplicates
            move_target: Target directory for MOVE action
        """
        self.strategy = strategy
        self.action = action
        self.move_target = move_target

    def plan_merge(
        self,
        groups: List[DuplicateGroup],
        *,
        cancel_event: Optional[object] = None,
    ) -> List[MergeDecision]:
        """Create merge plan for hash-duplicate groups.

        Args:
            groups: List of DuplicateGroups from HashDuplicateFinder
            cancel_event: Cancellation event

        Returns:
            List of MergeDecisions (dry-run, no changes made)
        """
        decisions: List[MergeDecision] = []

        for idx, group in enumerate(groups):
            if _is_cancelled(cancel_event):
                break

            if len(group.entries) < 2:
                continue

            # Select file to keep
            keep_entry = self._select_keep_entry(group.entries)
            remove_entries = [e for e in group.entries if e.file_path != keep_entry.file_path]

            decision = MergeDecision(
                group_id=f"hash_{idx}_{group.hash_value[:8]}",
                keep_path=keep_entry.file_path,
                remove_paths=[e.file_path for e in remove_entries],
                action=self.action,
                strategy_used=self.strategy,
                reason=f"Selected by {self.strategy.name}",
            )
            decisions.append(decision)

        return decisions

    def plan_fuzzy_merge(
        self,
        groups: List[FuzzyGroup],
        *,
        cancel_event: Optional[object] = None,
    ) -> List[MergeDecision]:
        """Create merge plan for fuzzy-duplicate groups.

        Args:
            groups: List of FuzzyGroups from FuzzyDuplicateFinder
            cancel_event: Cancellation event

        Returns:
            List of MergeDecisions
        """
        decisions: List[MergeDecision] = []

        for idx, group in enumerate(groups):
            if _is_cancelled(cancel_event):
                break

            if len(group.files) < 2:
                continue

            # Convert to entries for selection
            entries = [
                DuplicateEntry(
                    file_path=f,
                    file_size=_get_file_size(f),
                )
                for f in group.files
            ]

            keep_entry = self._select_keep_entry(entries)
            remove_paths = [f for f in group.files if f != keep_entry.file_path]

            decision = MergeDecision(
                group_id=f"fuzzy_{idx}_{group.base_name[:20]}",
                keep_path=keep_entry.file_path,
                remove_paths=remove_paths,
                action=self.action,
                strategy_used=self.strategy,
                reason=f"Fuzzy match: {group.base_name}",
            )
            decisions.append(decision)

        return decisions

    def execute_merge(
        self,
        decisions: List[MergeDecision],
        *,
        dry_run: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_event: Optional[object] = None,
    ) -> MergeResult:
        """Execute merge decisions.

        Args:
            decisions: List of MergeDecisions from plan_merge()
            dry_run: If True, only simulate (no actual changes)
            progress_callback: Progress callback
            cancel_event: Cancellation event

        Returns:
            MergeResult with statistics
        """
        result = MergeResult(
            total_groups=len(decisions),
            decisions=decisions,
        )

        total = sum(len(d.remove_paths) for d in decisions)
        current = 0

        for decision in decisions:
            if _is_cancelled(cancel_event):
                break

            result.files_kept += 1

            for remove_path in decision.remove_paths:
                current += 1

                if progress_callback:
                    progress_callback(current, total, f"Processing: {remove_path}")

                if dry_run:
                    result.files_removed += 1
                    result.bytes_reclaimed += _get_file_size(remove_path)
                    continue

                try:
                    if decision.action == MergeAction.DELETE:
                        Path(remove_path).unlink()
                        result.files_removed += 1
                        result.bytes_reclaimed += _get_file_size(remove_path)

                    elif decision.action == MergeAction.MOVE:
                        if self.move_target:
                            dest = Path(self.move_target) / Path(remove_path).name
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(remove_path, str(dest))
                            result.files_moved += 1

                    elif decision.action == MergeAction.SYMLINK:
                        size = _get_file_size(remove_path)
                        Path(remove_path).unlink()
                        Path(remove_path).symlink_to(decision.keep_path)
                        result.files_linked += 1
                        result.bytes_reclaimed += size

                    elif decision.action == MergeAction.HARDLINK:
                        size = _get_file_size(remove_path)
                        Path(remove_path).unlink()
                        Path(remove_path).link_to(decision.keep_path)
                        result.files_linked += 1
                        result.bytes_reclaimed += size

                except OSError as e:
                    result.errors.append(f"Error processing {remove_path}: {e}")

            result.processed_groups += 1

        return result

    def _select_keep_entry(self, entries: List[DuplicateEntry]) -> DuplicateEntry:
        """Select which entry to keep based on strategy.

        Args:
            entries: List of duplicate entries

        Returns:
            Entry to keep
        """
        if not entries:
            raise ValueError("No entries to select from")

        if len(entries) == 1:
            return entries[0]

        if self.strategy == MergeStrategy.KEEP_FIRST:
            return min(entries, key=lambda e: e.file_path.lower())

        elif self.strategy == MergeStrategy.KEEP_LARGEST:
            return max(entries, key=lambda e: e.file_size)

        elif self.strategy == MergeStrategy.KEEP_SMALLEST:
            return min(entries, key=lambda e: e.file_size)

        elif self.strategy == MergeStrategy.KEEP_VERIFIED:
            # Look for [!] in filename
            for entry in entries:
                if "[!]" in entry.filename:
                    return entry
            # Fallback to first
            return min(entries, key=lambda e: e.file_path.lower())

        elif self.strategy == MergeStrategy.KEEP_USA:
            return self._select_by_region(entries, self.REGION_PRIORITY_USA)

        elif self.strategy == MergeStrategy.KEEP_EUROPE:
            return self._select_by_region(entries, self.REGION_PRIORITY_EUR)

        elif self.strategy == MergeStrategy.KEEP_JAPAN:
            return self._select_by_region(entries, self.REGION_PRIORITY_JPN)

        elif self.strategy == MergeStrategy.KEEP_SHORTEST_PATH:
            return min(entries, key=lambda e: len(e.file_path))

        elif self.strategy == MergeStrategy.KEEP_NEWEST:
            return max(entries, key=lambda e: _get_mtime(e.file_path))

        elif self.strategy == MergeStrategy.KEEP_OLDEST:
            return min(entries, key=lambda e: _get_mtime(e.file_path))

        else:
            # Default / MANUAL - return first
            return entries[0]

    def _select_by_region(
        self, entries: List[DuplicateEntry], priority: List[str]
    ) -> DuplicateEntry:
        """Select entry by region priority.

        Args:
            entries: Entries to select from
            priority: Region priority list

        Returns:
            Selected entry
        """
        from .fuzzy_duplicate_finder import _detect_region

        # Group by region
        by_region: Dict[str, List[DuplicateEntry]] = {}
        for entry in entries:
            region = _detect_region(entry.filename)
            if region not in by_region:
                by_region[region] = []
            by_region[region].append(entry)

        # Select by priority
        for region in priority:
            if region in by_region:
                # Return first from this region (alphabetically)
                return min(by_region[region], key=lambda e: e.file_path.lower())

        # Fallback
        return min(entries, key=lambda e: e.file_path.lower())


def _get_file_size(path: str) -> int:
    """Get file size safely."""
    try:
        return Path(path).stat().st_size
    except OSError:
        return 0


def _get_mtime(path: str) -> float:
    """Get file modification time safely."""
    try:
        return Path(path).stat().st_mtime
    except OSError:
        return 0.0


def _is_cancelled(cancel_event: Optional[object]) -> bool:
    """Check if operation should be cancelled."""
    if cancel_event and hasattr(cancel_event, "is_set"):
        return cancel_event.is_set()  # type: ignore
    return False


def auto_merge_duplicates(
    groups: List[DuplicateGroup],
    strategy: MergeStrategy = MergeStrategy.KEEP_VERIFIED,
    action: MergeAction = MergeAction.NONE,
    dry_run: bool = True,
    **kwargs: object,
) -> MergeResult:
    """Convenience function to auto-merge duplicates.

    Args:
        groups: DuplicateGroups to merge
        strategy: Selection strategy
        action: Merge action
        dry_run: Simulate only
        **kwargs: Additional arguments

    Returns:
        MergeResult
    """
    wizard = MergeWizard(strategy=strategy, action=action)
    decisions = wizard.plan_merge(groups)
    return wizard.execute_merge(decisions, dry_run=dry_run, **kwargs)  # type: ignore[arg-type]
