"""Tests for multi-file set validators (cue/bin, gdi, m3u)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.scanning.set_validators import (
    SetValidationResult,
    detect_set_membership,
    group_sets_in_directory,
    is_set_member_file,
    parse_cue_file,
    parse_gdi_file,
    parse_m3u_file,
    validate_cue_bin_set,
    validate_gdi_set,
    validate_m3u_set,
)


class TestCueBinValidation:
    """Tests for cue/bin disc image set validation."""

    def test_parse_cue_file_simple(self, tmp_path: Path) -> None:
        """Parse a simple cue file with one bin."""
        cue = tmp_path / "game.cue"
        bin_file = tmp_path / "game.bin"

        cue.write_text('FILE "game.bin" BINARY\n  TRACK 01 MODE1/2352\n    INDEX 01 00:00:00\n')
        bin_file.write_bytes(b"\x00" * 1024)

        found, missing = parse_cue_file(cue)

        assert len(found) == 1
        assert str(bin_file.resolve()) in found
        assert len(missing) == 0

    def test_parse_cue_file_multiple_tracks(self, tmp_path: Path) -> None:
        """Parse a cue file with multiple track files."""
        cue = tmp_path / "game.cue"
        track1 = tmp_path / "track01.bin"
        track2 = tmp_path / "track02.bin"
        track3 = tmp_path / "track03.bin"  # Missing

        cue.write_text(
            'FILE "track01.bin" BINARY\n'
            '  TRACK 01 MODE1/2352\n'
            '    INDEX 01 00:00:00\n'
            'FILE "track02.bin" BINARY\n'
            '  TRACK 02 AUDIO\n'
            '    INDEX 01 00:00:00\n'
            'FILE "track03.bin" BINARY\n'
            '  TRACK 03 AUDIO\n'
            '    INDEX 01 00:00:00\n'
        )
        track1.write_bytes(b"\x00" * 1024)
        track2.write_bytes(b"\x00" * 1024)

        found, missing = parse_cue_file(cue)

        assert len(found) == 2
        assert len(missing) == 1
        assert str(track3.resolve()) in missing

    def test_parse_cue_file_unquoted_filename(self, tmp_path: Path) -> None:
        """Parse a cue file with unquoted filename."""
        cue = tmp_path / "game.cue"
        bin_file = tmp_path / "game.bin"

        cue.write_text("FILE game.bin BINARY\n  TRACK 01 MODE1/2352\n")
        bin_file.write_bytes(b"\x00" * 1024)

        found, missing = parse_cue_file(cue)

        assert len(found) == 1
        assert str(bin_file.resolve()) in found

    def test_parse_cue_file_single_quotes(self, tmp_path: Path) -> None:
        """Parse a cue file with single-quoted filename."""
        cue = tmp_path / "game.cue"
        bin_file = tmp_path / "game.bin"

        cue.write_text("FILE 'game.bin' BINARY\n  TRACK 01 MODE1/2352\n")
        bin_file.write_bytes(b"\x00" * 1024)

        found, missing = parse_cue_file(cue)

        assert len(found) == 1

    def test_validate_cue_bin_set_complete(self, tmp_path: Path) -> None:
        """Validate a complete cue/bin set."""
        cue = tmp_path / "game.cue"
        bin_file = tmp_path / "game.bin"

        cue.write_text('FILE "game.bin" BINARY\n  TRACK 01 MODE1/2352\n')
        bin_file.write_bytes(b"\x00" * 1024)

        result = validate_cue_bin_set(cue)

        assert result.is_set is True
        assert result.set_type == "cue-bin"
        assert result.primary_file == str(cue)
        assert len(result.member_files) == 2
        assert str(cue) in result.member_files
        assert str(bin_file.resolve()) in result.member_files
        assert len(result.missing_files) == 0
        assert len(result.warnings) == 0

    def test_validate_cue_bin_set_missing_bin(self, tmp_path: Path) -> None:
        """Validate a cue file with missing bin."""
        cue = tmp_path / "game.cue"

        cue.write_text('FILE "game.bin" BINARY\n  TRACK 01 MODE1/2352\n')

        result = validate_cue_bin_set(cue)

        assert result.is_set is True
        assert result.set_type == "cue-bin"
        assert len(result.missing_files) == 1
        assert len(result.warnings) == 1
        assert "not found" in result.warnings[0].lower()

    def test_validate_cue_bin_set_empty_cue(self, tmp_path: Path) -> None:
        """Validate an empty cue file."""
        cue = tmp_path / "empty.cue"
        cue.write_text("")

        result = validate_cue_bin_set(cue)

        assert result.is_set is True
        assert result.set_type == "cue-bin"
        assert len(result.warnings) == 1
        assert "no file entries" in result.warnings[0].lower()


class TestGdiValidation:
    """Tests for Dreamcast GDI disc image set validation."""

    def test_parse_gdi_file_simple(self, tmp_path: Path) -> None:
        """Parse a simple GDI file."""
        gdi = tmp_path / "game.gdi"
        track1 = tmp_path / "track01.bin"
        track2 = tmp_path / "track02.raw"
        track3 = tmp_path / "track03.bin"

        gdi.write_text("3\n1 0 4 2352 track01.bin 0\n2 450 0 2352 track02.raw 0\n3 45000 4 2352 track03.bin 0\n")
        track1.write_bytes(b"\x00" * 1024)
        track2.write_bytes(b"\x00" * 1024)
        track3.write_bytes(b"\x00" * 1024)

        found, missing, track_count = parse_gdi_file(gdi)

        assert track_count == 3
        assert len(found) == 3
        assert len(missing) == 0

    def test_parse_gdi_file_missing_track(self, tmp_path: Path) -> None:
        """Parse a GDI file with a missing track."""
        gdi = tmp_path / "game.gdi"
        track1 = tmp_path / "track01.bin"

        gdi.write_text("2\n1 0 4 2352 track01.bin 0\n2 450 0 2352 track02.raw 0\n")
        track1.write_bytes(b"\x00" * 1024)

        found, missing, track_count = parse_gdi_file(gdi)

        assert track_count == 2
        assert len(found) == 1
        assert len(missing) == 1

    def test_validate_gdi_set_complete(self, tmp_path: Path) -> None:
        """Validate a complete Dreamcast GDI set."""
        gdi = tmp_path / "game.gdi"
        track1 = tmp_path / "track01.bin"
        track2 = tmp_path / "track02.raw"
        track3 = tmp_path / "track03.bin"

        gdi.write_text("3\n1 0 4 2352 track01.bin 0\n2 450 0 2352 track02.raw 0\n3 45000 4 2352 track03.bin 0\n")
        track1.write_bytes(b"\x00" * 1024)
        track2.write_bytes(b"\x00" * 1024)
        track3.write_bytes(b"\x00" * 1024)

        result = validate_gdi_set(gdi)

        assert result.is_set is True
        assert result.set_type == "gdi"
        assert result.platform_hint == "Dreamcast"
        assert len(result.member_files) == 4  # gdi + 3 tracks
        assert len(result.missing_files) == 0
        assert len(result.warnings) == 0

    def test_validate_gdi_set_missing_tracks(self, tmp_path: Path) -> None:
        """Validate a GDI set with missing tracks."""
        gdi = tmp_path / "game.gdi"
        track1 = tmp_path / "track01.bin"

        gdi.write_text("3\n1 0 4 2352 track01.bin 0\n2 450 0 2352 track02.raw 0\n3 45000 4 2352 track03.bin 0\n")
        track1.write_bytes(b"\x00" * 1024)

        result = validate_gdi_set(gdi)

        assert result.is_set is True
        assert len(result.missing_files) == 2
        assert len(result.warnings) >= 2  # Missing files + track count mismatch


class TestM3uValidation:
    """Tests for m3u multi-disc playlist validation."""

    def test_parse_m3u_file_simple(self, tmp_path: Path) -> None:
        """Parse a simple m3u playlist."""
        m3u = tmp_path / "game.m3u"
        disc1 = tmp_path / "disc1.cue"
        disc2 = tmp_path / "disc2.cue"

        m3u.write_text("disc1.cue\ndisc2.cue\n")
        disc1.write_text('FILE "disc1.bin" BINARY\n')
        disc2.write_text('FILE "disc2.bin" BINARY\n')

        found, missing = parse_m3u_file(m3u)

        assert len(found) == 2
        assert len(missing) == 0

    def test_parse_m3u_file_with_comments(self, tmp_path: Path) -> None:
        """Parse an m3u file with comments and extended directives."""
        m3u = tmp_path / "game.m3u"
        disc1 = tmp_path / "disc1.cue"

        m3u.write_text("#EXTM3U\n#This is a comment\ndisc1.cue\n")
        disc1.write_text('FILE "disc1.bin" BINARY\n')

        found, missing = parse_m3u_file(m3u)

        assert len(found) == 1
        assert len(missing) == 0

    def test_parse_m3u_file_missing_disc(self, tmp_path: Path) -> None:
        """Parse an m3u file with a missing disc."""
        m3u = tmp_path / "game.m3u"
        disc1 = tmp_path / "disc1.cue"

        m3u.write_text("disc1.cue\ndisc2.cue\n")
        disc1.write_text('FILE "disc1.bin" BINARY\n')

        found, missing = parse_m3u_file(m3u)

        assert len(found) == 1
        assert len(missing) == 1

    def test_validate_m3u_set_complete(self, tmp_path: Path) -> None:
        """Validate a complete m3u multi-disc set."""
        m3u = tmp_path / "game.m3u"
        disc1 = tmp_path / "disc1.cue"
        disc2 = tmp_path / "disc2.cue"

        m3u.write_text("disc1.cue\ndisc2.cue\n")
        disc1.write_text('FILE "disc1.bin" BINARY\n')
        disc2.write_text('FILE "disc2.bin" BINARY\n')

        result = validate_m3u_set(m3u)

        assert result.is_set is True
        assert result.set_type == "m3u"
        assert len(result.member_files) == 3  # m3u + 2 discs
        assert len(result.missing_files) == 0
        assert len(result.warnings) == 0


class TestSetDetection:
    """Tests for automatic set detection."""

    def test_detect_set_membership_cue_primary(self, tmp_path: Path) -> None:
        """Detect cue file as set primary."""
        cue = tmp_path / "game.cue"
        bin_file = tmp_path / "game.bin"

        cue.write_text('FILE "game.bin" BINARY\n')
        bin_file.write_bytes(b"\x00" * 1024)

        result = detect_set_membership(cue)

        assert result is not None
        assert result.is_set is True
        assert result.set_type == "cue-bin"

    def test_detect_set_membership_bin_member(self, tmp_path: Path) -> None:
        """Detect bin file as member of cue set."""
        cue = tmp_path / "game.cue"
        bin_file = tmp_path / "game.bin"

        cue.write_text('FILE "game.bin" BINARY\n')
        bin_file.write_bytes(b"\x00" * 1024)

        result = detect_set_membership(bin_file)

        assert result is not None
        assert result.is_set is True
        assert result.primary_file == str(cue)

    def test_detect_set_membership_standalone_bin(self, tmp_path: Path) -> None:
        """A standalone bin without cue should return None."""
        bin_file = tmp_path / "game.bin"
        bin_file.write_bytes(b"\x00" * 1024)

        result = detect_set_membership(bin_file)

        # No cue file, so no set detected
        assert result is None

    def test_detect_set_membership_gdi(self, tmp_path: Path) -> None:
        """Detect gdi file as set primary."""
        gdi = tmp_path / "game.gdi"
        track1 = tmp_path / "track01.bin"

        gdi.write_text("1\n1 0 4 2352 track01.bin 0\n")
        track1.write_bytes(b"\x00" * 1024)

        result = detect_set_membership(gdi)

        assert result is not None
        assert result.set_type == "gdi"
        assert result.platform_hint == "Dreamcast"


class TestSetGrouping:
    """Tests for grouping sets in a directory."""

    def test_group_sets_in_directory(self, tmp_path: Path) -> None:
        """Group multiple sets in a directory."""
        # Create a cue/bin set
        cue1 = tmp_path / "game1.cue"
        bin1 = tmp_path / "game1.bin"
        cue1.write_text('FILE "game1.bin" BINARY\n')
        bin1.write_bytes(b"\x00" * 1024)

        # Create a gdi set
        gdi = tmp_path / "game2.gdi"
        track = tmp_path / "track01.bin"
        gdi.write_text("1\n1 0 4 2352 track01.bin 0\n")
        track.write_bytes(b"\x00" * 1024)

        # Create an m3u set referencing its own dedicated cue file
        m3u = tmp_path / "multi.m3u"
        disc1 = tmp_path / "disc1.cue"
        disc1_bin = tmp_path / "disc1.bin"
        m3u.write_text("disc1.cue\n")
        disc1.write_text('FILE "disc1.bin" BINARY\n')
        disc1_bin.write_bytes(b"\x00" * 1024)

        sets = group_sets_in_directory(tmp_path)

        # 4 sets: game1.cue, game2.gdi, multi.m3u, and disc1.cue (as standalone cue)
        # Note: disc1.cue is picked up both as m3u member AND as its own cue set
        assert len(sets) == 4
        assert str(cue1) in sets
        assert str(gdi) in sets
        assert str(m3u) in sets
        assert str(disc1) in sets  # Also detected as standalone cue set

    def test_is_set_member_file(self, tmp_path: Path) -> None:
        """Check if a file is a member of a known set."""
        cue = tmp_path / "game.cue"
        bin_file = tmp_path / "game.bin"
        standalone = tmp_path / "other.rom"

        cue.write_text('FILE "game.bin" BINARY\n')
        bin_file.write_bytes(b"\x00" * 1024)
        standalone.write_bytes(b"\x00" * 1024)

        sets = group_sets_in_directory(tmp_path)

        assert is_set_member_file(bin_file, sets) is True
        assert is_set_member_file(cue, sets) is False  # Primary, not member
        assert is_set_member_file(standalone, sets) is False


class TestEdgeCases:
    """Edge case tests."""

    def test_cue_with_subdirectory_reference(self, tmp_path: Path) -> None:
        """Cue file referencing file in subdirectory."""
        subdir = tmp_path / "tracks"
        subdir.mkdir()

        cue = tmp_path / "game.cue"
        bin_file = subdir / "track01.bin"

        cue.write_text('FILE "tracks/track01.bin" BINARY\n')
        bin_file.write_bytes(b"\x00" * 1024)

        found, missing = parse_cue_file(cue)

        assert len(found) == 1
        assert str(bin_file.resolve()) in found

    def test_nonexistent_cue_file(self, tmp_path: Path) -> None:
        """Validating a nonexistent cue file."""
        cue = tmp_path / "nonexistent.cue"

        result = validate_cue_bin_set(cue)

        assert result.is_set is False
        assert result.set_type == "single"

    def test_wrong_extension_for_cue(self, tmp_path: Path) -> None:
        """Passing wrong extension to cue validator."""
        rom = tmp_path / "game.bin"
        rom.write_bytes(b"\x00" * 1024)

        result = validate_cue_bin_set(rom)

        assert result.is_set is False
        assert result.set_type == "single"

    def test_unicode_filenames(self, tmp_path: Path) -> None:
        """Cue file with unicode filename references."""
        cue = tmp_path / "ゲーム.cue"
        bin_file = tmp_path / "ゲーム.bin"

        cue.write_text('FILE "ゲーム.bin" BINARY\n', encoding="utf-8")
        bin_file.write_bytes(b"\x00" * 1024)

        found, missing = parse_cue_file(cue)

        assert len(found) == 1
        assert str(bin_file.resolve()) in found

    def test_latin1_encoded_cue(self, tmp_path: Path) -> None:
        """Cue file with latin-1 encoding."""
        cue = tmp_path / "game.cue"
        bin_file = tmp_path / "game.bin"

        # Write with latin-1 encoding
        cue.write_bytes(b'FILE "game.bin" BINARY\n')
        bin_file.write_bytes(b"\x00" * 1024)

        found, missing = parse_cue_file(cue)

        assert len(found) == 1
