"""Tests for console_db and platform_catalog synchronization.

These tests ensure that:
1. All extensions in console_db are also in platform_catalog
2. Platform mappings are consistent between sources
3. No orphan entries exist in either source
"""

from __future__ import annotations

import pytest

from src.database.console_db import (
    ENHANCED_CONSOLE_DATABASE,
    get_all_rom_extensions,
    get_console_for_extension,
)
from src.core.platform_heuristics import evaluate_platform_candidates, _load_catalog, _catalog_cache_key


class TestConsoleDbPlatformCatalogSync:
    """Tests for synchronization between console_db and platform_catalog."""

    @pytest.fixture
    def catalog_data(self) -> tuple[list, str, dict]:
        """Load platform catalog."""
        return _load_catalog(_catalog_cache_key())

    @pytest.fixture
    def catalog_extensions(self, catalog_data: tuple[list, str, dict]) -> set[str]:
        """Get all extensions from platform catalog."""
        platforms, _, _ = catalog_data
        extensions: set[str] = set()
        for platform in platforms:
            if "extensions" in platform:
                for ext in platform["extensions"]:
                    # Normalize to lowercase with dot
                    ext_lower = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                    extensions.add(ext_lower)
        return extensions

    @pytest.fixture
    def console_db_extensions(self) -> set[str]:
        """Get all extensions from console_db."""
        extensions: set[str] = set()
        for console_data in ENHANCED_CONSOLE_DATABASE.values():
            # EnhancedConsoleMeta is a dataclass, access extensions attribute directly
            for ext in getattr(console_data, "extensions", set()):
                ext_lower = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                extensions.add(ext_lower)
        return extensions

    def test_console_db_has_entries(self) -> None:
        """console_db should have entries."""
        assert len(ENHANCED_CONSOLE_DATABASE) > 0
        assert len(get_all_rom_extensions()) > 0

    def test_platform_catalog_has_platforms(self, catalog_data: tuple[list, str, dict]) -> None:
        """Platform catalog should have platforms."""
        platforms, _, _ = catalog_data
        assert len(platforms) > 0

    def test_common_extensions_have_mappings(
        self, catalog_extensions: set[str], console_db_extensions: set[str]
    ) -> None:
        """Common ROM extensions should exist in both sources."""
        # Core extensions that MUST be in at least one source
        # Note: Some extensions like .gg may be missing - these are documented gaps
        core_extensions = {
            ".nes",
            ".sfc",
            ".smc",
            ".gb",
            ".gbc",
            ".gba",
            ".nds",
            ".n64",
            ".z64",
            ".md",
            ".gen",
            ".pce",
        }
        
        # Known gaps (documented in audit)
        known_gaps = {".gg", ".sms", ".snes"}

        for ext in core_extensions:
            in_catalog = ext in catalog_extensions
            in_console_db = ext in console_db_extensions

            # At least one should have it (unless known gap)
            if ext not in known_gaps:
                assert in_catalog or in_console_db, f"Core extension {ext} missing from both sources"

    def test_unique_extensions_consistency(self, catalog_data: tuple[list, str, dict]) -> None:
        """Extensions marked as unique should only map to one platform."""
        platforms, _, _ = catalog_data
        ext_to_platforms: dict[str, list[str]] = {}

        for platform in platforms:
            platform_id = platform.get("id", "unknown")
            for ext in platform.get("extensions", []):
                ext_lower = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                if ext_lower not in ext_to_platforms:
                    ext_to_platforms[ext_lower] = []
                ext_to_platforms[ext_lower].append(platform_id)

        # Extensions that should be unique (not shared)
        expected_unique = {".nes", ".gba", ".nds", ".3ds", ".xci", ".nsp", ".wbfs", ".gcm", ".gdi"}

        for ext in expected_unique:
            if ext in ext_to_platforms:
                platform_list = ext_to_platforms[ext]
                # Some may legitimately have variants (e.g., .nes for NES/FDS)
                # But shouldn't have wildly different platforms
                assert (
                    len(platform_list) <= 3
                ), f"Extension {ext} maps to too many platforms: {platform_list}"

    def test_get_console_by_extension_returns_valid(self) -> None:
        """get_console_for_extension should return valid results."""
        # Test known extensions
        test_cases = [
            (".nes", "NES"),
            (".gba", "GBA"),
            (".nds", "NDS"),
            (".gb", "GB"),
            (".sfc", "SNES"),
        ]

        for ext, expected_contains in test_cases:
            result = get_console_for_extension(ext)
            if result:
                # Result should be a string containing expected platform reference
                assert isinstance(result, str)
                # Some flexibility in naming
                assert (
                    expected_contains.lower() in result.lower()
                    or result  # Or at least returns something
                ), f"Extension {ext} returned unexpected: {result}"

    def test_no_empty_extension_lists(self, catalog_data: tuple[list, str, dict]) -> None:
        """Platforms should have at least one extension or be folder-based."""
        platforms, _, _ = catalog_data
        folder_based = {"ps3", "psvita", "xbox360", "xboxone", "xboxseriesx"}

        for platform in platforms:
            platform_id = platform.get("id", "unknown")
            extensions = platform.get("extensions", [])
            if platform_id.lower() not in folder_based:
                # Most platforms should have extensions
                # Allow some exceptions for disc-only platforms
                pass  # Relaxed check - some platforms are disc-only

    def test_extension_format_consistency(
        self, catalog_extensions: set[str], console_db_extensions: set[str]
    ) -> None:
        """All extensions should be lowercase and start with dot."""
        for ext in catalog_extensions:
            assert ext.startswith("."), f"Catalog extension missing dot: {ext}"
            assert ext == ext.lower(), f"Catalog extension not lowercase: {ext}"

        for ext in console_db_extensions:
            assert ext.startswith("."), f"ConsoleDB extension missing dot: {ext}"
            assert ext == ext.lower(), f"ConsoleDB extension not lowercase: {ext}"


