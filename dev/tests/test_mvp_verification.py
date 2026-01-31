"""Tests for ROM Verification Module (F71-F74).

Tests:
- F71: Bad-Dump Scanner
- F72: Intro/Trainer Detection
- F73: Overdump Detection
- F74: Integrity Reports
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.verification.rom_verifier import (
    RomVerifier,
    VerificationResult,
    RomFlag,
    FlagType,
    detect_bad_dumps,
    detect_modified_roms,
)
from src.verification.integrity_report import (
    IntegrityReportGenerator,
    IntegrityReport,
    PlatformSummary,
)


class TestRomVerifier:
    """Tests for RomVerifier class."""

    def test_init_without_index(self):
        """Test initialization without DAT index."""
        verifier = RomVerifier()
        assert verifier.index is None

    def test_init_with_index(self):
        """Test initialization with DAT index."""
        mock_index = MagicMock()
        verifier = RomVerifier(index=mock_index)
        assert verifier.index is mock_index


class TestFlagDetection:
    """Tests for flag detection patterns (F71, F72)."""

    @pytest.fixture
    def verifier(self):
        return RomVerifier()

    @pytest.mark.parametrize(
        "filename,expected_flag",
        [
            ("Super Mario Bros [b]", FlagType.BAD_DUMP),
            ("Zelda (b)", FlagType.BAD_DUMP),
            ("Metroid [!]", FlagType.VERIFIED),
            ("Castlevania [o1]", FlagType.OVERDUMP),
            ("Mega Man [h1C]", FlagType.HACK),
        ],
    )
    def test_bad_dump_flags_f71(self, verifier, filename, expected_flag):
        """F71: Test bad dump flag detection."""
        flags = verifier._detect_flags_in_name(filename, "filename")
        flag_types = {f.flag_type for f in flags}
        assert expected_flag in flag_types

    @pytest.mark.parametrize(
        "filename,expected_flag",
        [
            ("Game [t1]", FlagType.TRAINER),
            ("Game +4Trainer", FlagType.TRAINER),
            ("Game [f]", FlagType.FIXED),
            ("Game [a1]", FlagType.ALTERNATE),
            ("Game [p]", FlagType.PIRATE),
            ("Game [T+Eng]", FlagType.TRANSLATION),
            ("Game [I]", FlagType.INTRO),
        ],
    )
    def test_modification_flags_f72(self, verifier, filename, expected_flag):
        """F72: Test modification flag detection."""
        flags = verifier._detect_flags_in_name(filename, "filename")
        flag_types = {f.flag_type for f in flags}
        assert expected_flag in flag_types

    @pytest.mark.parametrize(
        "filename,expected_flag",
        [
            ("Game (Beta)", FlagType.BETA),
            ("Game (Proto)", FlagType.PROTO),
            ("Game (Demo)", FlagType.DEMO),
            ("Game (Sample)", FlagType.SAMPLE),
        ],
    )
    def test_version_flags(self, verifier, filename, expected_flag):
        """Test version/status flag detection."""
        flags = verifier._detect_flags_in_name(filename, "filename")
        flag_types = {f.flag_type for f in flags}
        assert expected_flag in flag_types

    def test_multiple_flags(self, verifier):
        """Test detection of multiple flags in one name."""
        filename = "Game [b][t1] (Beta)"
        flags = verifier._detect_flags_in_name(filename, "filename")
        flag_types = {f.flag_type for f in flags}

        assert FlagType.BAD_DUMP in flag_types
        assert FlagType.TRAINER in flag_types
        assert FlagType.BETA in flag_types

    def test_no_flags(self, verifier):
        """Test clean name with no flags."""
        filename = "Super Mario Bros (USA)"
        flags = verifier._detect_flags_in_name(filename, "filename")
        # Should not detect bad dump or modification flags
        flag_types = {f.flag_type for f in flags}
        assert FlagType.BAD_DUMP not in flag_types
        assert FlagType.TRAINER not in flag_types


class TestSizeVerification:
    """Tests for size verification (F73)."""

    @pytest.fixture
    def verifier(self):
        return RomVerifier()

    def test_size_match(self, verifier):
        """Test exact size match."""
        flags = verifier._check_size(1024, 1024)
        assert len(flags) == 0

    def test_undersized(self, verifier):
        """Test undersized detection."""
        flags = verifier._check_size(500, 1000)
        flag_types = {f.flag_type for f in flags}
        assert FlagType.SIZE_MISMATCH in flag_types
        assert FlagType.UNDERSIZED in flag_types

    def test_oversized(self, verifier):
        """Test oversized detection (potential overdump)."""
        flags = verifier._check_size(1500, 1000)
        flag_types = {f.flag_type for f in flags}
        assert FlagType.SIZE_MISMATCH in flag_types
        assert FlagType.OVERSIZED in flag_types


class TestVerifyFile:
    """Tests for full file verification."""

    def test_verify_nonexistent_file(self):
        """Test verifying a file that doesn't exist."""
        verifier = RomVerifier()
        result = verifier.verify("/nonexistent/path/game.rom")
        assert result.file_path == "/nonexistent/path/game.rom"
        assert result.file_size == 0
        assert not result.dat_matched

    def test_verify_real_file(self, tmp_path):
        """Test verifying a real file."""
        # Create a test file
        test_file = tmp_path / "Test Game [b].rom"
        test_file.write_bytes(b"test data for rom verification")

        verifier = RomVerifier()
        result = verifier.verify(str(test_file))

        assert result.file_path == str(test_file)
        assert result.file_size > 0
        assert result.sha1 is not None
        assert result.is_bad_dump  # Has [b] in name

    def test_verify_verified_good_file(self, tmp_path):
        """Test verifying a [!] file."""
        test_file = tmp_path / "Test Game [!].rom"
        test_file.write_bytes(b"verified rom data")

        verifier = RomVerifier()
        result = verifier.verify(str(test_file))

        assert result.is_verified_good

    def test_verify_modified_file(self, tmp_path):
        """Test verifying a modified ROM."""
        test_file = tmp_path / "Test Game [t1][f].rom"
        test_file.write_bytes(b"modified rom data")

        verifier = RomVerifier()
        result = verifier.verify(str(test_file))

        assert result.is_modified

    def test_confidence_score(self, tmp_path):
        """Test confidence score calculation."""
        # Good ROM
        good_file = tmp_path / "Good Game [!].rom"
        good_file.write_bytes(b"good rom")

        # Bad ROM
        bad_file = tmp_path / "Bad Game [b].rom"
        bad_file.write_bytes(b"bad rom")

        verifier = RomVerifier()
        good_result = verifier.verify(str(good_file))
        bad_result = verifier.verify(str(bad_file))

        # Good should have higher confidence
        assert good_result.confidence_score > bad_result.confidence_score


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_flag_types_property(self):
        """Test flag_types property."""
        result = VerificationResult(file_path="/test")
        result.flags.append(RomFlag(FlagType.BAD_DUMP, "[b]", 1.0, "filename"))
        result.flags.append(RomFlag(FlagType.TRAINER, "[t]", 1.0, "filename"))

        assert FlagType.BAD_DUMP in result.flag_types
        assert FlagType.TRAINER in result.flag_types
        assert FlagType.VERIFIED not in result.flag_types

    def test_is_clean_property(self):
        """Test is_clean property."""
        # Clean ROM
        clean = VerificationResult(file_path="/test", dat_matched=True)
        assert clean.is_clean

        # Bad dump
        bad = VerificationResult(file_path="/test", dat_matched=True, is_bad_dump=True)
        assert not bad.is_clean


