"""Parent/Clone Relationship Manager - F78 Implementation.

Manages MAME-style parent/clone relationships for ROM collections.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from ..core.dat_index_sqlite import DatIndexSqlite


class RelationshipType(Enum):
    """Type of ROM relationship."""

    PARENT = auto()  # Parent/original ROM
    CLONE = auto()  # Clone/variant of parent
    INDEPENDENT = auto()  # No relationship detected
    BIOS = auto()  # BIOS ROM
    DEVICE = auto()  # Device ROM


@dataclass
class RomRelationship:
    """A ROM with its relationship information."""

    file_path: str
    rom_name: str
    set_name: Optional[str] = None
    parent_name: Optional[str] = None
    relationship_type: RelationshipType = RelationshipType.INDEPENDENT
    clones: List[str] = field(default_factory=list)  # Paths to clone ROMs
    platform_id: Optional[str] = None
    region: Optional[str] = None
    revision: Optional[str] = None

    @property
    def is_parent(self) -> bool:
        return self.relationship_type == RelationshipType.PARENT

    @property
    def is_clone(self) -> bool:
        return self.relationship_type == RelationshipType.CLONE

    @property
    def has_clones(self) -> bool:
        return len(self.clones) > 0


@dataclass
class ParentCloneGroup:
    """A group of parent and clone ROMs."""

    parent: Optional[RomRelationship] = None
    clones: List[RomRelationship] = field(default_factory=list)
    base_name: str = ""
    platform_id: Optional[str] = None

    @property
    def all_roms(self) -> List[RomRelationship]:
        """Get all ROMs in this group."""
        result = []
        if self.parent:
            result.append(self.parent)
        result.extend(self.clones)
        return result

    @property
    def total_count(self) -> int:
        return len(self.all_roms)

    @property
    def has_parent(self) -> bool:
        return self.parent is not None


class ParentCloneManager:
    """Manages parent/clone relationships for ROM collections.

    Implements F78: Parent/Clone-Verwaltung

    Features:
    - Extract relationships from DAT data
    - Infer relationships from naming patterns
    - Build hierarchy views
    - Support MAME-style parent/clone organization
    """

    # Patterns for detecting clones
    REVISION_PATTERN = re.compile(r"\(Rev\s*([A-Z0-9]+)\)", re.IGNORECASE)
    VERSION_PATTERN = re.compile(r"v(\d+\.?\d*)", re.IGNORECASE)
    ALTERNATE_PATTERN = re.compile(r"\[a(\d*)\]", re.IGNORECASE)
    REGION_PATTERN = re.compile(r"\((USA|Europe|Japan|World|[A-Z]{2})\)", re.IGNORECASE)

    # Patterns that indicate a clone (not original)
    CLONE_INDICATORS = [
        re.compile(r"\[a\d*\]", re.IGNORECASE),  # Alternate
        re.compile(r"\[h\d*\w*\]", re.IGNORECASE),  # Hack
        re.compile(r"\[t\d*\]", re.IGNORECASE),  # Trainer
        re.compile(r"\[f\d*\]", re.IGNORECASE),  # Fixed
        re.compile(r"\[p\d*\]", re.IGNORECASE),  # Pirate
        re.compile(r"\(Rev\s*[B-Z]\)", re.IGNORECASE),  # Rev B+ (A is usually original)
        re.compile(r"v[2-9]\.", re.IGNORECASE),  # v2.0+ (v1.x is usually original)
    ]

    # Patterns that indicate parent/original
    PARENT_INDICATORS = [
        re.compile(r"\[!\]"),  # Verified good dump
        re.compile(r"\(Rev\s*A\)", re.IGNORECASE),  # Rev A
        re.compile(r"v1\.0", re.IGNORECASE),  # v1.0
    ]

    def __init__(self, index: Optional[DatIndexSqlite] = None):
        """Initialize manager.

        Args:
            index: Optional DAT index for relationship lookup
        """
        self.index = index

    def build_hierarchy(
        self,
        paths: List[str],
        *,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_event: Optional[object] = None,
    ) -> List[ParentCloneGroup]:
        """Build parent/clone hierarchy from file list.

        Args:
            paths: List of ROM file paths
            progress_callback: Progress callback
            cancel_event: Cancellation event

        Returns:
            List of ParentCloneGroups
        """
        # First pass: Create relationships for all files
        relationships: Dict[str, RomRelationship] = {}
        total = len(paths)

        for idx, path in enumerate(paths):
            if _is_cancelled(cancel_event):
                break

            if progress_callback:
                progress_callback(idx + 1, total, f"Analyzing: {path}")

            rel = self._create_relationship(path)
            relationships[path] = rel

        # Second pass: Group by base name
        base_groups: Dict[str, List[RomRelationship]] = defaultdict(list)
        for rel in relationships.values():
            base_name = self._get_base_name(rel.rom_name)
            base_groups[base_name.lower()].append(rel)

        # Third pass: Identify parent in each group
        groups: List[ParentCloneGroup] = []
        for base_name, rels in base_groups.items():
            if _is_cancelled(cancel_event):
                break

            if len(rels) < 1:
                continue

            group = self._build_group(base_name, rels)
            groups.append(group)

        return groups

    def get_clones_for_parent(
        self,
        parent_path: str,
        all_paths: List[str],
    ) -> List[str]:
        """Find all clones for a given parent ROM.

        Args:
            parent_path: Path to parent ROM
            all_paths: All ROM paths to search

        Returns:
            List of clone file paths
        """
        parent_name = Path(parent_path).stem
        parent_base = self._get_base_name(parent_name)

        clones = []
        for path in all_paths:
            if path == parent_path:
                continue

            name = Path(path).stem
            base = self._get_base_name(name)

            if base.lower() == parent_base.lower():
                # Check if it looks like a clone
                if self._looks_like_clone(name):
                    clones.append(path)

        return clones

    def suggest_parent(
        self,
        paths: List[str],
    ) -> Optional[str]:
        """Suggest which ROM should be the parent from a list.

        Args:
            paths: List of related ROM paths

        Returns:
            Path of suggested parent, or None
        """
        if not paths:
            return None

        if len(paths) == 1:
            return paths[0]

        # Score each path
        scores: List[Tuple[str, int]] = []
        for path in paths:
            name = Path(path).stem
            score = self._parent_score(name)
            scores.append((path, score))

        # Return highest scoring
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0][0]

    def _create_relationship(self, path: str) -> RomRelationship:
        """Create relationship info for a ROM file.

        Args:
            path: File path

        Returns:
            RomRelationship
        """
        name = Path(path).stem

        rel = RomRelationship(
            file_path=path,
            rom_name=name,
        )

        # Extract region
        region_match = self.REGION_PATTERN.search(name)
        if region_match:
            rel.region = region_match.group(1)

        # Extract revision
        rev_match = self.REVISION_PATTERN.search(name)
        if rev_match:
            rel.revision = rev_match.group(1)

        # Determine type
        if self._looks_like_clone(name):
            rel.relationship_type = RelationshipType.CLONE
        elif self._looks_like_parent(name):
            rel.relationship_type = RelationshipType.PARENT
        else:
            rel.relationship_type = RelationshipType.INDEPENDENT

        # Try to get info from DAT index
        if self.index:
            self._enrich_from_dat(rel)

        return rel

    def _enrich_from_dat(self, rel: RomRelationship) -> None:
        """Enrich relationship with DAT index data.

        Args:
            rel: Relationship to enrich
        """
        # This would query the DAT index for parent/clone info
        # DATs like MAME include cloneof attributes
        # For now, we rely on naming patterns
        pass

    def _get_base_name(self, name: str) -> str:
        """Get base name without region/version tags.

        Args:
            name: ROM name

        Returns:
            Base name
        """
        result = name

        # Remove common suffixes
        patterns = [
            r"\s*\([^)]+\)",  # (USA), (Europe), etc.
            r"\s*\[[^\]]+\]",  # [!], [a1], etc.
            r"\s*v\d+\.?\d*",  # v1.0
            r"\s+-\s*$",  # Trailing dash
        ]

        for pattern in patterns:
            result = re.sub(pattern, "", result)

        return result.strip()

    def _looks_like_clone(self, name: str) -> bool:
        """Check if name indicates a clone.

        Args:
            name: ROM name

        Returns:
            True if likely a clone
        """
        for pattern in self.CLONE_INDICATORS:
            if pattern.search(name):
                return True
        return False

    def _looks_like_parent(self, name: str) -> bool:
        """Check if name indicates a parent/original.

        Args:
            name: ROM name

        Returns:
            True if likely a parent
        """
        for pattern in self.PARENT_INDICATORS:
            if pattern.search(name):
                return True
        return False

    def _parent_score(self, name: str) -> int:
        """Calculate parent likelihood score.

        Higher score = more likely to be parent.

        Args:
            name: ROM name

        Returns:
            Score (higher is better for parent)
        """
        score = 0

        # Positive indicators
        if "[!]" in name:
            score += 100  # Verified good dump
        if re.search(r"\(Rev\s*A\)", name, re.IGNORECASE):
            score += 50  # Rev A
        if re.search(r"v1\.0", name, re.IGNORECASE):
            score += 30  # v1.0
        if "(USA)" in name:
            score += 20  # USA region often primary
        if "(World)" in name:
            score += 15  # World release

        # Negative indicators (clones)
        for pattern in self.CLONE_INDICATORS:
            if pattern.search(name):
                score -= 50

        return score

    def _build_group(
        self, base_name: str, rels: List[RomRelationship]
    ) -> ParentCloneGroup:
        """Build a ParentCloneGroup from related ROMs.

        Args:
            base_name: Normalized base name
            rels: Related relationships

        Returns:
            ParentCloneGroup
        """
        group = ParentCloneGroup(
            base_name=base_name,
        )

        if len(rels) == 1:
            # Single ROM - could be parent or independent
            rel = rels[0]
            if rel.relationship_type == RelationshipType.CLONE:
                group.clones.append(rel)
            else:
                group.parent = rel
            group.platform_id = rel.platform_id
            return group

        # Find best parent candidate
        best_parent: Optional[RomRelationship] = None
        best_score = -1000

        for rel in rels:
            score = self._parent_score(rel.rom_name)
            if score > best_score:
                best_score = score
                best_parent = rel

        # Set parent and clones
        if best_parent:
            best_parent.relationship_type = RelationshipType.PARENT
            group.parent = best_parent
            group.platform_id = best_parent.platform_id

            for rel in rels:
                if rel.file_path != best_parent.file_path:
                    rel.relationship_type = RelationshipType.CLONE
                    rel.parent_name = best_parent.rom_name
                    group.clones.append(rel)
                    best_parent.clones.append(rel.file_path)

        return group


def _is_cancelled(cancel_event: Optional[object]) -> bool:
    """Check if operation should be cancelled."""
    if cancel_event and hasattr(cancel_event, "is_set"):
        return cancel_event.is_set()  # type: ignore
    return False


def build_parent_clone_hierarchy(
    paths: List[str],
    index: Optional[DatIndexSqlite] = None,
    **kwargs: object,
) -> List[ParentCloneGroup]:
    """Convenience function to build parent/clone hierarchy.

    Args:
        paths: ROM file paths
        index: Optional DAT index
        **kwargs: Additional arguments

    Returns:
        List of ParentCloneGroups
    """
    manager = ParentCloneManager(index=index)
    return manager.build_hierarchy(paths, **kwargs)  # type: ignore[arg-type]
