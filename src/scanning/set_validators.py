"""Set validators for multi-file ROM sets (cue/bin, gdi, m3u).

These validators detect and group related files that belong together as a single
ROM set, preventing them from being sorted separately or incorrectly.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SetValidationResult:
    """Result of validating a multi-file set."""

    is_set: bool
    set_type: str  # "cue-bin", "gdi", "m3u", "ps3-folder", "single"
    primary_file: str  # The main file (e.g., .cue, .gdi, .m3u)
    member_files: Tuple[str, ...]  # All files in the set
    missing_files: Tuple[str, ...]  # Referenced but not found
    warnings: Tuple[str, ...]
    platform_hint: Optional[str] = None  # e.g., "Dreamcast" for .gdi


def parse_cue_file(cue_path: Path) -> Tuple[List[str], List[str]]:
    """Parse a .cue file and extract referenced FILE entries.

    Returns:
        Tuple of (found_files, missing_files) as absolute paths.
    """
    found: List[str] = []
    missing: List[str] = []

    if not cue_path.exists():
        return found, missing

    try:
        content = cue_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        try:
            content = cue_path.read_text(encoding="latin-1", errors="replace")
        except Exception as e:
            logger.warning("Could not read cue file %s: %s", cue_path, e)
            return found, missing

    # FILE "filename.bin" BINARY
    # FILE filename.bin BINARY
    # FILE 'filename.bin' BINARY
    file_pattern = re.compile(
        r'^\s*FILE\s+["\']?([^"\']+)["\']?\s+(?:BINARY|MOTOROLA|AIFF|WAVE|MP3)',
        re.IGNORECASE | re.MULTILINE,
    )

    cue_dir = cue_path.parent

    for match in file_pattern.finditer(content):
        filename = match.group(1).strip()
        if not filename:
            continue

        # Handle relative and absolute paths
        if os.path.isabs(filename):
            file_path = Path(filename)
        else:
            file_path = cue_dir / filename

        resolved = file_path.resolve()

        if resolved.exists():
            found.append(str(resolved))
        else:
            missing.append(str(resolved))

    return found, missing


def validate_cue_bin_set(cue_path: Path) -> SetValidationResult:
    """Validate a cue/bin disc image set.

    Args:
        cue_path: Path to the .cue file.

    Returns:
        SetValidationResult with validation details.
    """
    if not cue_path.exists() or cue_path.suffix.lower() != ".cue":
        return SetValidationResult(
            is_set=False,
            set_type="single",
            primary_file=str(cue_path),
            member_files=(str(cue_path),),
            missing_files=(),
            warnings=(),
        )

    found_files, missing_files = parse_cue_file(cue_path)

    warnings: List[str] = []
    if missing_files:
        for mf in missing_files:
            warnings.append(f"Referenced file not found: {mf}")

    if not found_files and not missing_files:
        warnings.append("No FILE entries found in cue sheet")

    # Platform hint: cue/bin is used by PS1, PS2, Saturn, SegaCD, PCE-CD, PC-FX, etc.
    # We cannot determine the exact platform from the cue alone.
    platform_hint = None

    all_members = [str(cue_path)] + found_files

    return SetValidationResult(
        is_set=True,
        set_type="cue-bin",
        primary_file=str(cue_path),
        member_files=tuple(all_members),
        missing_files=tuple(missing_files),
        warnings=tuple(warnings),
        platform_hint=platform_hint,
    )


def parse_gdi_file(gdi_path: Path) -> Tuple[List[str], List[str], int]:
    """Parse a .gdi file and extract track file references.

    Returns:
        Tuple of (found_files, missing_files, track_count).
    """
    found: List[str] = []
    missing: List[str] = []
    track_count = 0

    if not gdi_path.exists():
        return found, missing, track_count

    try:
        content = gdi_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        try:
            content = gdi_path.read_text(encoding="latin-1", errors="replace")
        except Exception as e:
            logger.warning("Could not read gdi file %s: %s", gdi_path, e)
            return found, missing, track_count

    gdi_dir = gdi_path.parent
    lines = content.strip().splitlines()

    if not lines:
        return found, missing, track_count

    # First line is track count
    try:
        track_count = int(lines[0].strip())
    except ValueError:
        track_count = 0

    # Subsequent lines: track_num lba type sector_size filename offset
    # Example: 1 0 4 2352 track01.bin 0
    track_pattern = re.compile(
        r'^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([^\s]+)\s+(\d+)\s*$'
    )

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        match = track_pattern.match(line)
        if not match:
            # Try quoted filename variant
            quoted_pattern = re.compile(
                r'^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+"([^"]+)"\s+(\d+)\s*$'
            )
            match = quoted_pattern.match(line)

        if match:
            filename = match.group(5).strip()
            if filename:
                file_path = gdi_dir / filename
                resolved = file_path.resolve()
                if resolved.exists():
                    found.append(str(resolved))
                else:
                    missing.append(str(resolved))

    return found, missing, track_count


def validate_gdi_set(gdi_path: Path) -> SetValidationResult:
    """Validate a Dreamcast GDI disc image set.

    Args:
        gdi_path: Path to the .gdi file.

    Returns:
        SetValidationResult with validation details.
    """
    if not gdi_path.exists() or gdi_path.suffix.lower() != ".gdi":
        return SetValidationResult(
            is_set=False,
            set_type="single",
            primary_file=str(gdi_path),
            member_files=(str(gdi_path),),
            missing_files=(),
            warnings=(),
        )

    found_files, missing_files, track_count = parse_gdi_file(gdi_path)

    warnings: List[str] = []
    if missing_files:
        for mf in missing_files:
            warnings.append(f"Track file not found: {mf}")

    if track_count > 0 and len(found_files) < track_count:
        warnings.append(
            f"Expected {track_count} tracks, found {len(found_files)} files"
        )

    if not found_files and not missing_files:
        warnings.append("No track entries found in GDI file")

    all_members = [str(gdi_path)] + found_files

    return SetValidationResult(
        is_set=True,
        set_type="gdi",
        primary_file=str(gdi_path),
        member_files=tuple(all_members),
        missing_files=tuple(missing_files),
        warnings=tuple(warnings),
        platform_hint="Dreamcast",
    )


def parse_m3u_file(m3u_path: Path) -> Tuple[List[str], List[str]]:
    """Parse a .m3u playlist file and extract disc file references.

    Returns:
        Tuple of (found_files, missing_files).
    """
    found: List[str] = []
    missing: List[str] = []

    if not m3u_path.exists():
        return found, missing

    try:
        content = m3u_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        try:
            content = m3u_path.read_text(encoding="latin-1", errors="replace")
        except Exception as e:
            logger.warning("Could not read m3u file %s: %s", m3u_path, e)
            return found, missing

    m3u_dir = m3u_path.parent

    for line in content.strip().splitlines():
        line = line.strip()
        # Skip comments and extended m3u directives
        if not line or line.startswith("#"):
            continue

        # Handle relative and absolute paths
        if os.path.isabs(line):
            file_path = Path(line)
        else:
            file_path = m3u_dir / line

        resolved = file_path.resolve()

        if resolved.exists():
            found.append(str(resolved))
        else:
            missing.append(str(resolved))

    return found, missing


def validate_m3u_set(m3u_path: Path) -> SetValidationResult:
    """Validate an m3u multi-disc playlist.

    Args:
        m3u_path: Path to the .m3u file.

    Returns:
        SetValidationResult with validation details.
    """
    if not m3u_path.exists() or m3u_path.suffix.lower() != ".m3u":
        return SetValidationResult(
            is_set=False,
            set_type="single",
            primary_file=str(m3u_path),
            member_files=(str(m3u_path),),
            missing_files=(),
            warnings=(),
        )

    found_files, missing_files = parse_m3u_file(m3u_path)

    warnings: List[str] = []
    if missing_files:
        for mf in missing_files:
            warnings.append(f"Referenced disc not found: {mf}")

    if not found_files and not missing_files:
        warnings.append("No disc entries found in m3u playlist")

    all_members = [str(m3u_path)] + found_files

    return SetValidationResult(
        is_set=True,
        set_type="m3u",
        primary_file=str(m3u_path),
        member_files=tuple(all_members),
        missing_files=tuple(missing_files),
        warnings=tuple(warnings),
        platform_hint=None,  # m3u is platform-agnostic
    )


def detect_set_membership(file_path: Path) -> Optional[SetValidationResult]:
    """Detect if a file is part of a multi-file set and return validation info.

    This function checks if the given file is:
    1. A primary file (.cue, .gdi, .m3u) that defines a set
    2. A member file (.bin, track*.raw, etc.) that belongs to a set

    Args:
        file_path: Path to the file to check.

    Returns:
        SetValidationResult if part of a set, None otherwise.
    """
    ext = file_path.suffix.lower()

    # Primary file types
    if ext == ".cue":
        return validate_cue_bin_set(file_path)
    elif ext == ".gdi":
        return validate_gdi_set(file_path)
    elif ext == ".m3u":
        return validate_m3u_set(file_path)

    # Check if this file is referenced by a nearby set file
    parent = file_path.parent

    # Look for a .cue file that references this .bin
    if ext == ".bin":
        for cue_file in parent.glob("*.cue"):
            result = validate_cue_bin_set(cue_file)
            if str(file_path.resolve()) in result.member_files:
                return result

    # Look for a .gdi file that references this track file
    if ext in (".bin", ".raw"):
        for gdi_file in parent.glob("*.gdi"):
            result = validate_gdi_set(gdi_file)
            if str(file_path.resolve()) in result.member_files:
                return result

    # Check if referenced in m3u
    for m3u_file in parent.glob("*.m3u"):
        result = validate_m3u_set(m3u_file)
        if str(file_path.resolve()) in result.member_files:
            return result

    return None


def group_sets_in_directory(directory: Path) -> Dict[str, SetValidationResult]:
    """Group all multi-file sets in a directory.

    Args:
        directory: Directory to scan.

    Returns:
        Dict mapping primary file path to SetValidationResult.
    """
    sets: Dict[str, SetValidationResult] = {}
    seen_members: Set[str] = set()

    if not directory.is_dir():
        return sets

    # First pass: find all set primary files
    for ext, validator in [
        (".cue", validate_cue_bin_set),
        (".gdi", validate_gdi_set),
        (".m3u", validate_m3u_set),
    ]:
        for primary in directory.glob(f"*{ext}"):
            result = validator(primary)
            if result.is_set:
                sets[str(primary)] = result
                seen_members.update(result.member_files)

    return sets


def is_set_member_file(file_path: Path, known_sets: Dict[str, SetValidationResult]) -> bool:
    """Check if a file is a member of any known set (excluding primary files).

    Args:
        file_path: File to check.
        known_sets: Dictionary from group_sets_in_directory().

    Returns:
        True if the file is a non-primary member of a set.
    """
    resolved = str(file_path.resolve())

    for primary, result in known_sets.items():
        if resolved == primary:
            # Primary file, not a member
            return False
        if resolved in result.member_files:
            return True

    return False