class TestIntegrityReport:
    """Tests for IntegrityReport (F74)."""

    def test_report_creation(self):
        """Test creating an integrity report."""
        report = IntegrityReport(
            scan_path="/test/roms",
            total_files_scanned=100,
            total_verified_good=50,
            total_bad_dumps=10,
        )
        assert report.total_files_scanned == 100
        assert report.total_verified_good == 50

    def test_overall_health_score(self):
        """Test health score calculation."""
        # Good collection
        good_report = IntegrityReport(
            total_files_scanned=100,
            total_clean=90,
            total_verified_good=80,
            total_bad_dumps=2,
        )
        # Bad collection
        bad_report = IntegrityReport(
            total_files_scanned=100,
            total_clean=10,
            total_bad_dumps=40,
        )

        assert good_report.overall_health_score > bad_report.overall_health_score

    def test_to_json(self):
        """Test JSON serialization."""
        report = IntegrityReport(
            scan_path="/test",
            total_files_scanned=10,
        )
        json_str = report.to_json()
        assert '"scan_path": "/test"' in json_str
        assert '"total_files_scanned": 10' in json_str

    def test_save_and_load(self, tmp_path):
        """Test saving report to file."""
        report = IntegrityReport(
            scan_path="/test",
            total_files_scanned=5,
        )
        report_path = tmp_path / "report.json"
        report.save(str(report_path))

        assert report_path.exists()
        content = report_path.read_text()
        assert "total_files_scanned" in content


