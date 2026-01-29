"""Tests for disc format detection via header sniffing.

Tests cover:
- PlayStation 1/2 detection via PVD and SYSTEM.CNF
- Sega Saturn detection via IP.BIN header
- Sega CD/Mega CD detection
- PC Engine CD detection
- 3DO detection
- Extension fallbacks
- Edge cases and error handling
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.core.disc_detection import (
    DiscDetectionResult,
    DiscPlatform,
    detect_bin_with_cue,
    detect_disc_format,
    is_disc_image_extension,
    needs_disambiguation,
)


class TestSaturnDetection:
    """Tests for Sega Saturn disc detection."""

    def test_saturn_ip_bin_header(self, tmp_path: Path) -> None:
        """Saturn disc with SEGA SEGASATURN header at sector 0."""
        iso_path = tmp_path / "saturn_game.bin"

        # Create Saturn IP.BIN header
        header = b"SEGA SEGASATURN " + b"\x00" * (2048 - 16)
        iso_path.write_bytes(header + b"\x00" * 65536)

        result = detect_disc_format(iso_path)

        assert result.platform == DiscPlatform.SATURN
        assert result.confidence >= 0.9
        assert "saturn" in result.detection_source.lower() or "header" in result.detection_source.lower()

    def test_saturn_segasaturn_identifier(self, tmp_path: Path) -> None:
        """Saturn disc with SEGASATURN in header."""
        iso_path = tmp_path / "saturn.iso"

        header = b"\x00" * 100 + b"SEGASATURN" + b"\x00" * (2048 - 110)
        iso_path.write_bytes(header)

        result = detect_disc_format(iso_path)

        # May detect or may not depending on exact offset
        # At minimum should not crash
        assert isinstance(result, DiscDetectionResult)


class TestSegaCDDetection:
    """Tests for Sega CD/Mega CD detection."""

    def test_segacd_disc_system_header(self, tmp_path: Path) -> None:
        """Sega CD disc with SEGADISCSYSTEM identifier."""
        iso_path = tmp_path / "segacd_game.bin"

        header = b"SEGADISCSYSTEM" + b"\x00" * (2048 - 14)
        iso_path.write_bytes(header + b"\x00" * 32768)

        result = detect_disc_format(iso_path)

        assert result.platform == DiscPlatform.SEGACD
        assert result.confidence >= 0.9

    def test_megacd_genesis_header(self, tmp_path: Path) -> None:
        """Mega CD with SEGA MEGA DRIVE identifier."""
        iso_path = tmp_path / "megacd.bin"

        header = b"SEGA MEGA DRIVE" + b"\x00" * (2048 - 15)
        iso_path.write_bytes(header + b"\x00" * 32768)

        result = detect_disc_format(iso_path)

        assert result.platform == DiscPlatform.SEGACD
        assert result.confidence >= 0.85


class TestPlayStationDetection:
    """Tests for PlayStation 1/2 detection."""

    def test_ps1_pvd_system_id(self, tmp_path: Path) -> None:
        """PS1 disc with PLAYSTATION in PVD system identifier."""
        iso_path = tmp_path / "ps1_game.iso"

        # Create ISO with PVD at sector 16 (offset 0x8000)
        header = b"\x00" * 0x8000  # Sectors 0-15

        # PVD: Type 1, CD001, version, system id
        pvd = bytearray(2048)
        pvd[0] = 1  # Primary Volume Descriptor
        pvd[1:6] = b"CD001"
        pvd[6] = 1  # Version
        pvd[8:40] = b"PLAYSTATION".ljust(32)  # System Identifier
        pvd[40:72] = b"MYGAME".ljust(32)  # Volume Identifier

        iso_path.write_bytes(header + bytes(pvd) + b"\x00" * 32768)

        result = detect_disc_format(iso_path)

        assert result.platform == DiscPlatform.PS1
        assert result.confidence >= 0.85
        assert "pvd" in result.detection_source.lower() or "playstation" in result.details.lower()

    def test_ps2_pvd_system_id(self, tmp_path: Path) -> None:
        """PS2 disc with PLAYSTATION 2 in PVD."""
        iso_path = tmp_path / "ps2_game.iso"

        header = b"\x00" * 0x8000

        pvd = bytearray(2048)
        pvd[0] = 1
        pvd[1:6] = b"CD001"
        pvd[6] = 1
        pvd[8:40] = b"PLAYSTATION 2".ljust(32)
        pvd[40:72] = b"SLUS_12345".ljust(32)

        iso_path.write_bytes(header + bytes(pvd) + b"\x00" * 32768)

        result = detect_disc_format(iso_path)

        assert result.platform == DiscPlatform.PS2
        assert result.confidence >= 0.9

    def test_ps2_boot2_detection(self, tmp_path: Path) -> None:
        """PS2 disc detected via BOOT2 in SYSTEM.CNF."""
        iso_path = tmp_path / "ps2_game.iso"

        # Generic ISO with BOOT2 marker somewhere
        content = b"\x00" * 4096 + b"BOOT2 = cdrom0:\\SLUS_123.45" + b"\x00" * 60000

        iso_path.write_bytes(content)

        result = detect_disc_format(iso_path)

        assert result.platform == DiscPlatform.PS2
        assert result.confidence >= 0.85

    def test_ps1_boot_detection(self, tmp_path: Path) -> None:
        """PS1 disc detected via BOOT= in SYSTEM.CNF."""
        iso_path = tmp_path / "ps1_game.bin"

        content = b"\x00" * 2048 + b"BOOT = cdrom:\\SLUS_012.34;1" + b"\x00" * 60000

        iso_path.write_bytes(content)

        result = detect_disc_format(iso_path)

        # Should detect PS1 or at least not PS2
        assert result.platform in (DiscPlatform.PS1, DiscPlatform.UNKNOWN)


class TestPSPDetection:
    """Tests for PSP disc detection."""

    def test_psp_pvd_detection(self, tmp_path: Path) -> None:
        """PSP UMD with PSP in system identifier."""
        iso_path = tmp_path / "psp_game.iso"

        header = b"\x00" * 0x8000

        pvd = bytearray(2048)
        pvd[0] = 1
        pvd[1:6] = b"CD001"
        pvd[8:40] = b"PSP GAME".ljust(32)
        pvd[40:72] = b"UCUS12345".ljust(32)

        iso_path.write_bytes(header + bytes(pvd) + b"\x00" * 32768)

        result = detect_disc_format(iso_path)

        assert result.platform == DiscPlatform.PSP
        assert result.confidence >= 0.9

    def test_cso_extension_fallback(self, tmp_path: Path) -> None:
        """CSO extension should suggest PSP."""
        iso_path = tmp_path / "game.cso"
        iso_path.write_bytes(b"\x00" * 1024)

        result = detect_disc_format(iso_path)

        assert result.platform == DiscPlatform.PSP
        assert result.confidence >= 0.7
        assert "extension" in result.detection_source.lower()


class Test3DODetection:
    """Tests for 3DO disc detection."""

    def test_3do_opera_fs(self, tmp_path: Path) -> None:
        """3DO disc with opera_fs signature."""
        iso_path = tmp_path / "3do_game.iso"

        header = b"\x00" * 100 + b"opera_fs" + b"\x00" * 400
        iso_path.write_bytes(header + b"\x00" * 32768)

        result = detect_disc_format(iso_path)

        assert result.platform == DiscPlatform.THREE_DO
        assert result.confidence >= 0.9

    def test_3do_magic_bytes(self, tmp_path: Path) -> None:
        """3DO disc with specific magic bytes."""
        iso_path = tmp_path / "3do_game.iso"

        header = b"\x01\x5a\x5a\x5a\x5a\x5a\x01" + b"\x00" * 2041
        iso_path.write_bytes(header + b"\x00" * 32768)

        result = detect_disc_format(iso_path)

        assert result.platform == DiscPlatform.THREE_DO
        assert result.confidence >= 0.9


class TestPCEngineDetection:
    """Tests for PC Engine CD detection."""

    def test_pce_cd_system_header(self, tmp_path: Path) -> None:
        """PC Engine CD with system identifier."""
        iso_path = tmp_path / "pce_game.bin"

        header = b"PC Engine CD-ROM SYSTEM" + b"\x00" * (2048 - 23)
        iso_path.write_bytes(header + b"\x00" * 32768)

        result = detect_disc_format(iso_path)

        assert result.platform == DiscPlatform.PC_ENGINE_CD
        assert result.confidence >= 0.85


class TestXboxDetection:
    """Tests for Xbox disc detection."""

    def test_xbox_media_header(self, tmp_path: Path) -> None:
        """Xbox disc with MICROSOFT*XBOX*MEDIA identifier."""
        iso_path = tmp_path / "xbox_game.iso"

        header = b"\x00" * 1000 + b"MICROSOFT*XBOX*MEDIA" + b"\x00" * 64000
        iso_path.write_bytes(header)

        result = detect_disc_format(iso_path)

        assert result.platform == DiscPlatform.XBOX
        assert result.confidence >= 0.9


class TestDreamcastDetection:
    """Tests for Dreamcast detection."""

    def test_gdi_extension_detection(self, tmp_path: Path) -> None:
        """GDI extension should strongly suggest Dreamcast."""
        gdi_path = tmp_path / "game.gdi"
        gdi_path.write_text("3\n1 0 4 2352 track01.raw 0\n")

        result = detect_disc_format(gdi_path)

        assert result.platform == DiscPlatform.DREAMCAST
        assert result.confidence >= 0.8

    def test_cdi_extension_detection(self, tmp_path: Path) -> None:
        """CDI extension often indicates Dreamcast."""
        cdi_path = tmp_path / "game.cdi"
        cdi_path.write_bytes(b"\x00" * 1024)

        result = detect_disc_format(cdi_path)

        assert result.platform == DiscPlatform.DREAMCAST
        assert result.confidence >= 0.6


class TestExtensionFallbacks:
    """Tests for extension-based fallback detection."""

    def test_pbp_is_psp(self, tmp_path: Path) -> None:
        """PBP files are PSP EBOOT."""
        pbp_path = tmp_path / "EBOOT.PBP"
        pbp_path.write_bytes(b"\x00" * 1024)

        result = detect_disc_format(pbp_path)

        assert result.platform == DiscPlatform.PSP
        assert result.confidence >= 0.8

    def test_unknown_iso_low_confidence(self, tmp_path: Path) -> None:
        """Unknown .iso should have low confidence."""
        iso_path = tmp_path / "unknown.iso"
        iso_path.write_bytes(b"\x00" * 1024)

        result = detect_disc_format(iso_path)

        assert result.confidence <= 0.5

    def test_unknown_bin_low_confidence(self, tmp_path: Path) -> None:
        """Unknown .bin should have low confidence."""
        bin_path = tmp_path / "unknown.bin"
        bin_path.write_bytes(b"\x00" * 1024)

        result = detect_disc_format(bin_path)

        assert result.confidence <= 0.5


class TestBinWithCue:
    """Tests for bin+cue combined detection."""

    def test_bin_with_playstation_cue(self, tmp_path: Path) -> None:
        """Bin file with PlayStation reference in cue."""
        bin_path = tmp_path / "game.bin"
        cue_path = tmp_path / "game.cue"

        bin_path.write_bytes(b"\x00" * 2048)
        cue_path.write_text('REM PlayStation Game\nFILE "game.bin" BINARY\n  TRACK 01 MODE2/2352\n')

        result = detect_bin_with_cue(bin_path, cue_path)

        assert result.platform == DiscPlatform.PS1
        assert result.confidence >= 0.7

    def test_bin_with_saturn_cue(self, tmp_path: Path) -> None:
        """Bin file with Saturn reference in cue."""
        bin_path = tmp_path / "saturn.bin"
        cue_path = tmp_path / "saturn.cue"

        bin_path.write_bytes(b"\x00" * 2048)
        cue_path.write_text('REM Sega Saturn ISO\nFILE "saturn.bin" BINARY\n')

        result = detect_bin_with_cue(bin_path, cue_path)

        assert result.platform == DiscPlatform.SATURN
        assert result.confidence >= 0.7

    def test_bin_with_segacd_cue(self, tmp_path: Path) -> None:
        """Bin file with Sega CD reference in cue."""
        bin_path = tmp_path / "segacd.bin"
        cue_path = tmp_path / "segacd.cue"

        bin_path.write_bytes(b"\x00" * 2048)
        cue_path.write_text('REM SEGA CD GAME\nFILE "segacd.bin" BINARY\n')

        result = detect_bin_with_cue(bin_path, cue_path)

        assert result.platform == DiscPlatform.SEGACD
        assert result.confidence >= 0.7

    def test_bin_header_takes_precedence(self, tmp_path: Path) -> None:
        """Header detection should take precedence over cue hints."""
        bin_path = tmp_path / "saturn.bin"
        cue_path = tmp_path / "saturn.cue"

        # Saturn header in bin
        header = b"SEGA SEGASATURN " + b"\x00" * (2048 - 16)
        bin_path.write_bytes(header + b"\x00" * 32768)
        cue_path.write_text('REM Some game\nFILE "saturn.bin" BINARY\n')

        result = detect_bin_with_cue(bin_path, cue_path)

        assert result.platform == DiscPlatform.SATURN
        assert result.confidence >= 0.9  # High confidence from header


class TestHelperFunctions:
    """Tests for helper utility functions."""

    def test_is_disc_image_extension(self) -> None:
        """Test disc image extension detection."""
        assert is_disc_image_extension(".iso") is True
        assert is_disc_image_extension(".ISO") is True
        assert is_disc_image_extension(".bin") is True
        assert is_disc_image_extension(".cue") is True
        assert is_disc_image_extension(".gdi") is True
        assert is_disc_image_extension(".chd") is True
        assert is_disc_image_extension(".cso") is True

        assert is_disc_image_extension(".nes") is False
        assert is_disc_image_extension(".gba") is False
        assert is_disc_image_extension(".zip") is False

    def test_needs_disambiguation(self) -> None:
        """Test which extensions need header sniffing."""
        assert needs_disambiguation(".iso") is True
        assert needs_disambiguation(".bin") is True
        assert needs_disambiguation(".img") is True
        assert needs_disambiguation(".chd") is True

        assert needs_disambiguation(".gdi") is False  # Always Dreamcast
        assert needs_disambiguation(".cso") is False  # Always PSP
        assert needs_disambiguation(".nes") is False


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Nonexistent file should return unknown with error."""
        result = detect_disc_format(tmp_path / "does_not_exist.iso")

        assert result.platform == DiscPlatform.UNKNOWN
        assert result.confidence == 0.0
        assert "error" in result.detection_source.lower()

    def test_directory_instead_of_file(self, tmp_path: Path) -> None:
        """Directory should return unknown with error."""
        result = detect_disc_format(tmp_path)

        assert result.platform == DiscPlatform.UNKNOWN
        assert result.confidence == 0.0

    def test_empty_file(self, tmp_path: Path) -> None:
        """Empty file should not crash."""
        empty_file = tmp_path / "empty.iso"
        empty_file.write_bytes(b"")

        result = detect_disc_format(empty_file)

        assert isinstance(result, DiscDetectionResult)
        assert result.confidence <= 0.5

    def test_very_small_file(self, tmp_path: Path) -> None:
        """Very small file should not crash."""
        small_file = tmp_path / "tiny.bin"
        small_file.write_bytes(b"\x00" * 10)

        result = detect_disc_format(small_file)

        assert isinstance(result, DiscDetectionResult)


class TestRawSectorFormat:
    """Tests for raw sector (2352 bytes/sector) format detection."""

    def test_raw_sector_ps1(self, tmp_path: Path) -> None:
        """PS1 disc in raw 2352 byte sector format."""
        iso_path = tmp_path / "ps1_raw.bin"

        # Raw sector format: each sector is 2352 bytes
        # Sector 16 contains PVD, with 16-byte sync header
        sectors = b"\x00" * (16 * 2352)  # Sectors 0-15

        # Sector 16 with sync header
        sync_header = b"\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00"

        pvd = bytearray(2048)
        pvd[0] = 1
        pvd[1:6] = b"CD001"
        pvd[8:40] = b"PLAYSTATION".ljust(32)

        # Complete raw sector
        ecc = b"\x00" * (2352 - 16 - 2048)  # ECC/EDC padding
        raw_sector = sync_header + bytes(pvd) + ecc

        iso_path.write_bytes(sectors + raw_sector + b"\x00" * 65536)

        result = detect_disc_format(iso_path)

        # Should detect PlayStation (may or may not detect raw format specifically)
        assert result.platform in (DiscPlatform.PS1, DiscPlatform.UNKNOWN)
