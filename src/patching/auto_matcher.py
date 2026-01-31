"""Auto-Patch Matching - F81 Implementation.

Automatically finds compatible patches for ROMs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .patch_library import PatchLibrary, PatchEntry
from ..hash_utils import calculate_crc32
from ..core.file_utils import calculate_file_hash


class MatchConfidence(Enum):
    """Confidence level of patch match."""

    EXACT = auto()  # Hash match
    HIGH = auto()  # Name + platform match
    MEDIUM = auto()  # Name similar
    LOW = auto()  # Platform only
    NONE = auto()  # No match


@dataclass
class PatchMatch:
    """A potential patch match for a ROM."""

    patch: PatchEntry
    confidence: MatchConfidence
    score: float  # 0.0 - 1.0
    match_reasons: List[str] = field(default_factory=list)

    @property
    def is_compatible(self) -> bool:
        """Whether patch is likely compatible."""
        return self.confidence in (MatchConfidence.EXACT, MatchConfidence.HIGH)


class PatchMatcher:
    """Automatically matches patches to ROMs.

    Implements F81: Auto-Patch-Matching

    Matching strategies:
    1. Exact: CRC32/SHA1 match
    2. Name-based: ROM name similarity
    3. Platform: Same platform
    """

    # Patterns to normalize ROM names
    NORMALIZE_PATTERNS = [
        (re.compile(r"\s*\([^)]+\)"), ""),  # Remove (USA), (Europe), etc.
        (re.compile(r"\s*\[[^\]]+\]"), ""),  # Remove [!], [a1], etc.
        (re.compile(r"\s*v\d+\.?\d*"), ""),  # Remove v1.0
        (re.compile(r"[_\-\.]"), " "),  # Replace separators
        (re.compile(r"\s+"), " "),  # Collapse spaces
    ]

    def __init__(self, library: PatchLibrary):
        """Initialize matcher.

        Args:
            library: Patch library to search
        """
        self.library = library

    def find_matches(
        self,
        rom_path: str,
        *,
        platform_id: Optional[str] = None,
        min_confidence: MatchConfidence = MatchConfidence.MEDIUM,
    ) -> List[PatchMatch]:
        """Find matching patches for a ROM.

        Args:
            rom_path: Path to ROM file
            platform_id: Known platform ID (improves matching)
            min_confidence: Minimum confidence level

        Returns:
            List of PatchMatches sorted by score
        """
        matches: List[PatchMatch] = []

        # Get ROM info
        rom_info = self._get_rom_info(rom_path)
        if not rom_info:
            return []

        crc32, sha1, name, normalized_name = rom_info

        # Search all patches
        for patch in self.library.get_all_patches():
            match = self._check_match(patch, crc32, sha1, name, normalized_name, platform_id)
            if match and self._confidence_meets_threshold(match.confidence, min_confidence):
                matches.append(match)

        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches

    def find_best_match(
        self,
        rom_path: str,
        *,
        platform_id: Optional[str] = None,
    ) -> Optional[PatchMatch]:
        """Find the best matching patch.

        Args:
            rom_path: ROM path
            platform_id: Platform ID

        Returns:
            Best PatchMatch or None
        """
        matches = self.find_matches(
            rom_path,
            platform_id=platform_id,
            min_confidence=MatchConfidence.HIGH,
        )
        return matches[0] if matches else None

    def batch_match(
        self,
        rom_paths: List[str],
        *,
        platform_id: Optional[str] = None,
    ) -> Dict[str, List[PatchMatch]]:
        """Find matches for multiple ROMs.

        Args:
            rom_paths: List of ROM paths
            platform_id: Platform ID

        Returns:
            Dict mapping ROM path to matches
        """
        results = {}
        for rom_path in rom_paths:
            matches = self.find_matches(rom_path, platform_id=platform_id)
            if matches:
                results[rom_path] = matches
        return results

    def get_unmatched_patches(
        self,
        rom_paths: List[str],
        *,
        platform_id: Optional[str] = None,
    ) -> List[PatchEntry]:
        """Find patches that don't match any ROM.

        Args:
            rom_paths: ROM paths to check
            platform_id: Filter by platform

        Returns:
            List of unmatched patches
        """
        # Get all ROM info
        rom_infos = []
        for path in rom_paths:
            info = self._get_rom_info(path)
            if info:
                rom_infos.append(info)

        # Check each patch
        unmatched = []
        patches = self.library.get_all_patches()
        if platform_id:
            patches = [p for p in patches if p.platform_id == platform_id]

        for patch in patches:
            matched = False
            for crc32, sha1, name, normalized_name in rom_infos:
                match = self._check_match(patch, crc32, sha1, name, normalized_name, platform_id)
                if match and match.confidence in (MatchConfidence.EXACT, MatchConfidence.HIGH):
                    matched = True
                    break
            if not matched:
                unmatched.append(patch)

        return unmatched

    def _get_rom_info(self, rom_path: str) -> Optional[Tuple[str, str, str, str]]:
        """Get ROM info for matching.

        Returns:
            Tuple of (crc32, sha1, name, normalized_name) or None
        """
        path = Path(rom_path)
        if not path.exists():
            return None

        try:
            crc32 = calculate_crc32(rom_path) or ""
            sha1 = calculate_file_hash(rom_path, algorithm="sha1") or ""
            name = path.stem
            normalized_name = self._normalize_name(name)
            return crc32, sha1, name, normalized_name
        except Exception:
            return None

    def _check_match(
        self,
        patch: PatchEntry,
        rom_crc32: str,
        rom_sha1: str,
        rom_name: str,
        normalized_rom_name: str,
        platform_id: Optional[str],
    ) -> Optional[PatchMatch]:
        """Check if patch matches ROM.

        Args:
            patch: Patch to check
            rom_crc32: ROM CRC32
            rom_sha1: ROM SHA1
            rom_name: ROM filename
            normalized_rom_name: Normalized ROM name
            platform_id: Platform ID

        Returns:
            PatchMatch if match, None otherwise
        """
        reasons: List[str] = []
        score = 0.0

        # Exact hash match (highest priority)
        if patch.metadata.target_rom_sha1:
            if patch.metadata.target_rom_sha1.lower() == rom_sha1.lower():
                reasons.append("SHA1 exact match")
                return PatchMatch(
                    patch=patch,
                    confidence=MatchConfidence.EXACT,
                    score=1.0,
                    match_reasons=reasons,
                )

        if patch.metadata.target_rom_crc32:
            if patch.metadata.target_rom_crc32.lower() == rom_crc32.lower():
                reasons.append("CRC32 exact match")
                return PatchMatch(
                    patch=patch,
                    confidence=MatchConfidence.EXACT,
                    score=0.99,
                    match_reasons=reasons,
                )

        # Name-based matching
        patch_target_name = patch.metadata.target_rom_name
        if patch_target_name:
            normalized_patch_name = self._normalize_name(patch_target_name)

            # Exact normalized name match
            if normalized_rom_name.lower() == normalized_patch_name.lower():
                reasons.append("Name exact match")
                score += 0.6

            # Partial name match
            elif (
                normalized_rom_name.lower() in normalized_patch_name.lower()
                or normalized_patch_name.lower() in normalized_rom_name.lower()
            ):
                reasons.append("Name partial match")
                score += 0.3

        # Patch filename matching
        patch_filename = Path(patch.file_path).stem
        normalized_patch_filename = self._normalize_name(patch_filename)
        if normalized_rom_name.lower() in normalized_patch_filename.lower():
            reasons.append("Patch filename contains ROM name")
            score += 0.2

        # Platform match
        if platform_id and patch.platform_id:
            if platform_id.lower() == patch.platform_id.lower():
                reasons.append("Platform match")
                score += 0.2

        # Determine confidence
        if not reasons:
            return None

        if score >= 0.7:
            confidence = MatchConfidence.HIGH
        elif score >= 0.4:
            confidence = MatchConfidence.MEDIUM
        elif score > 0:
            confidence = MatchConfidence.LOW
        else:
            confidence = MatchConfidence.NONE

        if confidence == MatchConfidence.NONE:
            return None

        return PatchMatch(
            patch=patch,
            confidence=confidence,
            score=min(score, 0.95),  # Cap below exact match
            match_reasons=reasons,
        )

    def _normalize_name(self, name: str) -> str:
        """Normalize ROM/patch name for comparison."""
        result = name
        for pattern, replacement in self.NORMALIZE_PATTERNS:
            result = pattern.sub(replacement, result)
        return result.strip().lower()

    def _confidence_meets_threshold(
        self, confidence: MatchConfidence, threshold: MatchConfidence
    ) -> bool:
        """Check if confidence meets threshold."""
        order = [
            MatchConfidence.EXACT,
            MatchConfidence.HIGH,
            MatchConfidence.MEDIUM,
            MatchConfidence.LOW,
            MatchConfidence.NONE,
        ]
        return order.index(confidence) <= order.index(threshold)


def find_patches_for_rom(
    rom_path: str,
    library: PatchLibrary,
    platform_id: Optional[str] = None,
) -> List[PatchMatch]:
    """Convenience function to find patches for a ROM.

    Args:
        rom_path: ROM path
        library: Patch library
        platform_id: Platform ID

    Returns:
        List of matches
    """
    matcher = PatchMatcher(library)
    return matcher.find_matches(rom_path, platform_id=platform_id)
