"""Tests for CHD (Compressed Hunks of Data) metadata extraction.

Tests cover:
- CHD magic validation
- Version 1-5 header parsing
- Media type detection (CD-ROM, GD-ROM, HDD, LaserDisc)
- Compression codec decoding
- Metadata tag scanning
- Size-based heuristics
- Error handling for corrupt/truncated files
"""

import io
import struct
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.core.chd_detection import (
    CHDMediaType,
    CHDMetadata,
    CHD_MAGIC,
    detect_chd_media_type,
    get_likely_platform_from_chd,
    _decode_compression,
    _guess_media_type_from_size,
    _parse_chd_header,
)


# =============================================================================
# Fixtures
# =============================================================================

def create_minimal_chd_v5(media_type_tags: list[bytes] | None = None, logical_bytes: int = 700 * 1024 * 1024) -> bytes:
    """Create a minimal CHD v5 file for testing.
    
    Args:
        media_type_tags: Optional metadata tags to include.
        logical_bytes: Logical size of uncompressed data.
        
    Returns:
        Bytes representing a minimal CHD v5 file.
    """
    # V5 header: 124 bytes
    header = bytearray(124)
    
    # Magic
    header[0:8] = CHD_MAGIC
    # Header length
    struct.pack_into(">I", header, 8, 124)
    # Version
    struct.pack_into(">I", header, 12, 5)
    # Compression codecs (zlib)
    struct.pack_into(">I", header, 16, 0x7A6C6962)  # 'zlib'
    # Logical bytes
    struct.pack_into(">Q", header, 32, logical_bytes)
    # Hunk size (2352 for CD sector)
    hunk_size = 2352 * 8
    struct.pack_into(">I", header, 56, hunk_size)
    # Unit bytes
    struct.pack_into(">I", header, 60, 2352)
    
    # Metadata offset (right after header)
    meta_offset = 124
    struct.pack_into(">Q", header, 48, meta_offset)
    
    # Build metadata section
    metadata = bytearray()
    if media_type_tags:
        for i, tag in enumerate(media_type_tags):
            entry = bytearray(24)
            entry[0:4] = tag[:4].ljust(4)[:4]
            # Flags: bit 0 = more entries
            has_more = i < len(media_type_tags) - 1
            struct.pack_into(">I", entry, 4, 1 if has_more else 0)
            # Next offset
            next_off = meta_offset + (i + 1) * 24 if has_more else 0
            struct.pack_into(">Q", entry, 8, next_off)
            # Length
            struct.pack_into(">Q", entry, 16, 0)
            metadata.extend(entry)
    
    return bytes(header) + bytes(metadata)


def create_minimal_chd_v4(logical_bytes: int = 700 * 1024 * 1024) -> bytes:
    """Create a minimal CHD v4 file for testing."""
    # V4 header: 108 bytes
    header = bytearray(108)
    
    # Magic
    header[0:8] = CHD_MAGIC
    # Header length
    struct.pack_into(">I", header, 8, 108)
    # Version
    struct.pack_into(">I", header, 12, 4)
    # Compression (zlib)
    struct.pack_into(">I", header, 20, 0x7A6C6962)
    # Total hunks
    struct.pack_into(">I", header, 24, 1000)
    # Logical bytes
    struct.pack_into(">Q", header, 28, logical_bytes)
    # Hunk size
    struct.pack_into(">I", header, 44, 2352 * 8)
    
    return bytes(header)


# =============================================================================
# Test: Magic Validation
# =============================================================================

class TestCHDMagicValidation:
    """Tests for CHD magic signature validation."""
    
    def test_valid_magic(self, tmp_path: Path):
        """Valid CHD magic should be accepted."""
        chd_file = tmp_path / "test.chd"
        chd_file.write_bytes(create_minimal_chd_v5())
        
        result = detect_chd_media_type(chd_file)
        
        assert result is not None
        assert result.version == 5
    
    def test_invalid_magic_rejected(self, tmp_path: Path):
        """Files without CHD magic should return None."""
        bad_file = tmp_path / "not_chd.bin"
        bad_file.write_bytes(b"NOTACHD!" + b"\x00" * 200)
        
        result = detect_chd_media_type(bad_file)
        
        assert result is None
    
    def test_empty_file(self, tmp_path: Path):
        """Empty files should return None."""
        empty_file = tmp_path / "empty.chd"
        empty_file.write_bytes(b"")
        
        result = detect_chd_media_type(empty_file)
        
        assert result is None
    
    def test_truncated_header(self, tmp_path: Path):
        """Truncated CHD header should return None."""
        truncated = tmp_path / "truncated.chd"
        truncated.write_bytes(CHD_MAGIC + b"\x00" * 4)  # Only 12 bytes
        
        result = detect_chd_media_type(truncated)
        
        assert result is None
    
    def test_nonexistent_file(self, tmp_path: Path):
        """Non-existent file should return None."""
        result = detect_chd_media_type(tmp_path / "nonexistent.chd")
        
        assert result is None


