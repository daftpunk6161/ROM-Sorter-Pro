"""ROM Verification Module - F71, F72, F73 Implementation.

Detects various ROM flags and issues:
- Bad Dumps ([b], [!], [o], [h])
- Modifications ([t], [f], [a])
- Overdumps (size mismatch with DAT)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ..core.dat_index_sqlite import DatIndexSqlite, DatHashRow
from ..core.file_utils import calculate_file_hash
from ..hash_utils import calculate_crc32


class FlagType(Enum):
    """ROM flag categories."""

    # Bad dump flags (F71)
    BAD_DUMP = auto()  # [b] - Bad dump
    VERIFIED = auto()  # [!] - Verified good dump
    OVERDUMP = auto()  # [o] - Overdump
    HACK = auto()  # [h] - Hack

    # Modification flags (F72)
    TRAINER = auto()  # [t] - Trainer
    FIXED = auto()  # [f] - Fixed
    ALTERNATE = auto()  # [a] - Alternate
    PIRATE = auto()  # [p] - Pirate
    TRANSLATION = auto()  # [T] - Translation
    INTRO = auto()  # [I] - Intro (cracktro)

    # Version/Region flags
    BETA = auto()  # (Beta)
    PROTO = auto()  # (Proto)
    DEMO = auto()  # (Demo)
    SAMPLE = auto()  # (Sample)
    UNVERIFIED = auto()  # (Unverified)

    # Size issues (F73)
    SIZE_MISMATCH = auto()  # File size != DAT size
    UNDERSIZED = auto()  # File smaller than expected
    OVERSIZED = auto()  # File larger than expected (potential overdump)


@dataclass(frozen=True)
class RomFlag:
    """A detected flag in a ROM name or file."""

    flag_type: FlagType
    raw_pattern: str  # The actual pattern matched, e.g., "[b]", "(Beta)"
    confidence: float  # 0.0 - 1.0
    source: str  # "filename", "dat_name", "size_check"


@dataclass
class VerificationResult:
    """Complete verification result for a ROM file."""

    file_path: str
    sha1: Optional[str] = None
    crc32: Optional[str] = None
    file_size: int = 0

    # DAT match info
    dat_matched: bool = False
    dat_platform: Optional[str] = None
    dat_rom_name: Optional[str] = None
    dat_set_name: Optional[str] = None
    dat_expected_size: Optional[int] = None

    # Detected flags
    flags: List[RomFlag] = field(default_factory=list)

    # Summary
    is_verified_good: bool = False  # Has [!] flag
    is_bad_dump: bool = False  # Has [b] flag
    is_modified: bool = False  # Has [t], [f], [h], etc.
    has_size_issue: bool = False  # Size mismatch
    confidence_score: float = 0.0  # Overall confidence

    @property
    def flag_types(self) -> Set[FlagType]:
        """Get set of all detected flag types."""
        return {f.flag_type for f in self.flags}

    @property
    def is_clean(self) -> bool:
        """ROM has no issues detected."""
        return (
            self.dat_matched
            and not self.is_bad_dump
            and not self.is_modified
            and not self.has_size_issue
        )


class RomVerifier:
    """ROM verification engine.

    Implements F71, F72, F73:
    - Bad dump detection via [b], [!], [o], [h] flags
    - Modification detection via [t], [f], [a] flags
    - Overdump detection via size comparison with DAT
    """

    # Patterns for flag detection
    # Format: (pattern, flag_type, confidence)
    FLAG_PATTERNS: List[Tuple[re.Pattern[str], FlagType, float]] = [
        # F71: Bad dump flags
        (re.compile(r"\[b\]", re.IGNORECASE), FlagType.BAD_DUMP, 1.0),
        (re.compile(r"\(b\)", re.IGNORECASE), FlagType.BAD_DUMP, 0.9),
        (re.compile(r"\[!\]"), FlagType.VERIFIED, 1.0),
        (re.compile(r"\[o\d*\]", re.IGNORECASE), FlagType.OVERDUMP, 1.0),
        (re.compile(r"\[h\d*\w*\]", re.IGNORECASE), FlagType.HACK, 1.0),
        # F72: Modification flags
        (re.compile(r"\[t\d*\]", re.IGNORECASE), FlagType.TRAINER, 1.0),
        (re.compile(r"\+\d+Trainer", re.IGNORECASE), FlagType.TRAINER, 0.9),
        (re.compile(r"\[f\d*\]", re.IGNORECASE), FlagType.FIXED, 1.0),
        (re.compile(r"\[a\d*\]", re.IGNORECASE), FlagType.ALTERNATE, 1.0),
        (re.compile(r"\[p\d*\]", re.IGNORECASE), FlagType.PIRATE, 1.0),
        (re.compile(r"\[T[\+\-]\w+\]", re.IGNORECASE), FlagType.TRANSLATION, 1.0),
        (re.compile(r"\[I\]", re.IGNORECASE), FlagType.INTRO, 1.0),
        # Version/status patterns
        (re.compile(r"\(Beta\s*\d*\)", re.IGNORECASE), FlagType.BETA, 1.0),
        (re.compile(r"\(Proto\w*\)", re.IGNORECASE), FlagType.PROTO, 1.0),
        (re.compile(r"\(Demo\)", re.IGNORECASE), FlagType.DEMO, 1.0),
        (re.compile(r"\(Sample\)", re.IGNORECASE), FlagType.SAMPLE, 1.0),
        (re.compile(r"\(Unverified\)", re.IGNORECASE), FlagType.UNVERIFIED, 0.8),
    ]

    def __init__(self, index: Optional[DatIndexSqlite] = None):
        """Initialize verifier.

        Args:
            index: Optional DAT index for hash lookups
        """
        self.index = index

    def verify(self, path: str) -> VerificationResult:
        """Verify a ROM file.

        Args:
            path: Path to ROM file

        Returns:
            VerificationResult with all detected flags and issues
        """
        result = VerificationResult(file_path=path)
        file_path = Path(path)

        if not file_path.exists():
            return result

        # Get file size
        try:
            result.file_size = file_path.stat().st_size
        except OSError:
            return result

        # Calculate hashes
        result.sha1 = calculate_file_hash(path, algorithm="sha1")
        result.crc32 = calculate_crc32(path)

        # Check filename for flags
        filename = file_path.stem  # Without extension
        result.flags.extend(self._detect_flags_in_name(filename, "filename"))

        # Look up in DAT index
        if self.index:
            dat_rows = self._lookup_in_dat(result.sha1, result.crc32, result.file_size)
            if dat_rows:
                result.dat_matched = True
                # Use first match for primary info
                first = dat_rows[0]
                result.dat_platform = first.platform_id
                result.dat_rom_name = first.rom_name
                result.dat_set_name = first.set_name
                result.dat_expected_size = first.size_bytes

                # Check DAT name for flags
                if first.rom_name:
                    dat_flags = self._detect_flags_in_name(first.rom_name, "dat_name")
                    # Avoid duplicates
                    existing_patterns = {f.raw_pattern for f in result.flags}
                    for flag in dat_flags:
                        if flag.raw_pattern not in existing_patterns:
                            result.flags.append(flag)

                # F73: Size verification
                if first.size_bytes and first.size_bytes > 0:
                    size_flags = self._check_size(result.file_size, first.size_bytes)
                    result.flags.extend(size_flags)

        # Compute summary flags
        result.is_verified_good = FlagType.VERIFIED in result.flag_types
        result.is_bad_dump = FlagType.BAD_DUMP in result.flag_types
        result.is_modified = bool(
            result.flag_types
            & {
                FlagType.TRAINER,
                FlagType.FIXED,
                FlagType.ALTERNATE,
                FlagType.HACK,
                FlagType.PIRATE,
                FlagType.TRANSLATION,
                FlagType.INTRO,
            }
        )
        result.has_size_issue = bool(
            result.flag_types
            & {FlagType.SIZE_MISMATCH, FlagType.UNDERSIZED, FlagType.OVERSIZED}
        )

        # Compute confidence score
        result.confidence_score = self._compute_confidence(result)

        return result

    def verify_batch(
        self, paths: List[str], *, cancel_event: Optional[object] = None
    ) -> List[VerificationResult]:
        """Verify multiple ROM files.

        Args:
            paths: List of file paths
            cancel_event: Optional event to check for cancellation

        Returns:
            List of VerificationResults
        """
        results = []
        for path in paths:
            if cancel_event and hasattr(cancel_event, "is_set"):
                if cancel_event.is_set():  # type: ignore
                    break
            results.append(self.verify(path))
        return results

    def _detect_flags_in_name(self, name: str, source: str) -> List[RomFlag]:
        """Detect ROM flags in a name string.

        Args:
            name: ROM name or filename
            source: Source of the name ("filename" or "dat_name")

        Returns:
            List of detected RomFlags
        """
        flags = []
        for pattern, flag_type, confidence in self.FLAG_PATTERNS:
            match = pattern.search(name)
            if match:
                flags.append(
                    RomFlag(
                        flag_type=flag_type,
                        raw_pattern=match.group(),
                        confidence=confidence,
                        source=source,
                    )
                )
        return flags

    def _lookup_in_dat(
        self, sha1: Optional[str], crc32: Optional[str], size: int
    ) -> List[DatHashRow]:
        """Look up ROM in DAT index.

        Args:
            sha1: SHA1 hash
            crc32: CRC32 hash
            size: File size in bytes

        Returns:
            List of matching DatHashRow entries
        """
        if not self.index:
            return []

        # Try SHA1 first
        if sha1:
            rows = self.index.lookup_sha1_all(sha1)
            if rows:
                return rows

        # Fallback to CRC32+size
        if crc32 and size:
            rows = self.index.lookup_crc_size_all(crc32, size)
            # Only use if no SHA1 in DAT row
            return [r for r in rows if not r.sha1]

        return []

    def _check_size(self, actual_size: int, expected_size: int) -> List[RomFlag]:
        """Check file size against DAT expected size (F73).

        Args:
            actual_size: Actual file size in bytes
            expected_size: Expected size from DAT

        Returns:
            List of size-related RomFlags
        """
        if actual_size == expected_size:
            return []

        flags = []

        # Always add size mismatch
        flags.append(
            RomFlag(
                flag_type=FlagType.SIZE_MISMATCH,
                raw_pattern=f"size:{actual_size}!={expected_size}",
                confidence=1.0,
                source="size_check",
            )
        )

        # Classify direction
        if actual_size < expected_size:
            diff_pct = (expected_size - actual_size) / expected_size * 100
            flags.append(
                RomFlag(
                    flag_type=FlagType.UNDERSIZED,
                    raw_pattern=f"undersized:{diff_pct:.1f}%",
                    confidence=1.0 if diff_pct > 1 else 0.8,
                    source="size_check",
                )
            )
        else:
            diff_pct = (actual_size - expected_size) / expected_size * 100
            # Overdump detection
            confidence = 1.0 if diff_pct > 5 else 0.7
            flags.append(
                RomFlag(
                    flag_type=FlagType.OVERSIZED,
                    raw_pattern=f"oversized:{diff_pct:.1f}%",
                    confidence=confidence,
                    source="size_check",
                )
            )

        return flags

    def _compute_confidence(self, result: VerificationResult) -> float:
        """Compute overall confidence score.

        Higher score = more trustworthy ROM.

        Args:
            result: Verification result to score

        Returns:
            Confidence score 0.0 - 1.0
        """
        score = 0.5  # Base score

        # DAT match is good
        if result.dat_matched:
            score += 0.3

        # Verified good is excellent
        if result.is_verified_good:
            score += 0.2

        # Bad dump is bad
        if result.is_bad_dump:
            score -= 0.4

        # Modifications reduce trust
        if result.is_modified:
            score -= 0.2

        # Size issues are concerning
        if result.has_size_issue:
            score -= 0.3

        return max(0.0, min(1.0, score))


def detect_bad_dumps(
    paths: List[str], index: Optional[DatIndexSqlite] = None
) -> Dict[str, VerificationResult]:
    """Convenience function to detect bad dumps in a list of files.

    Args:
        paths: List of ROM file paths
        index: Optional DAT index

    Returns:
        Dict mapping path to VerificationResult for ROMs with issues
    """
    verifier = RomVerifier(index)
    results = {}
    for path in paths:
        result = verifier.verify(path)
        if result.is_bad_dump or result.has_size_issue:
            results[path] = result
    return results


def detect_modified_roms(
    paths: List[str], index: Optional[DatIndexSqlite] = None
) -> Dict[str, VerificationResult]:
    """Convenience function to detect modified ROMs.

    Args:
        paths: List of ROM file paths
        index: Optional DAT index

    Returns:
        Dict mapping path to VerificationResult for modified ROMs
    """
    verifier = RomVerifier(index)
    results = {}
    for path in paths:
        result = verifier.verify(path)
        if result.is_modified:
            results[path] = result
    return results
