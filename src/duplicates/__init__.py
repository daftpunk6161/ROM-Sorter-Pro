"""Duplicate detection and management module.

Features:
- F75: Hash-based duplicate finder
- F76: Fuzzy duplicate finder
- F77: Duplicate merge wizard logic
- F78: Parent/Clone relationship management
"""

from .hash_duplicate_finder import (
    HashDuplicateFinder,
    DuplicateGroup,
    DuplicateEntry,
)
from .fuzzy_duplicate_finder import (
    FuzzyDuplicateFinder,
    FuzzyMatch,
    MatchReason,
)
from .merge_wizard import (
    MergeWizard,
    MergeStrategy,
    MergeDecision,
    MergeResult,
)
from .parent_clone import (
    ParentCloneManager,
    RomRelationship,
    RelationshipType,
)

__all__ = [
    # F75
    "HashDuplicateFinder",
    "DuplicateGroup",
    "DuplicateEntry",
    # F76
    "FuzzyDuplicateFinder",
    "FuzzyMatch",
    "MatchReason",
    # F77
    "MergeWizard",
    "MergeStrategy",
    "MergeDecision",
    "MergeResult",
    # F78
    "ParentCloneManager",
    "RomRelationship",
    "RelationshipType",
]