# =============================================================================
# Test: Version Parsing
# =============================================================================

class TestVersionParsing:
    """Tests for CHD version detection and parsing."""
    
    def test_v5_parsing(self, tmp_path: Path):
        """CHD v5 should be parsed correctly."""
        chd_file = tmp_path / "v5.chd"
        chd_file.write_bytes(create_minimal_chd_v5(logical_bytes=800_000_000))
        
        result = detect_chd_media_type(chd_file)
        
        assert result is not None
        assert result.version == 5
        assert result.logical_bytes == 800_000_000
        assert "zlib" in result.compression
    
    def test_v4_parsing(self, tmp_path: Path):
        """CHD v4 should be parsed correctly."""
        chd_file = tmp_path / "v4.chd"
        chd_file.write_bytes(create_minimal_chd_v4(logical_bytes=600_000_000))
        
        result = detect_chd_media_type(chd_file)
        
        assert result is not None
        assert result.version == 4
        assert result.logical_bytes == 600_000_000
    
    def test_unknown_version(self, tmp_path: Path):
        """Unknown CHD version should return basic metadata."""
        chd_file = tmp_path / "future.chd"
        header = bytearray(32)
        header[0:8] = CHD_MAGIC
        struct.pack_into(">I", header, 8, 32)
        struct.pack_into(">I", header, 12, 99)  # Version 99 (future)
        chd_file.write_bytes(bytes(header))
        
        result = detect_chd_media_type(chd_file)
        
        assert result is not None
        assert result.version == 99
        assert result.media_type == CHDMediaType.UNKNOWN


# =============================================================================
# Test: Media Type Detection
# =============================================================================

class TestMediaTypeDetection:
    """Tests for CHD media type detection from metadata tags."""
    
    def test_cdrom_from_chtr_tag(self, tmp_path: Path):
        """CHTR tag should indicate CD-ROM."""
        chd_file = tmp_path / "cdrom.chd"
        chd_file.write_bytes(create_minimal_chd_v5(media_type_tags=[b"CHTR"]))
        
        result = detect_chd_media_type(chd_file)
        
        assert result is not None
        assert result.media_type == CHDMediaType.CDROM
        assert result.track_count >= 1
    
    def test_gdrom_from_chgd_tag(self, tmp_path: Path):
        """CHGD tag should indicate GD-ROM (Dreamcast)."""
        chd_file = tmp_path / "gdrom.chd"
        chd_file.write_bytes(create_minimal_chd_v5(media_type_tags=[b"CHGD"]))
        
        result = detect_chd_media_type(chd_file)
        
        assert result is not None
        assert result.media_type == CHDMediaType.GDROM
    
    def test_hdd_from_idnt_tag(self, tmp_path: Path):
        """IDNT tag should indicate Hard Disk."""
        chd_file = tmp_path / "hdd.chd"
        chd_file.write_bytes(create_minimal_chd_v5(media_type_tags=[b"IDNT"]))
        
        result = detect_chd_media_type(chd_file)
        
        assert result is not None
        assert result.media_type == CHDMediaType.HDD
    
    def test_laserdisc_from_avld_tag(self, tmp_path: Path):
        """AVLD tag should indicate LaserDisc."""
        chd_file = tmp_path / "ld.chd"
        chd_file.write_bytes(create_minimal_chd_v5(media_type_tags=[b"AVLD"]))
        
        result = detect_chd_media_type(chd_file)
        
        assert result is not None
        assert result.media_type == CHDMediaType.LASERDISC
    
    def test_multiple_track_tags(self, tmp_path: Path):
        """Multiple track tags should increment track count."""
        chd_file = tmp_path / "multi.chd"
        # 3 CD tracks
        chd_file.write_bytes(create_minimal_chd_v5(
            media_type_tags=[b"CHTR", b"CHTR", b"CHTR"]
        ))
        
        result = detect_chd_media_type(chd_file)
        
        assert result is not None
        assert result.media_type == CHDMediaType.CDROM
        assert result.track_count == 3


