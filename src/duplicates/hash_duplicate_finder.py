"""Hash-based duplicate finder - F75 Implementation.

Finds exact duplicates based on file hashes (SHA1, CRC32).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from ..core.file_utils import calculate_file_hash
from ..hash_utils import calculate_crc32


@dataclass
class DuplicateEntry:
    """A single file in a duplicate group."""

    file_path: str
    file_size: int
    sha1: Optional[str] = None
    crc32: Optional[str] = None
    is_primary: bool = False  # Marked as the "keep" candidate
    platform_id: Optional[str] = None
    rom_name: Optional[str] = None

    @property
    def filename(self) -> str:
        """Get just the filename."""
        return Path(self.file_path).name


@dataclass
class DuplicateGroup:
    """A group of duplicate files (same hash)."""

    hash_value: str
    hash_type: str  # "sha1" or "crc32_size"
    entries: List[DuplicateEntry] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Number of duplicates in this group."""
        return len(self.entries)

    @property
    def wasted_bytes(self) -> int:
        """Bytes that could be reclaimed by keeping only one copy."""
        if len(self.entries) <= 1:
            return 0
        sizes = [e.file_size for e in self.entries]
        return sum(sizes) - min(sizes)  # Keep smallest, remove rest

    @property
    def primary(self) -> Optional[DuplicateEntry]:
        """Get the primary (keep) entry."""
        for e in self.entries:
            if e.is_primary:
                return e
        return self.entries[0] if self.entries else None

    def mark_primary(self, file_path: str) -> bool:
        """Mark a file as the primary (keep) entry.

        Args:
            file_path: Path to mark as primary

        Returns:
            True if found and marked
        """
        found = False
        for e in self.entries:
            if e.file_path == file_path:
                e.is_primary = True
                found = True
            else:
                e.is_primary = False
        return found

    def get_duplicates_to_remove(self) -> List[DuplicateEntry]:
        """Get entries that should be removed (not primary)."""
        primary = self.primary
        if not primary:
            return []
        return [e for e in self.entries if e.file_path != primary.file_path]


