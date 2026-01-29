"""CHD (MAME Compressed Hunks of Data) metadata extraction.

This module parses CHD file headers to determine the disc/media type
and extract relevant metadata for sorting purposes.

CHD Format Overview:
- Magic: "MComprHD" (8 bytes)
- Version 1-5 supported
- Header contains: flags, compression, hunk size, total hunks, logical bytes
- Metadata area contains CD/GD/HDD track info

Supported media types:
- CDROM: PlayStation, Saturn, SegaCD, PC Engine CD, etc.
- GDROM: Dreamcast
- HDD: PlayStation 2, Xbox

References:
- MAME source: src/lib/util/chd.h
- CHD format: https://wiki.mamedev.org/index.php/CHD
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import BinaryIO, Optional, List


class CHDMediaType(Enum):
    """CHD media type based on metadata tags."""
    
    UNKNOWN = "Unknown"
    CDROM = "CD-ROM"
    GDROM = "GD-ROM"
    HDD = "Hard Disk"
    LASERDISC = "LaserDisc"
    DVD = "DVD"


@dataclass
class CHDMetadata:
    """Parsed CHD header and metadata information."""
    
    version: int
    """CHD format version (1-5)."""
    
    media_type: CHDMediaType
    """Detected media type from metadata tags."""
    
    logical_bytes: int
    """Total logical size of the uncompressed data."""
    
    hunk_size: int
    """Size of each hunk (compression unit)."""
    
    total_hunks: int
    """Total number of hunks in the file."""
    
    compression: List[str]
    """Compression codec(s) used."""
    
    sha1: Optional[str]
    """SHA1 hash of the uncompressed data (if present)."""
    
    parent_sha1: Optional[str]
    """SHA1 of parent CHD for delta images."""
    
    track_count: int
    """Number of tracks (for CD/GD media)."""
    
    raw_metadata: List[str]
    """Raw metadata tags found in the file."""


# CHD magic signature
CHD_MAGIC = b"MComprHD"

# CHD header sizes by version
CHD_HEADER_SIZES = {
    1: 76,
    2: 80,
    3: 120,
    4: 108,
    5: 124,
}

# Compression codec fourcc codes (CHD v5)
COMPRESSION_CODECS = {
    0x00000000: "none",
    0x7A6C6962: "zlib",  # 'zlib'
    0x6C7A6D61: "lzma",  # 'lzma'
    0x68756666: "huff",  # 'huff'
    0x666C6163: "flac",  # 'flac'
    0x63647A6C: "cdzl",  # CD zlib
    0x63646C7A: "cdlz",  # CD lzma
    0x6364666C: "cdfl",  # CD flac
}

# Metadata tag fourcc codes
METADATA_TAGS = {
    b"GDDD": "gd_old_metadata",      # Old GD-ROM format
    b"CHCD": "cdrom_old_metadata",   # Old CD-ROM format
    b"CHTR": "cdrom_track",          # CD-ROM track info
    b"CHT2": "cdrom_track_v2",       # CD-ROM track v2
    b"CHGD": "gdrom_old",            # Old GD-ROM
    b"CHGT": "gdrom_track",          # GD-ROM track
    b"IDNT": "hard_disk_ident",      # ATA identify
    b"KEY ": "hard_disk_key",        # Encryption key
    b"PCMK": "hard_disk_pcmcia",     # PCMCIA CIS
    b"CIS ": "pcmcia_cis",           # PCMCIA CIS
    b"AVLD": "av_laserdisc",         # LaserDisc
    b"AVMT": "av_metadata",          # AV metadata
}


def detect_chd_media_type(file_path: str | Path) -> Optional[CHDMetadata]:
    """Detect the media type and extract metadata from a CHD file.
    
    Args:
        file_path: Path to the CHD file.
        
    Returns:
        CHDMetadata if valid CHD, None otherwise.
    """
    path = Path(file_path)
    if not path.is_file():
        return None
    
    try:
        with open(path, "rb") as f:
            return _parse_chd_header(f, path.stat().st_size)
    except (OSError, IOError, struct.error):
        return None


def _parse_chd_header(f: BinaryIO, file_size: int) -> Optional[CHDMetadata]:
    """Parse CHD header from an open file handle.
    
    Args:
        f: Binary file handle positioned at start.
        file_size: Total file size for bounds checking.
        
    Returns:
        CHDMetadata or None if not a valid CHD.
    """
    # Read and verify magic
    magic = f.read(8)
    if magic != CHD_MAGIC:
        return None
    
    # Read header length and version
    header_data = f.read(8)
    if len(header_data) < 8:
        return None
    
    header_len, version = struct.unpack(">II", header_data)
    
    if version not in CHD_HEADER_SIZES:
        # Unknown version, try to continue with basic info
        return CHDMetadata(
            version=version,
            media_type=CHDMediaType.UNKNOWN,
            logical_bytes=0,
            hunk_size=0,
            total_hunks=0,
            compression=["unknown"],
            sha1=None,
            parent_sha1=None,
            track_count=0,
            raw_metadata=[],
        )
    
    # Seek back to start and read full header
    f.seek(0)
    header_size = max(header_len, CHD_HEADER_SIZES.get(version, 124))
    header = f.read(min(header_size, 256))
    
    if version <= 3:
        return _parse_v1_to_v3(header, version, f, file_size)
    elif version == 4:
        return _parse_v4(header, f, file_size)
    else:  # version 5
        return _parse_v5(header, f, file_size)


def _parse_v1_to_v3(header: bytes, version: int, f: BinaryIO, file_size: int) -> CHDMetadata:
    """Parse CHD version 1-3 headers."""
    # V1-V3 header layout (big-endian):
    # 0-7: magic
    # 8-11: header length
    # 12-15: version
    # 16-19: flags
    # 20-23: compression
    # 24-27: hunk size (v1: sectors per hunk * 512)
    # 28-35: total hunks (v3: 64-bit)
    # varies: logical bytes
    
    flags = struct.unpack_from(">I", header, 16)[0] if len(header) > 20 else 0
    compression_code = struct.unpack_from(">I", header, 20)[0] if len(header) > 24 else 0
    
    hunk_size = 0
    total_hunks = 0
    logical_bytes = 0
    
    if version == 1:
        if len(header) >= 76:
            hunk_size = struct.unpack_from(">I", header, 24)[0] * 512
            total_hunks = struct.unpack_from(">I", header, 28)[0]
            logical_bytes = struct.unpack_from(">Q", header, 32)[0] if len(header) >= 40 else hunk_size * total_hunks
    elif version == 2:
        if len(header) >= 80:
            hunk_size = struct.unpack_from(">I", header, 24)[0]
            total_hunks = struct.unpack_from(">I", header, 28)[0]
            logical_bytes = struct.unpack_from(">Q", header, 32)[0] if len(header) >= 40 else hunk_size * total_hunks
    elif version == 3:
        if len(header) >= 120:
            hunk_size = struct.unpack_from(">I", header, 24)[0]
            total_hunks = struct.unpack_from(">Q", header, 28)[0]
            logical_bytes = struct.unpack_from(">Q", header, 36)[0]
    
    compression = [_decode_compression(compression_code)]
    
    # Read metadata to determine media type
    media_type, track_count, raw_metadata = _scan_metadata(f, file_size, header)
    
    return CHDMetadata(
        version=version,
        media_type=media_type,
        logical_bytes=logical_bytes,
        hunk_size=hunk_size,
        total_hunks=total_hunks,
        compression=compression,
        sha1=None,  # V1-3 don't have SHA1 in header
        parent_sha1=None,
        track_count=track_count,
        raw_metadata=raw_metadata,
    )


def _parse_v4(header: bytes, f: BinaryIO, file_size: int) -> CHDMetadata:
    """Parse CHD version 4 header."""
    # V4 header layout (big-endian):
    # 0-7: magic
    # 8-11: header length
    # 12-15: version (4)
    # 16-19: flags
    # 20-23: compression
    # 24-27: total hunks
    # 28-35: logical bytes
    # 36-43: meta offset
    # 44-47: hunk bytes
    # 48-67: SHA1
    # 68-87: parent SHA1
    # 88-107: raw SHA1
    
    if len(header) < 108:
        return _empty_metadata(4)
    
    flags = struct.unpack_from(">I", header, 16)[0]
    compression_code = struct.unpack_from(">I", header, 20)[0]
    total_hunks = struct.unpack_from(">I", header, 24)[0]
    logical_bytes = struct.unpack_from(">Q", header, 28)[0]
    hunk_size = struct.unpack_from(">I", header, 44)[0]
    
    sha1 = header[48:68].hex() if len(header) >= 68 else None
    parent_sha1 = header[68:88].hex() if len(header) >= 88 else None
    
    # Check if SHA1 is all zeros (no parent)
    if parent_sha1 and all(b == 0 for b in header[68:88]):
        parent_sha1 = None
    
    compression = [_decode_compression(compression_code)]
    
    # Read metadata
    media_type, track_count, raw_metadata = _scan_metadata(f, file_size, header)
    
    return CHDMetadata(
        version=4,
        media_type=media_type,
        logical_bytes=logical_bytes,
        hunk_size=hunk_size,
        total_hunks=total_hunks,
        compression=compression,
        sha1=sha1 if sha1 and sha1 != "0" * 40 else None,
        parent_sha1=parent_sha1,
        track_count=track_count,
        raw_metadata=raw_metadata,
    )


def _parse_v5(header: bytes, f: BinaryIO, file_size: int) -> CHDMetadata:
    """Parse CHD version 5 header."""
    # V5 header layout (big-endian):
    # 0-7: magic
    # 8-11: header length
    # 12-15: version (5)
    # 16-19: compressors[0]
    # 20-23: compressors[1]
    # 24-27: compressors[2]
    # 28-31: compressors[3]
    # 32-39: logical bytes
    # 40-47: map offset
    # 48-55: meta offset
    # 56-59: hunk bytes
    # 60-63: unit bytes
    # 64-83: raw SHA1
    # 84-103: SHA1
    # 104-123: parent SHA1
    
    if len(header) < 124:
        return _empty_metadata(5)
    
    # Parse compression codecs (up to 4)
    compression = []
    for i in range(4):
        codec = struct.unpack_from(">I", header, 16 + i * 4)[0]
        if codec != 0:
            compression.append(_decode_compression(codec))
    
    if not compression:
        compression = ["none"]
    
    logical_bytes = struct.unpack_from(">Q", header, 32)[0]
    hunk_size = struct.unpack_from(">I", header, 56)[0]
    total_hunks = (logical_bytes + hunk_size - 1) // hunk_size if hunk_size > 0 else 0
    
    sha1 = header[84:104].hex() if len(header) >= 104 else None
    parent_sha1 = header[104:124].hex() if len(header) >= 124 else None
    
    # Check if SHA1s are all zeros
    if sha1 and all(b == 0 for b in header[84:104]):
        sha1 = None
    if parent_sha1 and all(b == 0 for b in header[104:124]):
        parent_sha1 = None
    
    # Read metadata
    media_type, track_count, raw_metadata = _scan_metadata(f, file_size, header)
    
    return CHDMetadata(
        version=5,
        media_type=media_type,
        logical_bytes=logical_bytes,
        hunk_size=hunk_size,
        total_hunks=int(total_hunks),
        compression=compression,
        sha1=sha1,
        parent_sha1=parent_sha1,
        track_count=track_count,
        raw_metadata=raw_metadata,
    )


def _scan_metadata(f: BinaryIO, file_size: int, header: bytes) -> tuple[CHDMediaType, int, List[str]]:
    """Scan CHD metadata area to determine media type.
    
    Args:
        f: File handle.
        file_size: Total file size.
        header: Already-read header bytes.
        
    Returns:
        Tuple of (media_type, track_count, raw_metadata_tags).
    """
    media_type = CHDMediaType.UNKNOWN
    track_count = 0
    raw_metadata: List[str] = []
    
    # Try to find metadata offset from header
    version = struct.unpack_from(">I", header, 12)[0] if len(header) >= 16 else 0
    
    meta_offset = 0
    if version == 4 and len(header) >= 44:
        meta_offset = struct.unpack_from(">Q", header, 36)[0]
    elif version == 5 and len(header) >= 56:
        meta_offset = struct.unpack_from(">Q", header, 48)[0]
    
    if meta_offset == 0 or meta_offset >= file_size:
        # Fallback: try to detect from file size heuristics
        media_type = _guess_media_type_from_size(file_size)
        return media_type, track_count, raw_metadata
    
    # Read metadata entries
    try:
        f.seek(meta_offset)
        
        # Metadata format: 4-byte tag, 4-byte flags (bit 0 = more entries), 8-byte next offset, 8-byte length
        max_entries = 100  # Safety limit
        entries_read = 0
        
        while entries_read < max_entries:
            entry_header = f.read(24)
            if len(entry_header) < 24:
                break
            
            tag = entry_header[0:4]
            flags = struct.unpack_from(">I", entry_header, 4)[0]
            next_offset = struct.unpack_from(">Q", entry_header, 8)[0]
            length = struct.unpack_from(">Q", entry_header, 16)[0]
            
            tag_name = METADATA_TAGS.get(tag, tag.decode("ascii", errors="replace"))
            raw_metadata.append(tag_name)
            
            # Determine media type from tags
            if tag in (b"CHCD", b"CHTR", b"CHT2"):
                media_type = CHDMediaType.CDROM
                track_count += 1
            elif tag in (b"GDDD", b"CHGD", b"CHGT"):
                media_type = CHDMediaType.GDROM
                track_count += 1
            elif tag in (b"IDNT", b"KEY "):
                media_type = CHDMediaType.HDD
            elif tag == b"AVLD":
                media_type = CHDMediaType.LASERDISC
            
            # Check if more entries
            if flags & 1 == 0 or next_offset == 0:
                break
            
            f.seek(next_offset)
            entries_read += 1
            
    except (OSError, struct.error):
        pass
    
    # If still unknown, guess from size
    if media_type == CHDMediaType.UNKNOWN:
        media_type = _guess_media_type_from_size(file_size)
    
    return media_type, track_count, raw_metadata


def _guess_media_type_from_size(file_size: int) -> CHDMediaType:
    """Guess media type from file size when metadata is unavailable.
    
    Rough heuristics:
    - CD: 500MB - 900MB compressed (~700MB raw)
    - GD: 800MB - 1.5GB compressed (~1.2GB raw)
    - DVD: 2GB+ compressed (4.7GB+ raw)
    - HDD: varies widely
    """
    mb = file_size / (1024 * 1024)
    
    if mb < 100:
        # Very small, could be anything
        return CHDMediaType.UNKNOWN
    elif mb < 1000:
        # Likely CD-ROM
        return CHDMediaType.CDROM
    elif mb < 1800:
        # Could be GD-ROM or large CD
        return CHDMediaType.GDROM
    elif mb < 5000:
        # Likely DVD
        return CHDMediaType.DVD
    else:
        # Likely HDD image
        return CHDMediaType.HDD


def _decode_compression(code: int) -> str:
    """Decode compression fourcc code to string."""
    if code in COMPRESSION_CODECS:
        return COMPRESSION_CODECS[code]
    
    # Try to decode as ASCII fourcc
    try:
        chars = struct.pack(">I", code)
        return chars.decode("ascii").strip()
    except (UnicodeDecodeError, struct.error):
        return f"0x{code:08x}"


def _empty_metadata(version: int) -> CHDMetadata:
    """Create empty metadata for parse failures."""
    return CHDMetadata(
        version=version,
        media_type=CHDMediaType.UNKNOWN,
        logical_bytes=0,
        hunk_size=0,
        total_hunks=0,
        compression=["unknown"],
        sha1=None,
        parent_sha1=None,
        track_count=0,
        raw_metadata=[],
    )


def get_likely_platform_from_chd(metadata: CHDMetadata) -> Optional[str]:
    """Suggest likely platform based on CHD media type and size.
    
    This is a heuristic helper - actual identification should use DAT matching.
    
    Args:
        metadata: Parsed CHD metadata.
        
    Returns:
        Platform name hint or None.
    """
    if metadata.media_type == CHDMediaType.GDROM:
        return "Dreamcast"
    
    if metadata.media_type == CHDMediaType.HDD:
        # HDD could be PS2 or Xbox
        return None  # Ambiguous
    
    if metadata.media_type == CHDMediaType.LASERDISC:
        return "LaserDisc"
    
    if metadata.media_type == CHDMediaType.DVD:
        # Could be PS2, Xbox, Wii, etc.
        return None  # Ambiguous
    
    if metadata.media_type == CHDMediaType.CDROM:
        # Could be many platforms - PS1, Saturn, SegaCD, PCE-CD, etc.
        return None  # Ambiguous
    
    return None
