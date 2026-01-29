"""Disc format detection via header sniffing.

This module provides lightweight header analysis to disambiguate disc image formats
that share common extensions (.iso, .bin, .img) across different platforms.

Supported formats:
- PlayStation 1/2 (ISO9660 with PLAYSTATION identifier)
- Sega Saturn (SEGA SEGASATURN in PVD)
- Sega CD / Mega CD (SEGADISCSYSTEM)
- Dreamcast (via .gdi files, not .bin directly)
- PC Engine CD (PC Engine CD-ROM SYSTEM)
- 3DO (3DO filesystem)
- Xbox (XBOX DVD filesystem)

References:
- ISO9660 Primary Volume Descriptor: sector 16, offset 0x8000
- PS1/PS2: "PLAYSTATION" at PVD system identifier or specific magic
- Saturn: "SEGA SEGASATURN" at offset 0x00 in IP.BIN
- SegaCD: "SEGADISCSYSTEM" at offset 0x00
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import BinaryIO, Optional


class DiscPlatform(Enum):
    """Detected disc platform."""

    UNKNOWN = "Unknown"
    PS1 = "PS1"
    PS2 = "PS2"
    PS3 = "PS3"
    PSP = "PSP"
    SATURN = "Saturn"
    SEGACD = "SegaCD"
    DREAMCAST = "Dreamcast"
    PC_ENGINE_CD = "PC Engine CD"
    THREE_DO = "3DO"
    XBOX = "Xbox"
    XBOX_360 = "Xbox 360"
    PC = "PC"
    DVD_VIDEO = "DVD-Video"


@dataclass
class DiscDetectionResult:
    """Result of disc format detection."""

    platform: DiscPlatform
    confidence: float  # 0.0 - 1.0
    detection_source: str
    details: str = ""

    @property
    def is_detected(self) -> bool:
        """Return True if platform was detected (not Unknown)."""
        return self.platform != DiscPlatform.UNKNOWN


# Magic bytes and identifiers
MAGIC_PATTERNS = {
    # ISO9660 Primary Volume Descriptor identifier at offset 1
    b"CD001": "iso9660",
    # PlayStation
    b"PLAYSTATION": "playstation",
    b"PlayStation": "playstation",
    # Sony specific
    b"Sony Computer Entertainment": "sony",
    # Sega
    b"SEGA SEGASATURN": "saturn",
    b"SEGASATURN": "saturn",
    b"SEGADISCSYSTEM": "segacd",
    b"SEGA MEGA DRIVE": "megacd",
    b"SEGA GENESIS": "megacd",
    # PC Engine
    b"PC Engine CD-ROM SYSTEM": "pce_cd",
    b"NEC Home Electronics": "pce_cd",
    # 3DO
    b"opera_fs": "3do",
    b"\x01\x5a\x5a\x5a\x5a\x5a\x01": "3do",
    # Xbox
    b"MICROSOFT*XBOX*MEDIA": "xbox",
    b"XBOX DVD": "xbox",
}

# PS2 disc magic at offset 0x00028000 (sector 160)
PS2_SYSTEM_CNF_MAGIC = b"BOOT2"
PS1_SYSTEM_CNF_MAGIC = b"BOOT"

# Sector sizes
SECTOR_2048 = 2048
SECTOR_2352 = 2352  # Raw CD sector with header/ecc


def detect_disc_format(file_path: str | Path, max_read_bytes: int = 65536) -> DiscDetectionResult:
    """Detect disc image platform by analyzing file headers.

    Args:
        file_path: Path to the disc image file (.iso, .bin, .img)
        max_read_bytes: Maximum bytes to read for analysis (default 64KB)

    Returns:
        DiscDetectionResult with detected platform and confidence
    """
    path = Path(file_path)

    if not path.exists():
        return DiscDetectionResult(
            platform=DiscPlatform.UNKNOWN,
            confidence=0.0,
            detection_source="error",
            details=f"File not found: {path}",
        )

    if not path.is_file():
        return DiscDetectionResult(
            platform=DiscPlatform.UNKNOWN,
            confidence=0.0,
            detection_source="error",
            details=f"Not a file: {path}",
        )

    ext = path.suffix.lower()

    try:
        with open(path, "rb") as f:
            # Read initial header
            header = f.read(min(max_read_bytes, os.path.getsize(path)))

            # Try different detection strategies
            result = _detect_from_header(header, ext)
            if result.is_detected:
                return result

            # Try reading at ISO9660 PVD offset (sector 16)
            if len(header) >= 0x8000 + 2048:
                pvd_result = _detect_from_pvd(header[0x8000 : 0x8000 + 2048])
                if pvd_result.is_detected:
                    return pvd_result

            # Try raw sector format (2352 bytes/sector)
            if len(header) >= 16 * SECTOR_2352 + 2352:
                raw_offset = 16 * SECTOR_2352 + 16  # Sector 16 + sync header
                raw_pvd = header[raw_offset : raw_offset + 2048]
                pvd_result = _detect_from_pvd(raw_pvd)
                if pvd_result.is_detected:
                    pvd_result.details += " (raw sector format)"
                    return pvd_result

            # Check for PS1/PS2 SYSTEM.CNF content
            ps_result = _detect_playstation_system_cnf(f, ext)
            if ps_result.is_detected:
                return ps_result

    except (OSError, IOError) as e:
        return DiscDetectionResult(
            platform=DiscPlatform.UNKNOWN,
            confidence=0.0,
            detection_source="error",
            details=f"Read error: {e}",
        )

    # Fallback based on extension alone (low confidence)
    return _fallback_by_extension(ext)


def _detect_from_header(header: bytes, ext: str) -> DiscDetectionResult:
    """Detect platform from raw header bytes."""
    # Check for Sega Saturn (IP.BIN at sector 0)
    if header[:16] == b"SEGA SEGASATURN ":
        return DiscDetectionResult(
            platform=DiscPlatform.SATURN,
            confidence=0.95,
            detection_source="header-magic",
            details="SEGA SEGASATURN identifier at sector 0",
        )

    # Check for Sega CD/Mega CD
    if b"SEGADISCSYSTEM" in header[:2048]:
        return DiscDetectionResult(
            platform=DiscPlatform.SEGACD,
            confidence=0.95,
            detection_source="header-magic",
            details="SEGADISCSYSTEM identifier found",
        )

    if b"SEGA MEGA DRIVE" in header[:2048] or b"SEGA GENESIS" in header[:2048]:
        return DiscDetectionResult(
            platform=DiscPlatform.SEGACD,
            confidence=0.90,
            detection_source="header-magic",
            details="SEGA MEGA DRIVE/GENESIS identifier",
        )

    # Check for 3DO
    if header[:7] == b"\x01\x5a\x5a\x5a\x5a\x5a\x01" or b"opera_fs" in header[:512]:
        return DiscDetectionResult(
            platform=DiscPlatform.THREE_DO,
            confidence=0.95,
            detection_source="header-magic",
            details="3DO filesystem signature",
        )

    # Check for Xbox
    if b"MICROSOFT*XBOX*MEDIA" in header[:65536]:
        return DiscDetectionResult(
            platform=DiscPlatform.XBOX,
            confidence=0.95,
            detection_source="header-magic",
            details="Xbox media identifier",
        )

    # Check for PC Engine CD
    if b"PC Engine CD-ROM SYSTEM" in header[:4096] or b"NEC Home Electronics" in header[:4096]:
        return DiscDetectionResult(
            platform=DiscPlatform.PC_ENGINE_CD,
            confidence=0.90,
            detection_source="header-magic",
            details="PC Engine CD identifier",
        )

    return DiscDetectionResult(
        platform=DiscPlatform.UNKNOWN,
        confidence=0.0,
        detection_source="header",
        details="No known magic found in header",
    )


def _detect_from_pvd(pvd_data: bytes) -> DiscDetectionResult:
    """Detect platform from ISO9660 Primary Volume Descriptor."""
    if len(pvd_data) < 128:
        return DiscDetectionResult(
            platform=DiscPlatform.UNKNOWN,
            confidence=0.0,
            detection_source="pvd",
            details="PVD too short",
        )

    # Check for ISO9660 magic (CD001 at offset 1)
    if pvd_data[1:6] != b"CD001":
        return DiscDetectionResult(
            platform=DiscPlatform.UNKNOWN,
            confidence=0.0,
            detection_source="pvd",
            details="Not ISO9660 format",
        )

    # System Identifier is at offset 8, 32 bytes
    system_id = pvd_data[8:40].decode("ascii", errors="ignore").strip()

    # Volume Identifier is at offset 40, 32 bytes
    volume_id = pvd_data[40:72].decode("ascii", errors="ignore").strip()

    # Publisher is at offset 318, 128 bytes
    publisher = pvd_data[318:446].decode("ascii", errors="ignore").strip() if len(pvd_data) > 446 else ""

    # PlayStation detection
    if "PLAYSTATION" in system_id.upper():
        # Distinguish PS1 vs PS2
        if "2" in system_id or "PS2" in volume_id.upper():
            return DiscDetectionResult(
                platform=DiscPlatform.PS2,
                confidence=0.95,
                detection_source="pvd-system-id",
                details=f"System ID: {system_id}",
            )
        return DiscDetectionResult(
            platform=DiscPlatform.PS1,
            confidence=0.90,
            detection_source="pvd-system-id",
            details=f"System ID: {system_id}",
        )

    # Sony in publisher
    if "SONY" in publisher.upper() and "PLAYSTATION" in publisher.upper():
        return DiscDetectionResult(
            platform=DiscPlatform.PS1,
            confidence=0.80,
            detection_source="pvd-publisher",
            details=f"Publisher: {publisher[:50]}",
        )

    # PSP detection
    if "PSP" in system_id.upper() or "PSP_GAME" in volume_id.upper():
        return DiscDetectionResult(
            platform=DiscPlatform.PSP,
            confidence=0.95,
            detection_source="pvd-system-id",
            details=f"System ID: {system_id}",
        )

    # DVD-Video detection
    if "DVDVIDEO" in system_id.upper() or volume_id.upper().startswith("DVD_VIDEO"):
        return DiscDetectionResult(
            platform=DiscPlatform.DVD_VIDEO,
            confidence=0.90,
            detection_source="pvd-volume-id",
            details=f"Volume ID: {volume_id}",
        )

    # Xbox 360 detection
    if "XBOX" in system_id.upper() or "XBOX" in volume_id.upper():
        return DiscDetectionResult(
            platform=DiscPlatform.XBOX_360,
            confidence=0.85,
            detection_source="pvd-system-id",
            details=f"System ID: {system_id}",
        )

    # Generic PC ISO (fallback for ISO9660 without specific markers)
    return DiscDetectionResult(
        platform=DiscPlatform.PC,
        confidence=0.50,
        detection_source="pvd-generic",
        details=f"Generic ISO9660, System: {system_id}, Volume: {volume_id}",
    )


def _detect_playstation_system_cnf(f: BinaryIO, ext: str) -> DiscDetectionResult:
    """Try to find and parse SYSTEM.CNF for PlayStation detection."""
    try:
        # Reset to beginning
        f.seek(0)

        # Read more data to search for SYSTEM.CNF content
        data = f.read(2 * 1024 * 1024)  # 2MB should be enough

        # Look for BOOT2 (PS2) or BOOT (PS1) pattern
        if b"BOOT2" in data:
            return DiscDetectionResult(
                platform=DiscPlatform.PS2,
                confidence=0.90,
                detection_source="system-cnf",
                details="BOOT2 directive found (PS2)",
            )

        if b"BOOT=" in data or b"BOOT =" in data:
            # Check if it's not BOOT2
            boot_idx = data.find(b"BOOT")
            if boot_idx != -1 and data[boot_idx : boot_idx + 5] != b"BOOT2":
                return DiscDetectionResult(
                    platform=DiscPlatform.PS1,
                    confidence=0.85,
                    detection_source="system-cnf",
                    details="BOOT directive found (PS1)",
                )

    except Exception:
        pass

    return DiscDetectionResult(
        platform=DiscPlatform.UNKNOWN,
        confidence=0.0,
        detection_source="system-cnf",
        details="No SYSTEM.CNF markers found",
    )


def _fallback_by_extension(ext: str) -> DiscDetectionResult:
    """Low-confidence fallback based purely on extension."""
    ext_map = {
        ".iso": (DiscPlatform.UNKNOWN, 0.1, "Could be PS1/PS2/Saturn/PC/etc."),
        ".bin": (DiscPlatform.UNKNOWN, 0.1, "Could be PS1/SegaCD/Saturn/etc."),
        ".img": (DiscPlatform.UNKNOWN, 0.1, "Generic disc image"),
        ".mdf": (DiscPlatform.PC, 0.3, "Alcohol 120% format, likely PC"),
        ".nrg": (DiscPlatform.PC, 0.3, "Nero format, likely PC"),
        ".cdi": (DiscPlatform.DREAMCAST, 0.7, "DiscJuggler format, often Dreamcast"),
        ".gdi": (DiscPlatform.DREAMCAST, 0.9, "GD-ROM format, Dreamcast"),
        ".chd": (DiscPlatform.UNKNOWN, 0.2, "MAME CHD, platform varies"),
        ".cso": (DiscPlatform.PSP, 0.8, "Compressed ISO, usually PSP"),
        ".pbp": (DiscPlatform.PSP, 0.9, "PSP EBOOT format"),
        ".pkg": (DiscPlatform.PS3, 0.7, "PS3/PS4 package"),
    }

    if ext in ext_map:
        platform, conf, details = ext_map[ext]
        return DiscDetectionResult(
            platform=platform,
            confidence=conf,
            detection_source="extension-fallback",
            details=details,
        )

    return DiscDetectionResult(
        platform=DiscPlatform.UNKNOWN,
        confidence=0.0,
        detection_source="extension-fallback",
        details=f"Unknown extension: {ext}",
    )


def detect_bin_with_cue(bin_path: str | Path, cue_path: str | Path) -> DiscDetectionResult:
    """Detect platform for a .bin file using its associated .cue file.

    The .cue file can provide context (game name, etc.) that helps identification.
    Also reads the .bin header directly.

    Args:
        bin_path: Path to the .bin file
        cue_path: Path to the associated .cue file

    Returns:
        DiscDetectionResult
    """
    # First try header detection on the bin file
    result = detect_disc_format(bin_path)
    if result.is_detected and result.confidence >= 0.8:
        return result

    # Parse cue file for additional context
    cue_path = Path(cue_path)
    if cue_path.exists():
        try:
            content = cue_path.read_text(encoding="utf-8", errors="ignore")
            content_upper = content.upper()

            # Look for platform hints in comments or titles
            if "PLAYSTATION" in content_upper or "PSX" in content_upper:
                return DiscDetectionResult(
                    platform=DiscPlatform.PS1,
                    confidence=0.75,
                    detection_source="cue-content",
                    details="PlayStation reference in cue file",
                )

            if "SATURN" in content_upper:
                return DiscDetectionResult(
                    platform=DiscPlatform.SATURN,
                    confidence=0.75,
                    detection_source="cue-content",
                    details="Saturn reference in cue file",
                )

            if "SEGA CD" in content_upper or "MEGACD" in content_upper or "MEGA-CD" in content_upper:
                return DiscDetectionResult(
                    platform=DiscPlatform.SEGACD,
                    confidence=0.75,
                    detection_source="cue-content",
                    details="Sega CD reference in cue file",
                )

            if "PC ENGINE" in content_upper or "TURBOGRAFX" in content_upper:
                return DiscDetectionResult(
                    platform=DiscPlatform.PC_ENGINE_CD,
                    confidence=0.75,
                    detection_source="cue-content",
                    details="PC Engine reference in cue file",
                )

        except Exception:
            pass

    return result


def is_disc_image_extension(ext: str) -> bool:
    """Check if extension is a known disc image format."""
    disc_extensions = {
        ".iso",
        ".bin",
        ".img",
        ".mdf",
        ".mds",
        ".nrg",
        ".cdi",
        ".gdi",
        ".chd",
        ".cue",
        ".cso",
        ".pbp",
        ".pkg",
        ".ecm",
    }
    return ext.lower() in disc_extensions


def needs_disambiguation(ext: str) -> bool:
    """Check if this extension requires header sniffing for platform detection."""
    ambiguous_extensions = {".iso", ".bin", ".img", ".chd"}
    return ext.lower() in ambiguous_extensions