class HashDuplicateFinder:
    """Finds exact duplicate files by hash.

    Implements F75: Hash-Duplikat-Finder

    Two modes:
    1. SHA1 mode: Uses SHA1 hash for exact matching (most reliable)
    2. CRC32+size mode: Uses CRC32 + file size (faster, slightly less reliable)
    """

    def __init__(
        self,
        use_sha1: bool = True,
        use_crc32_fallback: bool = True,
        min_file_size: int = 0,
    ):
        """Initialize finder.

        Args:
            use_sha1: Use SHA1 hashing (slower but more reliable)
            use_crc32_fallback: Use CRC32+size if SHA1 not available
            min_file_size: Minimum file size to consider
        """
        self.use_sha1 = use_sha1
        self.use_crc32_fallback = use_crc32_fallback
        self.min_file_size = min_file_size

    def find_duplicates(
        self,
        paths: List[str],
        *,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_event: Optional[object] = None,
    ) -> List[DuplicateGroup]:
        """Find duplicate files in a list of paths.

        Args:
            paths: List of file paths to check
            progress_callback: Optional callback (current, total, file_path)
            cancel_event: Optional cancellation event

        Returns:
            List of DuplicateGroups containing 2+ identical files
        """
        # First pass: group by size (quick filter)
        size_groups: Dict[int, List[str]] = defaultdict(list)
        total = len(paths)

        for idx, path in enumerate(paths):
            if _is_cancelled(cancel_event):
                break

            if progress_callback:
                progress_callback(idx + 1, total, f"Size check: {path}")

            try:
                size = Path(path).stat().st_size
                if size >= self.min_file_size:
                    size_groups[size].append(path)
            except OSError:
                continue

        # Second pass: hash files with same size
        hash_groups: Dict[str, DuplicateGroup] = {}
        candidate_files = [
            path for paths_list in size_groups.values() if len(paths_list) > 1 for path in paths_list
        ]
        total_candidates = len(candidate_files)

        for idx, path in enumerate(candidate_files):
            if _is_cancelled(cancel_event):
                break

            if progress_callback:
                progress_callback(idx + 1, total_candidates, f"Hashing: {path}")

            entry = self._create_entry(path)
            if not entry:
                continue

            # Determine hash key
            if entry.sha1:
                hash_key = f"sha1:{entry.sha1}"
                hash_type = "sha1"
            elif entry.crc32 and self.use_crc32_fallback:
                hash_key = f"crc32_size:{entry.crc32}_{entry.file_size}"
                hash_type = "crc32_size"
            else:
                continue

            # Add to group
            if hash_key not in hash_groups:
                hash_groups[hash_key] = DuplicateGroup(
                    hash_value=entry.sha1 or entry.crc32 or "",
                    hash_type=hash_type,
                )
            hash_groups[hash_key].entries.append(entry)

        # Filter to only groups with 2+ entries
        duplicates = [g for g in hash_groups.values() if g.count >= 2]

        # Auto-mark primary (first entry by default)
        for group in duplicates:
            if group.entries:
                group.entries[0].is_primary = True

        return duplicates

    def find_duplicates_in_directory(
        self,
        directory: str,
        *,
        extensions: Optional[List[str]] = None,
        recursive: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_event: Optional[object] = None,
    ) -> List[DuplicateGroup]:
        """Find duplicates in a directory.

        Args:
            directory: Directory to scan
            extensions: File extensions to include
            recursive: Scan recursively
            progress_callback: Progress callback
            cancel_event: Cancellation event

        Returns:
            List of DuplicateGroups
        """
        if extensions is None:
            extensions = _default_rom_extensions()

        dir_path = Path(directory)
        if not dir_path.is_dir():
            return []

        # Collect files
        paths: List[str] = []
        pattern = "**/*" if recursive else "*"
        for ext in extensions:
            paths.extend(str(p) for p in dir_path.glob(f"{pattern}{ext}"))

        paths = sorted(set(paths))
        return self.find_duplicates(
            paths,
            progress_callback=progress_callback,
            cancel_event=cancel_event,
        )

    def _create_entry(self, path: str) -> Optional[DuplicateEntry]:
        """Create a DuplicateEntry for a file.

        Args:
            path: File path

        Returns:
            DuplicateEntry or None if file can't be read
        """
        try:
            file_path = Path(path)
            size = file_path.stat().st_size
        except OSError:
            return None

        entry = DuplicateEntry(
            file_path=path,
            file_size=size,
        )

        # Calculate hashes
        if self.use_sha1:
            entry.sha1 = calculate_file_hash(path, algorithm="sha1")

        if self.use_crc32_fallback and not entry.sha1:
            entry.crc32 = calculate_crc32(path)

        return entry


def find_duplicates(
    paths: List[str],
    use_sha1: bool = True,
    **kwargs: object,
) -> List[DuplicateGroup]:
    """Convenience function to find duplicates.

    Args:
        paths: List of file paths
        use_sha1: Use SHA1 hashing
        **kwargs: Additional arguments for find_duplicates()

    Returns:
        List of DuplicateGroups
    """
    finder = HashDuplicateFinder(use_sha1=use_sha1)
    return finder.find_duplicates(paths, **kwargs)  # type: ignore[arg-type]


def calculate_wasted_space(groups: List[DuplicateGroup]) -> int:
    """Calculate total wasted space from duplicates.

    Args:
        groups: List of duplicate groups

    Returns:
        Total bytes that could be reclaimed
    """
    return sum(g.wasted_bytes for g in groups)


def _is_cancelled(cancel_event: Optional[object]) -> bool:
    """Check if operation should be cancelled."""
    if cancel_event and hasattr(cancel_event, "is_set"):
        return cancel_event.is_set()  # type: ignore
    return False


def _default_rom_extensions() -> List[str]:
    """Get default ROM file extensions."""
    return [
        ".nes",
        ".sfc",
        ".smc",
        ".gb",
        ".gbc",
        ".gba",
        ".nds",
        ".n64",
        ".z64",
        ".v64",
        ".md",
        ".smd",
        ".gen",
        ".bin",
        ".iso",
        ".cue",
        ".img",
        ".zip",
        ".7z",
        ".rar",
        ".rom",
        ".a26",
        ".a52",
        ".a78",
        ".lnx",
        ".pce",
        ".sgx",
        ".cdi",
        ".gdi",
        ".chd",
    ]