# =============================================================================
# Test: Size-Based Heuristics
# =============================================================================

class TestSizeHeuristics:
    """Tests for media type guessing from file size."""
    
    def test_small_file_unknown(self):
        """Very small files should be unknown."""
        assert _guess_media_type_from_size(50 * 1024 * 1024) == CHDMediaType.UNKNOWN
    
    def test_cd_size_range(self):
        """500-900MB should guess CD-ROM."""
        assert _guess_media_type_from_size(600 * 1024 * 1024) == CHDMediaType.CDROM
        assert _guess_media_type_from_size(850 * 1024 * 1024) == CHDMediaType.CDROM
    
    def test_gd_size_range(self):
        """1-1.8GB should guess GD-ROM."""
        assert _guess_media_type_from_size(1200 * 1024 * 1024) == CHDMediaType.GDROM
        assert _guess_media_type_from_size(1500 * 1024 * 1024) == CHDMediaType.GDROM
    
    def test_dvd_size_range(self):
        """2-5GB should guess DVD."""
        assert _guess_media_type_from_size(3000 * 1024 * 1024) == CHDMediaType.DVD
        assert _guess_media_type_from_size(4500 * 1024 * 1024) == CHDMediaType.DVD
    
    def test_large_hdd(self):
        """5GB+ should guess HDD."""
        assert _guess_media_type_from_size(10000 * 1024 * 1024) == CHDMediaType.HDD


# =============================================================================
# Test: Compression Codec Decoding
# =============================================================================

class TestCompressionDecoding:
    """Tests for compression codec fourcc decoding."""
    
    def test_known_codecs(self):
        """Known compression codecs should decode correctly."""
        assert _decode_compression(0x7A6C6962) == "zlib"
        assert _decode_compression(0x6C7A6D61) == "lzma"
        assert _decode_compression(0x666C6163) == "flac"
        assert _decode_compression(0x00000000) == "none"
    
    def test_unknown_codec_as_hex(self):
        """Unknown codecs should show as hex."""
        result = _decode_compression(0xDEADBEEF)
        assert "deadbeef" in result.lower() or "DEAD" in result.upper()


# =============================================================================
# Test: Platform Hints
# =============================================================================

class TestPlatformHints:
    """Tests for platform suggestion from CHD metadata."""
    
    def test_gdrom_suggests_dreamcast(self):
        """GD-ROM should suggest Dreamcast."""
        metadata = CHDMetadata(
            version=5,
            media_type=CHDMediaType.GDROM,
            logical_bytes=1_200_000_000,
            hunk_size=18816,
            total_hunks=63000,
            compression=["lzma"],
            sha1=None,
            parent_sha1=None,
            track_count=3,
            raw_metadata=["gdrom_track"],
        )
        
        assert get_likely_platform_from_chd(metadata) == "Dreamcast"
    
    def test_laserdisc_platform(self):
        """LaserDisc should suggest LaserDisc platform."""
        metadata = CHDMetadata(
            version=5,
            media_type=CHDMediaType.LASERDISC,
            logical_bytes=5_000_000_000,
            hunk_size=0,
            total_hunks=0,
            compression=["none"],
            sha1=None,
            parent_sha1=None,
            track_count=0,
            raw_metadata=["av_laserdisc"],
        )
        
        assert get_likely_platform_from_chd(metadata) == "LaserDisc"
    
    def test_cdrom_ambiguous(self):
        """CD-ROM should return None (ambiguous)."""
        metadata = CHDMetadata(
            version=5,
            media_type=CHDMediaType.CDROM,
            logical_bytes=700_000_000,
            hunk_size=18816,
            total_hunks=37000,
            compression=["cdzl"],
            sha1=None,
            parent_sha1=None,
            track_count=20,
            raw_metadata=["cdrom_track"],
        )
        
        # CD-ROM could be PS1, Saturn, SegaCD, PCE-CD, etc.
        assert get_likely_platform_from_chd(metadata) is None
    
    def test_hdd_ambiguous(self):
        """HDD should return None (ambiguous)."""
        metadata = CHDMetadata(
            version=5,
            media_type=CHDMediaType.HDD,
            logical_bytes=40_000_000_000,
            hunk_size=0,
            total_hunks=0,
            compression=["lzma"],
            sha1=None,
            parent_sha1=None,
            track_count=0,
            raw_metadata=["hard_disk_ident"],
        )
        
        # HDD could be PS2 or Xbox
        assert get_likely_platform_from_chd(metadata) is None