class TestIntegrityReportGenerator:
    """Tests for IntegrityReportGenerator."""

    def test_generate_empty(self):
        """Test generating report with no files."""
        verifier = RomVerifier()
        generator = IntegrityReportGenerator(verifier)
        report = generator.generate([])

        assert report.total_files_scanned == 0

    def test_generate_with_files(self, tmp_path):
        """Test generating report with actual files."""
        # Create test files
        (tmp_path / "good [!].rom").write_bytes(b"good")
        (tmp_path / "bad [b].rom").write_bytes(b"bad")
        (tmp_path / "modified [t].rom").write_bytes(b"mod")

        paths = [
            str(tmp_path / "good [!].rom"),
            str(tmp_path / "bad [b].rom"),
            str(tmp_path / "modified [t].rom"),
        ]

        verifier = RomVerifier()
        generator = IntegrityReportGenerator(verifier)
        report = generator.generate(paths)

        assert report.total_files_scanned == 3
        assert report.total_verified_good == 1
        assert report.total_bad_dumps == 1
        assert report.total_modified == 1

    def test_generate_with_progress_callback(self, tmp_path):
        """Test progress callback."""
        (tmp_path / "test.rom").write_bytes(b"test")
        paths = [str(tmp_path / "test.rom")]

        progress_calls = []

        def progress_cb(current, total, path):
            progress_calls.append((current, total, path))

        verifier = RomVerifier()
        generator = IntegrityReportGenerator(verifier)
        generator.generate(paths, progress_callback=progress_cb)

        assert len(progress_calls) == 1
        assert progress_calls[0][0] == 1  # current
        assert progress_calls[0][1] == 1  # total

    def test_generate_with_cancellation(self, tmp_path):
        """Test cancellation support."""
        # Create multiple files
        for i in range(10):
            (tmp_path / f"game{i}.rom").write_bytes(b"data")

        paths = [str(p) for p in tmp_path.glob("*.rom")]

        # Create cancel event that triggers after 2 files
        class MockCancelEvent:
            def __init__(self):
                self.call_count = 0

            def is_set(self):
                self.call_count += 1
                return self.call_count > 2

        cancel = MockCancelEvent()
        verifier = RomVerifier()
        generator = IntegrityReportGenerator(verifier)
        report = generator.generate(paths, cancel_event=cancel)

        # Should have stopped early
        assert report.total_files_scanned < 10


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_detect_bad_dumps(self, tmp_path):
        """Test detect_bad_dumps function."""
        (tmp_path / "bad [b].rom").write_bytes(b"bad")
        (tmp_path / "good.rom").write_bytes(b"good")

        paths = [
            str(tmp_path / "bad [b].rom"),
            str(tmp_path / "good.rom"),
        ]

        results = detect_bad_dumps(paths)
        assert len(results) == 1
        assert str(tmp_path / "bad [b].rom") in results

    def test_detect_modified_roms(self, tmp_path):
        """Test detect_modified_roms function."""
        (tmp_path / "trainer [t].rom").write_bytes(b"trainer")
        (tmp_path / "clean.rom").write_bytes(b"clean")

        paths = [
            str(tmp_path / "trainer [t].rom"),
            str(tmp_path / "clean.rom"),
        ]

        results = detect_modified_roms(paths)
        assert len(results) == 1
        assert str(tmp_path / "trainer [t].rom") in results


class TestPlatformSummary:
    """Tests for PlatformSummary."""

    def test_health_score_healthy(self):
        """Test health score for healthy platform."""
        summary = PlatformSummary(
            platform_id="NES",
            total_roms=100,
            verified_good=80,
            clean_roms=90,
            bad_dumps=2,
        )
        assert summary.health_score > 0.5

    def test_health_score_unhealthy(self):
        """Test health score for unhealthy platform."""
        summary = PlatformSummary(
            platform_id="NES",
            total_roms=100,
            bad_dumps=50,
            size_issues=20,
        )
        assert summary.health_score < 0.5

    def test_health_score_empty(self):
        """Test health score with no ROMs."""
        summary = PlatformSummary(platform_id="Empty", total_roms=0)
        assert summary.health_score == 0.0
