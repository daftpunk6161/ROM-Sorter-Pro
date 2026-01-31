"""Fuzzy duplicate finder - F76 Implementation.

Finds near-duplicates based on name similarity:
- Rev A vs Rev B
- Region variants (USA vs Europe)
- Language variants
- Alternative dumps [a1], [a2]
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple


class MatchReason(Enum):
    """Reason why two ROMs are considered fuzzy duplicates."""

    SAME_GAME_DIFFERENT_REVISION = auto()  # Rev A vs Rev B
    SAME_GAME_DIFFERENT_REGION = auto()  # USA vs Europe
    SAME_GAME_DIFFERENT_LANGUAGE = auto()  # En vs De
    SAME_GAME_ALTERNATE_DUMP = auto()  # [a1] vs [a2]
    SAME_GAME_VERSION_VARIANT = auto()  # v1.0 vs v1.1
    HIGH_NAME_SIMILARITY = auto()  # Names very similar
    SAME_NORMALIZED_NAME = auto()  # Same after normalization


@dataclass
class FuzzyMatch:
    """A pair of ROMs that are fuzzy duplicates."""

    file_path_a: str
    file_path_b: str
    match_reason: MatchReason
    similarity_score: float  # 0.0 - 1.0
    normalized_name: str  # Common base name
    details: Dict[str, str] = field(default_factory=dict)

    @property
    def filename_a(self) -> str:
        return Path(self.file_path_a).name

    @property
    def filename_b(self) -> str:
        return Path(self.file_path_b).name


@dataclass
class FuzzyGroup:
    """A group of ROMs that are variants of the same game."""

    base_name: str
    files: List[str] = field(default_factory=list)
    matches: List[FuzzyMatch] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.files)

    def get_regions(self) -> Dict[str, List[str]]:
        """Group files by detected region."""
        regions: Dict[str, List[str]] = defaultdict(list)
        for f in self.files:
            region = _detect_region(Path(f).stem)
            regions[region].append(f)
        return dict(regions)


class FuzzyDuplicateFinder:
    """Finds fuzzy/near-duplicates in ROM collections.

    Implements F76: Fuzzy-Duplikat-Finder

    Uses multiple strategies:
    1. Name normalization (remove tags, regions, versions)
    2. Levenshtein distance for similar names
    3. Region/revision/language detection
    """

    # Patterns to strip for normalization
    STRIP_PATTERNS = [
        r"\s*\([^)]+\)",  # (USA), (Europe), (Rev A), etc.
        r"\s*\[[^\]]+\]",  # [!], [a1], [b], etc.
        r"\s*v\d+\.?\d*",  # v1.0, v2, etc.
        r"\s*-\s*",  # Trailing dashes
        r"\s+",  # Multiple spaces -> single
    ]

    # Region patterns
    REGION_PATTERNS = {
        "USA": re.compile(r"\(USA\)|\(US\)|\(U\)", re.IGNORECASE),
        "Europe": re.compile(r"\(Europe\)|\(EUR\)|\(E\)", re.IGNORECASE),
        "Japan": re.compile(r"\(Japan\)|\(JPN\)|\(J\)", re.IGNORECASE),
        "World": re.compile(r"\(World\)|\(W\)", re.IGNORECASE),
        "Germany": re.compile(r"\(Germany\)|\(De\)|\(G\)", re.IGNORECASE),
        "France": re.compile(r"\(France\)|\(Fr\)|\(F\)", re.IGNORECASE),
        "Spain": re.compile(r"\(Spain\)|\(Es\)|\(S\)", re.IGNORECASE),
        "Italy": re.compile(r"\(Italy\)|\(It\)|\(I\)", re.IGNORECASE),
        "Korea": re.compile(r"\(Korea\)|\(K\)", re.IGNORECASE),
        "China": re.compile(r"\(China\)|\(Ch\)", re.IGNORECASE),
        "Australia": re.compile(r"\(Australia\)|\(A\)", re.IGNORECASE),
    }

    # Revision patterns
    REVISION_PATTERN = re.compile(r"\(Rev\s*([A-Z0-9]+)\)", re.IGNORECASE)
    VERSION_PATTERN = re.compile(r"v(\d+\.?\d*)", re.IGNORECASE)
    ALTERNATE_PATTERN = re.compile(r"\[a(\d*)\]", re.IGNORECASE)

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        min_name_length: int = 3,
    ):
        """Initialize finder.

        Args:
            similarity_threshold: Minimum similarity for fuzzy match (0.0-1.0)
            min_name_length: Minimum normalized name length to consider
        """
        self.similarity_threshold = similarity_threshold
        self.min_name_length = min_name_length

    def find_fuzzy_duplicates(
        self,
        paths: List[str],
        *,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_event: Optional[object] = None,
    ) -> List[FuzzyGroup]:
        """Find fuzzy duplicates in a list of paths.

        Args:
            paths: List of file paths
            progress_callback: Optional progress callback
            cancel_event: Optional cancellation event

        Returns:
            List of FuzzyGroups
        """
        # Group by normalized name
        normalized_groups: Dict[str, List[str]] = defaultdict(list)
        total = len(paths)

        for idx, path in enumerate(paths):
            if _is_cancelled(cancel_event):
                break

            if progress_callback:
                progress_callback(idx + 1, total, f"Normalizing: {path}")

            filename = Path(path).stem
            normalized = self._normalize_name(filename)

            if len(normalized) >= self.min_name_length:
                normalized_groups[normalized.lower()].append(path)

        # Filter to groups with 2+ files
        fuzzy_groups: List[FuzzyGroup] = []

        for base_name, files in normalized_groups.items():
            if len(files) < 2:
                continue

            group = FuzzyGroup(base_name=base_name, files=files)

            # Create matches between files
            for i, file_a in enumerate(files):
                for file_b in files[i + 1 :]:
                    match = self._create_match(file_a, file_b, base_name)
                    if match:
                        group.matches.append(match)

            fuzzy_groups.append(group)

        # Additionally find similar names using Levenshtein
        similar_matches = self._find_similar_names(paths, cancel_event)
        for match in similar_matches:
            # Create single-match groups for these
            group = FuzzyGroup(
                base_name=match.normalized_name,
                files=[match.file_path_a, match.file_path_b],
                matches=[match],
            )
            fuzzy_groups.append(group)

        return fuzzy_groups

    def find_region_variants(
        self,
        paths: List[str],
        *,
        cancel_event: Optional[object] = None,
    ) -> Dict[str, Dict[str, List[str]]]:
        """Find region variants of the same game.

        Args:
            paths: List of file paths
            cancel_event: Cancellation event

        Returns:
            Dict mapping normalized name to region->files dict
        """
        # Group by normalized name
        groups: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))

        for path in paths:
            if _is_cancelled(cancel_event):
                break

            filename = Path(path).stem
            normalized = self._normalize_name(filename)
            region = _detect_region(filename)

            if len(normalized) >= self.min_name_length:
                groups[normalized.lower()][region].append(path)

        # Filter to games with multiple regions
        return {
            name: dict(regions)
            for name, regions in groups.items()
            if len(regions) > 1
        }

    def _normalize_name(self, name: str) -> str:
        """Normalize a ROM name for comparison.

        Removes region tags, version info, dump flags, etc.

        Args:
            name: Original name

        Returns:
            Normalized name
        """
        result = name

        # Apply strip patterns
        for pattern in self.STRIP_PATTERNS:
            result = re.sub(pattern, " ", result)

        # Clean up
        result = result.strip()
        result = re.sub(r"\s+", " ", result)

        return result

    def _create_match(
        self, file_a: str, file_b: str, normalized: str
    ) -> Optional[FuzzyMatch]:
        """Create a FuzzyMatch between two files.

        Args:
            file_a: First file path
            file_b: Second file path
            normalized: Normalized base name

        Returns:
            FuzzyMatch or None
        """
        name_a = Path(file_a).stem
        name_b = Path(file_b).stem

        details: Dict[str, str] = {}
        reason = MatchReason.SAME_NORMALIZED_NAME

        # Detect specific differences
        region_a = _detect_region(name_a)
        region_b = _detect_region(name_b)

        if region_a != region_b and region_a != "Unknown" and region_b != "Unknown":
            reason = MatchReason.SAME_GAME_DIFFERENT_REGION
            details["region_a"] = region_a
            details["region_b"] = region_b

        # Check revision
        rev_a = self.REVISION_PATTERN.search(name_a)
        rev_b = self.REVISION_PATTERN.search(name_b)
        if rev_a and rev_b and rev_a.group(1) != rev_b.group(1):
            reason = MatchReason.SAME_GAME_DIFFERENT_REVISION
            details["revision_a"] = rev_a.group(1)
            details["revision_b"] = rev_b.group(1)

        # Check version
        ver_a = self.VERSION_PATTERN.search(name_a)
        ver_b = self.VERSION_PATTERN.search(name_b)
        if ver_a and ver_b and ver_a.group(1) != ver_b.group(1):
            reason = MatchReason.SAME_GAME_VERSION_VARIANT
            details["version_a"] = ver_a.group(1)
            details["version_b"] = ver_b.group(1)

        # Check alternate dump
        alt_a = self.ALTERNATE_PATTERN.search(name_a)
        alt_b = self.ALTERNATE_PATTERN.search(name_b)
        if alt_a or alt_b:
            reason = MatchReason.SAME_GAME_ALTERNATE_DUMP
            if alt_a:
                details["alt_a"] = alt_a.group(1) or "1"
            if alt_b:
                details["alt_b"] = alt_b.group(1) or "1"

        return FuzzyMatch(
            file_path_a=file_a,
            file_path_b=file_b,
            match_reason=reason,
            similarity_score=1.0,  # Exact normalized match
            normalized_name=normalized,
            details=details,
        )

    def _find_similar_names(
        self,
        paths: List[str],
        cancel_event: Optional[object] = None,
    ) -> List[FuzzyMatch]:
        """Find names that are similar but not identical after normalization.

        Uses Levenshtein distance for fuzzy matching.

        Args:
            paths: File paths
            cancel_event: Cancellation event

        Returns:
            List of FuzzyMatches
        """
        matches: List[FuzzyMatch] = []

        # Get unique normalized names
        name_to_paths: Dict[str, List[str]] = defaultdict(list)
        for path in paths:
            normalized = self._normalize_name(Path(path).stem).lower()
            if len(normalized) >= self.min_name_length:
                name_to_paths[normalized].append(path)

        # Compare names
        names = list(name_to_paths.keys())
        seen_pairs: Set[Tuple[str, str]] = set()

        for i, name_a in enumerate(names):
            if _is_cancelled(cancel_event):
                break

            for name_b in names[i + 1 :]:
                # Skip if already matched
                pair = tuple(sorted([name_a, name_b]))
                if pair in seen_pairs:
                    continue

                similarity = _levenshtein_similarity(name_a, name_b)
                if similarity >= self.similarity_threshold:
                    seen_pairs.add(pair)

                    # Create matches for all file combinations
                    for path_a in name_to_paths[name_a]:
                        for path_b in name_to_paths[name_b]:
                            matches.append(
                                FuzzyMatch(
                                    file_path_a=path_a,
                                    file_path_b=path_b,
                                    match_reason=MatchReason.HIGH_NAME_SIMILARITY,
                                    similarity_score=similarity,
                                    normalized_name=f"{name_a} ≈ {name_b}",
                                    details={
                                        "name_a": name_a,
                                        "name_b": name_b,
                                        "similarity": f"{similarity:.2%}",
                                    },
                                )
                            )

        return matches


def _detect_region(name: str) -> str:
    """Detect region from ROM name.

    Args:
        name: ROM filename or name

    Returns:
        Region name or "Unknown"
    """
    for region, pattern in FuzzyDuplicateFinder.REGION_PATTERNS.items():
        if pattern.search(name):
            return region
    return "Unknown"


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def _levenshtein_similarity(s1: str, s2: str) -> float:
    """Calculate similarity ratio based on Levenshtein distance.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity ratio 0.0 - 1.0
    """
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    distance = _levenshtein_distance(s1, s2)
    return 1.0 - (distance / max_len)


def _is_cancelled(cancel_event: Optional[object]) -> bool:
    """Check if operation should be cancelled."""
    if cancel_event and hasattr(cancel_event, "is_set"):
        return cancel_event.is_set()  # type: ignore
    return False


def find_fuzzy_duplicates(
    paths: List[str],
    similarity_threshold: float = 0.85,
    **kwargs: object,
) -> List[FuzzyGroup]:
    """Convenience function to find fuzzy duplicates.

    Args:
        paths: List of file paths
        similarity_threshold: Minimum similarity threshold
        **kwargs: Additional arguments

    Returns:
        List of FuzzyGroups
    """
    finder = FuzzyDuplicateFinder(similarity_threshold=similarity_threshold)
    return finder.find_fuzzy_duplicates(paths, **kwargs)  # type: ignore[arg-type]