# =============================================================================
# Test: Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in CHD parsing."""
    
    def test_io_error_returns_none(self, tmp_path: Path):
        """IOError during read should return None."""
        chd_file = tmp_path / "error.chd"
        chd_file.write_bytes(create_minimal_chd_v5())
        
        with patch("builtins.open", side_effect=IOError("Read error")):
            result = detect_chd_media_type(chd_file)
        
        assert result is None
    
    def test_permission_error(self, tmp_path: Path):
        """Permission denied should return None."""
        chd_file = tmp_path / "noperm.chd"
        chd_file.write_bytes(create_minimal_chd_v5())
        
        with patch("builtins.open", side_effect=PermissionError()):
            result = detect_chd_media_type(chd_file)
        
        assert result is None
    
    def test_struct_error_handling(self, tmp_path: Path):
        """Corrupt data causing struct errors should be handled."""
        chd_file = tmp_path / "corrupt.chd"
        # Valid magic but corrupt header data
        header = CHD_MAGIC + b"\xFF" * 200
        chd_file.write_bytes(header)
        
        # Should not raise, may return None or partial result
        result = detect_chd_media_type(chd_file)
        # Just verify it doesn't crash
        assert result is None or isinstance(result, CHDMetadata)


# =============================================================================
# Test: Real-World Scenarios
# =============================================================================

class TestRealWorldScenarios:
    """Tests simulating real-world CHD files."""
    
    def test_dreamcast_gdrom_scenario(self, tmp_path: Path):
        """Dreamcast GD-ROM CHD should be identified correctly."""
        # Dreamcast GD-ROM: ~1.2GB, GD track metadata
        chd_file = tmp_path / "sonic_adventure.chd"
        chd_file.write_bytes(create_minimal_chd_v5(
            media_type_tags=[b"CHGD", b"CHGT", b"CHGT", b"CHGT"],
            logical_bytes=1_200_000_000,
        ))
        
        result = detect_chd_media_type(chd_file)
        
        assert result is not None
        assert result.media_type == CHDMediaType.GDROM
        assert get_likely_platform_from_chd(result) == "Dreamcast"
    
    def test_ps1_cdrom_scenario(self, tmp_path: Path):
        """PS1 CD-ROM CHD should be identified as CD-ROM."""
        # PS1 game: ~700MB, CD track metadata
        chd_file = tmp_path / "ff7_disc1.chd"
        chd_file.write_bytes(create_minimal_chd_v5(
            media_type_tags=[b"CHT2"] * 10,  # Multi-track CD
            logical_bytes=700_000_000,
        ))
        
        result = detect_chd_media_type(chd_file)
        
        assert result is not None
        assert result.media_type == CHDMediaType.CDROM
        assert result.track_count == 10
        # PS1 is ambiguous from CD-ROM alone
        assert get_likely_platform_from_chd(result) is None
    
    def test_saturn_cdrom_scenario(self, tmp_path: Path):
        """Saturn CD-ROM CHD should be identified as CD-ROM."""
        # Saturn game: ~700MB, CD track metadata
        chd_file = tmp_path / "nights.chd"
        chd_file.write_bytes(create_minimal_chd_v5(
            media_type_tags=[b"CHCD", b"CHTR", b"CHTR"],
            logical_bytes=650_000_000,
        ))
        
        result = detect_chd_media_type(chd_file)
        
        assert result is not None
        assert result.media_type == CHDMediaType.CDROM
    
    def test_ps2_dvd_scenario(self, tmp_path: Path):
        """PS2 DVD CHD should be guessed as DVD from size."""
        # PS2 DVD: ~4GB, no specific metadata (or HDD metadata if installed)
        chd_file = tmp_path / "gow.chd"
        # No metadata tags, rely on size heuristic
        data = create_minimal_chd_v5(logical_bytes=4_000_000_000)
        chd_file.write_bytes(data)
        
        result = detect_chd_media_type(chd_file)
        
        assert result is not None
        # Should guess DVD from size
        assert result.media_type in (CHDMediaType.UNKNOWN, CHDMediaType.DVD)
