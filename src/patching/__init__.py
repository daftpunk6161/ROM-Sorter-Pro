"""Patch management module.

Features:
- F79: IPS/BPS/UPS Patcher - Apply patches to ROMs
- F80: Patch Library Manager - Manage patches per ROM
- F81: Auto-Patch Matching - Find compatible patches
- F82: Soft-Patching Support - Runtime patching without modification
"""

from .patcher import (
    Patcher,
    PatchFormat,
    PatchResult,
    apply_ips_patch,
    apply_bps_patch,
    apply_ups_patch,
)
from .patch_library import (
    PatchLibrary,
    PatchEntry,
    PatchMetadata,
)
from .auto_matcher import (
    PatchMatcher,
    PatchMatch,
    MatchConfidence,
)
from .soft_patcher import (
    SoftPatcher,
    PatchedRomStream,
)

__all__ = [
    # F79
    "Patcher",
    "PatchFormat",
    "PatchResult",
    "apply_ips_patch",
    "apply_bps_patch",
    "apply_ups_patch",
    # F80
    "PatchLibrary",
    "PatchEntry",
    "PatchMetadata",
    # F81
    "PatchMatcher",
    "PatchMatch",
    "MatchConfidence",
    # F82
    "SoftPatcher",
    "PatchedRomStream",
]
