"""ROM Integrity Report Generator - F74 Implementation.

Creates comprehensive audit reports for ROM collections.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from .rom_verifier import RomVerifier, VerificationResult, FlagType


@dataclass
class PlatformSummary:
    """Summary statistics for a single platform."""

    platform_id: str
    total_roms: int = 0
    verified_good: int = 0
    bad_dumps: int = 0
    modified: int = 0
    size_issues: int = 0
    unmatched: int = 0
    clean_roms: int = 0

    @property
    def health_score(self) -> float:
        """Calculate platform health score (0.0-1.0)."""
        if self.total_roms == 0:
            return 0.0
        # Clean and verified good count positively
        good = self.clean_roms + self.verified_good
        # Bad dumps and size issues count negatively
        bad = self.bad_dumps + self.size_issues
        # Modified and unmatched are neutral-ish
        return max(0.0, min(1.0, (good - bad * 2) / self.total_roms))


@dataclass
class IntegrityReport:
    """Complete integrity report for a ROM collection."""

    # Metadata
    generated_at: str = ""
    scan_path: str = ""
    total_files_scanned: int = 0
    scan_duration_seconds: float = 0.0

    # Global stats
    total_verified_good: int = 0
    total_bad_dumps: int = 0
    total_modified: int = 0
    total_size_issues: int = 0
    total_unmatched: int = 0
    total_clean: int = 0

    # Per-platform breakdown
    platforms: List[PlatformSummary] = field(default_factory=list)

    # Detailed results (optional, can be large)
    bad_dump_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    size_issue_files: List[str] = field(default_factory=list)
    unmatched_files: List[str] = field(default_factory=list)
    verified_files: List[str] = field(default_factory=list)

    # Full results (if requested)
    full_results: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def overall_health_score(self) -> float:
        """Calculate overall collection health score."""
        if self.total_files_scanned == 0:
            return 0.0
        good = self.total_clean + self.total_verified_good
        bad = self.total_bad_dumps + self.total_size_issues
        return max(0.0, min(1.0, (good - bad * 2) / self.total_files_scanned))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save(self, path: str) -> None:
        """Save report to JSON file."""
        Path(path).write_text(self.to_json(), encoding="utf-8")


class IntegrityReportGenerator:
    """Generates comprehensive integrity reports for ROM collections.

    Implements F74: ROM-Integritäts-Report
    """

    def __init__(self, verifier: RomVerifier):
        """Initialize generator.

        Args:
            verifier: RomVerifier instance to use for verification
        """
        self.verifier = verifier

    def generate(
        self,
        paths: List[str],
        *,
        scan_path: str = "",
        include_full_results: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_event: Optional[object] = None,
    ) -> IntegrityReport:
        """Generate integrity report for given ROM files.

        Args:
            paths: List of ROM file paths to verify
            scan_path: Root path being scanned (for metadata)
            include_full_results: Whether to include full verification results
            progress_callback: Optional callback (current, total, file_path)
            cancel_event: Optional event to check for cancellation

        Returns:
            IntegrityReport with all statistics and findings
        """
        start_time = datetime.now()
        report = IntegrityReport(
            generated_at=start_time.isoformat(),
            scan_path=scan_path,
        )

        # Platform tracking
        platform_stats: Dict[str, PlatformSummary] = {}

        total = len(paths)
        for idx, path in enumerate(paths):
            # Check cancellation
            if cancel_event and hasattr(cancel_event, "is_set"):
                if cancel_event.is_set():  # type: ignore
                    break

            # Progress callback
            if progress_callback:
                progress_callback(idx + 1, total, path)

            # Verify the ROM
            result = self.verifier.verify(path)
            report.total_files_scanned += 1

            # Categorize result
            platform_id = result.dat_platform or "Unknown"

            # Ensure platform exists in stats
            if platform_id not in platform_stats:
                platform_stats[platform_id] = PlatformSummary(platform_id=platform_id)
            ps = platform_stats[platform_id]
            ps.total_roms += 1

            # Track by category
            if not result.dat_matched:
                report.total_unmatched += 1
                report.unmatched_files.append(path)
                ps.unmatched += 1
            elif result.is_clean:
                report.total_clean += 1
                ps.clean_roms += 1

            if result.is_verified_good:
                report.total_verified_good += 1
                report.verified_files.append(path)
                ps.verified_good += 1

            if result.is_bad_dump:
                report.total_bad_dumps += 1
                report.bad_dump_files.append(path)
                ps.bad_dumps += 1

            if result.is_modified:
                report.total_modified += 1
                report.modified_files.append(path)
                ps.modified += 1

            if result.has_size_issue:
                report.total_size_issues += 1
                report.size_issue_files.append(path)
                ps.size_issues += 1

            # Store full result if requested
            if include_full_results:
                report.full_results.append(self._result_to_dict(result))

        # Convert platform stats to list
        report.platforms = sorted(platform_stats.values(), key=lambda p: p.platform_id)

        # Calculate duration
        end_time = datetime.now()
        report.scan_duration_seconds = (end_time - start_time).total_seconds()

        return report

    def generate_from_directory(
        self,
        directory: str,
        *,
        extensions: Optional[List[str]] = None,
        recursive: bool = True,
        include_full_results: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_event: Optional[object] = None,
    ) -> IntegrityReport:
        """Generate report by scanning a directory.

        Args:
            directory: Directory path to scan
            extensions: File extensions to include (default: common ROM extensions)
            recursive: Whether to scan recursively
            include_full_results: Whether to include full verification results
            progress_callback: Optional progress callback
            cancel_event: Optional cancellation event

        Returns:
            IntegrityReport
        """
        if extensions is None:
            extensions = [
                ".nes",
                ".sfc",
                ".smc",
                ".gb",
                ".gbc",
                ".gba",
                ".nds",
                ".n64",
                ".z64",
                ".v64",
                ".md",
                ".smd",
                ".gen",
                ".bin",
                ".iso",
                ".cue",
                ".img",
                ".zip",
                ".7z",
                ".rar",
                ".rom",
                ".a26",
                ".a52",
                ".a78",
                ".lnx",
                ".pce",
                ".sgx",
                ".cdi",
                ".gdi",
                ".chd",
            ]

        dir_path = Path(directory)
        if not dir_path.is_dir():
            return IntegrityReport(scan_path=directory)

        # Collect files
        paths = []
        pattern = "**/*" if recursive else "*"
        for ext in extensions:
            ext_pattern = f"{pattern}{ext}"
            paths.extend(str(p) for p in dir_path.glob(ext_pattern))

        # Remove duplicates and sort
        paths = sorted(set(paths))

        return self.generate(
            paths,
            scan_path=directory,
            include_full_results=include_full_results,
            progress_callback=progress_callback,
            cancel_event=cancel_event,
        )

    def _result_to_dict(self, result: VerificationResult) -> Dict[str, Any]:
        """Convert VerificationResult to dictionary."""
        return {
            "file_path": result.file_path,
            "sha1": result.sha1,
            "crc32": result.crc32,
            "file_size": result.file_size,
            "dat_matched": result.dat_matched,
            "dat_platform": result.dat_platform,
            "dat_rom_name": result.dat_rom_name,
            "dat_set_name": result.dat_set_name,
            "dat_expected_size": result.dat_expected_size,
            "flags": [
                {
                    "type": f.flag_type.name,
                    "pattern": f.raw_pattern,
                    "confidence": f.confidence,
                    "source": f.source,
                }
                for f in result.flags
            ],
            "is_verified_good": result.is_verified_good,
            "is_bad_dump": result.is_bad_dump,
            "is_modified": result.is_modified,
            "has_size_issue": result.has_size_issue,
            "is_clean": result.is_clean,
            "confidence_score": result.confidence_score,
        }


def generate_report(
    paths: List[str],
    verifier: Optional[RomVerifier] = None,
    **kwargs: Any,
) -> IntegrityReport:
    """Convenience function to generate integrity report.

    Args:
        paths: List of ROM file paths
        verifier: Optional verifier instance
        **kwargs: Additional arguments for generate()

    Returns:
        IntegrityReport
    """
    if verifier is None:
        verifier = RomVerifier()
    generator = IntegrityReportGenerator(verifier)
    return generator.generate(paths, **kwargs)