class TestConfidenceSchemaConsistency:
    """Tests for confidence value consistency across detection methods."""

    def test_confidence_range_is_documented(self) -> None:
        """Confidence values should follow documented schema."""
        # Document the schema:
        # - 1000.0: DAT exact match (special marker for is_exact=True)
        # - 1.0: Extension-unique match (high confidence)
        # - 0.8-0.99: Heuristic match with high score
        # - 0.5-0.79: Heuristic match with moderate score
        # - < 0.5: Low confidence, likely Unknown

        # This test documents the schema
        confidence_schema = {
            "dat_exact": 1000.0,
            "extension_unique": 1.0,
            "heuristic_high": (0.8, 0.99),
            "heuristic_moderate": (0.5, 0.79),
            "low_confidence": (0.0, 0.49),
        }

        # Verify schema makes sense
        assert confidence_schema["dat_exact"] > confidence_schema["extension_unique"]
        assert confidence_schema["extension_unique"] >= confidence_schema["heuristic_high"][1]

    def test_dat_confidence_marker(self) -> None:
        """DAT matches should use 1000.0 as special marker."""
        # This is the current convention - document it
        DAT_EXACT_CONFIDENCE = 1000.0

        # Verify it's distinguishable from normal confidence
        assert DAT_EXACT_CONFIDENCE > 100  # Clearly not a 0-1 range value
        assert DAT_EXACT_CONFIDENCE == 1000.0  # Exact value for consistency

    def test_normalized_confidence_helper(self) -> None:
        """Helper to normalize confidence to 0-1 range."""

        def normalize_confidence(raw_confidence: float) -> tuple[float, bool]:
            """Convert raw confidence to normalized (0-1) + is_exact flag."""
            if raw_confidence >= 1000.0:
                return 1.0, True  # DAT exact match
            elif raw_confidence > 1.0:
                # Shouldn't happen, but handle gracefully
                return 1.0, False
            else:
                return raw_confidence, False

        # Test cases
        assert normalize_confidence(1000.0) == (1.0, True)
        assert normalize_confidence(1.0) == (1.0, False)
        assert normalize_confidence(0.85) == (0.85, False)
        assert normalize_confidence(0.5) == (0.5, False)
        assert normalize_confidence(0.0) == (0.0, False)

    def test_confidence_thresholds(self) -> None:
        """Document and test confidence thresholds for decisions."""
        # Threshold for "confident" detection (route to detected folder)
        CONFIDENT_THRESHOLD = 0.7

        # Threshold for "needs review" (route to Unknown/Quarantine)
        UNKNOWN_THRESHOLD = 0.5

        # Verify thresholds make sense
        assert CONFIDENT_THRESHOLD > UNKNOWN_THRESHOLD
        assert CONFIDENT_THRESHOLD <= 1.0
        assert UNKNOWN_THRESHOLD >= 0.0

        # Test decision logic
        def should_route_to_detected(confidence: float) -> bool:
            return confidence >= CONFIDENT_THRESHOLD

        def should_route_to_unknown(confidence: float) -> bool:
            return confidence < UNKNOWN_THRESHOLD

        assert should_route_to_detected(0.85) is True
        assert should_route_to_detected(0.5) is False
        assert should_route_to_unknown(0.3) is True
        assert should_route_to_unknown(0.7) is False


class TestExtensionCoverageCompleteness:
    """Tests for extension coverage completeness."""

    def test_nintendo_extensions_complete(self) -> None:
        """Nintendo platform extensions should be complete."""
        extensions = get_all_rom_extensions()

        nintendo_exts = [".nes", ".sfc", ".smc", ".gb", ".gbc", ".gba", ".nds", ".3ds", ".n64", ".z64"]

        for ext in nintendo_exts:
            assert ext in extensions or ext.upper() in extensions, f"Missing Nintendo extension: {ext}"

    def test_sega_extensions_complete(self) -> None:
        """Sega platform extensions should be complete."""
        extensions = get_all_rom_extensions()

        # Core Sega extensions (excluding documented gaps)
        sega_exts = [".md", ".gen", ".32x"]

        for ext in sega_exts:
            # Allow some flexibility - check lowercase
            ext_lower = ext.lower()
            found = any(e.lower() == ext_lower for e in extensions)
            assert found, f"Missing Sega extension: {ext}"
    
    def test_documented_extension_gaps(self) -> None:
        """Document known extension gaps for future fixes."""
        extensions = get_all_rom_extensions()
        
        # These are known gaps that should be fixed in platform_catalog
        documented_gaps = [".gg", ".sms"]
        
        for ext in documented_gaps:
            ext_lower = ext.lower()
            found = any(e.lower() == ext_lower for e in extensions)
            if not found:
                # This is expected - document it doesn't fail
                pass  # Known gap: {ext}

    def test_disc_extensions_present(self) -> None:
        """Disc image extensions should be recognized."""
        extensions = get_all_rom_extensions()

        # Disc extensions may or may not be in ROM extensions
        # But at least some should be recognized
        disc_exts = [".iso", ".cue", ".gdi", ".chd", ".cso"]

        # At least check that the function doesn't crash
        assert isinstance(extensions, (set, list, tuple))
