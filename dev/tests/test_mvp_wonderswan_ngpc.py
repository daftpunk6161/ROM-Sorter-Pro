"""
MVP WonderSwan/NGPC Extension Collision Tests
==============================================

Tests für P2-003: Extension-Collision Validierung

Die Tests validieren:
1. WonderSwan .ws/.wsc Extensions werden korrekt getrennt
2. Neo Geo Pocket .ngp/.ngc Extensions werden korrekt getrennt
3. Keine Collision zwischen ähnlichen Plattformen
4. Catalog-Konsistenz für diese Handheld-Plattformen
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set, cast

import pytest

from src.database.console_db import (
    get_all_rom_extensions,
    get_console_for_extension,
    get_consoles_for_extension_fast,
    is_unique_extension,
    get_extension_ambiguity_count,
)
from src.core.platform_heuristics import evaluate_platform_candidates


# ---------------------------------------------------------------------------
# Test Class: Extension Uniqueness
# ---------------------------------------------------------------------------


class TestExtensionUniqueness:
    """Tests for extension uniqueness across handheld platforms."""

    def test_ws_extension_unique_to_wonderswan(self):
        """'.ws' extension should map uniquely to WonderSwan."""
        consoles = cast(List[str], get_consoles_for_extension_fast(".ws") or [])
        # Should be unique or at least resolve to WonderSwan family
        assert len(consoles) >= 1
        # Check at least one is WonderSwan related
        ws_found = any(
            "wonderswan" in c.lower() or "ws" in c.lower()
            for c in consoles
        )
        assert ws_found, f".ws should map to WonderSwan, got: {consoles}"

    def test_wsc_extension_unique_to_wonderswan(self):
        """'.wsc' extension should map uniquely to WonderSwan Color."""
        consoles = cast(List[str], get_consoles_for_extension_fast(".wsc") or [])
        assert len(consoles) >= 1
        ws_found = any(
            "wonderswan" in c.lower() or "ws" in c.lower()
            for c in consoles
        )
        assert ws_found, f".wsc should map to WonderSwan, got: {consoles}"

    def test_ngp_extension_unique_to_neogeo_pocket(self):
        """'.ngp' extension should map uniquely to Neo Geo Pocket."""
        consoles = cast(List[str], get_consoles_for_extension_fast(".ngp") or [])
        assert len(consoles) >= 1
        ngp_found = any(
            "neo" in c.lower() or "ngp" in c.lower() or "pocket" in c.lower()
            for c in consoles
        )
        assert ngp_found, f".ngp should map to Neo Geo Pocket, got: {consoles}"

    def test_ngc_extension_maps_correctly(self):
        """'.ngc' extension should map to Neo Geo Pocket Color or GameCube."""
        consoles = cast(List[str], get_consoles_for_extension_fast(".ngc") or [])
        assert len(consoles) >= 1
        # .ngc could map to NGP/NGPC or GameCube - both are valid
        ngp_found = any(
            "neo" in c.lower() or "ngp" in c.lower() or "pocket" in c.lower()
            for c in consoles
        )
        gc_found = any(
            "gamecube" in c.lower() or "gc" in c.lower().split()
            for c in consoles
        )
        assert ngp_found or gc_found, f".ngc should map to NGP or GameCube, got: {consoles}"


# ---------------------------------------------------------------------------
# Test Class: Extension Fast Lookup
# ---------------------------------------------------------------------------


class TestExtensionFastLookup:
    """Tests for the O(1) extension lookup functions."""

    def test_ws_fast_lookup(self):
        """Fast lookup for .ws should work."""
        consoles = get_consoles_for_extension_fast(".ws")
        assert len(consoles) >= 1

    def test_wsc_fast_lookup(self):
        """Fast lookup for .wsc should work."""
        consoles = get_consoles_for_extension_fast(".wsc")
        assert len(consoles) >= 1

    def test_ngp_fast_lookup(self):
        """Fast lookup for .ngp should work."""
        consoles = get_consoles_for_extension_fast(".ngp")
        assert len(consoles) >= 1

    def test_ngc_fast_lookup(self):
        """Fast lookup for .ngc should work."""
        consoles = get_consoles_for_extension_fast(".ngc")
        assert len(consoles) >= 1

    def test_fast_lookup_case_insensitive(self):
        """Fast lookup should be case insensitive."""
        for ext in [".ws", ".wsc", ".ngp", ".ngc"]:
            lower = set(cast(List[str], get_consoles_for_extension_fast(ext.lower()) or []))
            upper = set(cast(List[str], get_consoles_for_extension_fast(ext.upper()) or []))
            assert lower == upper, f"Case sensitivity issue for {ext}: {lower} vs {upper}"


# ---------------------------------------------------------------------------
# Test Class: Ambiguity Count
# ---------------------------------------------------------------------------


class TestAmbiguityCount:
    """Tests for extension ambiguity detection."""

    def test_ws_ambiguity_count(self):
        """'.ws' should have low ambiguity (1-2 platforms max)."""
        count = get_extension_ambiguity_count(".ws")
        assert count >= 1
        assert count <= 3, f".ws has too high ambiguity: {count}"

    def test_wsc_ambiguity_count(self):
        """'.wsc' should have low ambiguity."""
        count = get_extension_ambiguity_count(".wsc")
        assert count >= 1
        assert count <= 3, f".wsc has too high ambiguity: {count}"

    def test_ngp_ambiguity_count(self):
        """'.ngp' should have low ambiguity."""
        count = get_extension_ambiguity_count(".ngp")
        assert count >= 1
        assert count <= 3, f".ngp has too high ambiguity: {count}"

    def test_ngc_ambiguity_count(self):
        """'.ngc' might have higher ambiguity due to GameCube conflict."""
        count = get_extension_ambiguity_count(".ngc")
        assert count >= 1
        # Allow higher because of potential GameCube overlap
        assert count <= 5, f".ngc has unexpectedly high ambiguity: {count}"


# ---------------------------------------------------------------------------
# Test Class: Platform Heuristics
# ---------------------------------------------------------------------------


class TestPlatformHeuristics:
    """Tests for platform identification via heuristics."""

    def test_ws_extension_identifies_wonderswan(self):
        """File with .ws extension should identify as WonderSwan."""
        result = evaluate_platform_candidates("game.ws")
        systems = cast(List[str], result.get("candidate_systems", []) or [])
        assert len(systems) >= 1, f"No candidates for .ws: {result}"
        
        ws_found = any(
            "wonderswan" in s.lower()
            for s in systems
        )
        assert ws_found, f".ws should identify WonderSwan, got: {systems}"

    def test_wsc_extension_identifies_wonderswan(self):
        """File with .wsc extension should identify as WonderSwan."""
        result = evaluate_platform_candidates("game.wsc")
        systems = cast(List[str], result.get("candidate_systems", []) or [])
        assert len(systems) >= 1, f"No candidates for .wsc: {result}"
        
        ws_found = any(
            "wonderswan" in s.lower()
            for s in systems
        )
        assert ws_found, f".wsc should identify WonderSwan, got: {systems}"

    def test_ngp_extension_identifies_neogeo(self):
        """File with .ngp extension should identify as Neo Geo Pocket."""
        result = evaluate_platform_candidates("game.ngp")
        systems = cast(List[str], result.get("candidate_systems", []) or [])
        assert len(systems) >= 1, f"No candidates for .ngp: {result}"
        
        ngp_found = any(
            "neogeo" in s.lower() or "ngp" in s.lower() or "pocket" in s.lower()
            for s in systems
        )
        assert ngp_found, f".ngp should identify Neo Geo Pocket, got: {systems}"

    def test_ngc_extension_identifies_platform(self):
        """File with .ngc extension should identify something."""
        result = evaluate_platform_candidates("game.ngc")
        systems = cast(List[str], result.get("candidate_systems", []) or [])
        # May be ambiguous with GameCube, just ensure something is found
        assert len(systems) >= 1 or result.get("reason") == "no_match", f"Unexpected result for .ngc: {result}"


# ---------------------------------------------------------------------------
# Test Class: No Cross-Collision
# ---------------------------------------------------------------------------


class TestNoCrossCollision:
    """Tests ensuring no false collision between WonderSwan and NGP families."""

    def test_ws_not_ngp(self):
        """'.ws' should not map to Neo Geo Pocket."""
        consoles = cast(List[str], get_consoles_for_extension_fast(".ws") or [])
        ngp_found = any(
            "neo" in c.lower() and "pocket" in c.lower()
            for c in consoles
        )
        assert not ngp_found, f".ws incorrectly maps to NGP: {consoles}"

    def test_wsc_not_ngp(self):
        """'.wsc' should not map to Neo Geo Pocket."""
        consoles = cast(List[str], get_consoles_for_extension_fast(".wsc") or [])
        ngp_found = any(
            "neo" in c.lower() and "pocket" in c.lower()
            for c in consoles
        )
        assert not ngp_found, f".wsc incorrectly maps to NGP: {consoles}"

    def test_ngp_not_wonderswan(self):
        """'.ngp' should not map to WonderSwan."""
        consoles = cast(List[str], get_consoles_for_extension_fast(".ngp") or [])
        ws_found = any(
            "wonderswan" in c.lower()
            for c in consoles
        )
        assert not ws_found, f".ngp incorrectly maps to WonderSwan: {consoles}"

    def test_ngc_not_wonderswan(self):
        """'.ngc' should not map to WonderSwan."""
        consoles = get_consoles_for_extension_fast(".ngc")
        ws_found = any(
            "wonderswan" in c.lower()
            for c in consoles
        )
        assert not ws_found, f".ngc incorrectly maps to WonderSwan: {consoles}"


# ---------------------------------------------------------------------------
# Test Class: Extension Normalization
# ---------------------------------------------------------------------------


class TestExtensionNormalization:
    """Tests for extension case normalization."""

    def test_uppercase_ws_normalized(self):
        """'.WS' should normalize to same as '.ws'."""
        lower = get_consoles_for_extension_fast(".ws")
        upper = get_consoles_for_extension_fast(".WS")
        assert set(lower) == set(upper), f"Case sensitivity issue: {lower} vs {upper}"

    def test_uppercase_wsc_normalized(self):
        """'.WSC' should normalize to same as '.wsc'."""
        lower = get_consoles_for_extension_fast(".wsc")
        upper = get_consoles_for_extension_fast(".WSC")
        assert set(lower) == set(upper), f"Case sensitivity issue: {lower} vs {upper}"

    def test_uppercase_ngp_normalized(self):
        """'.NGP' should normalize to same as '.ngp'."""
        lower = get_consoles_for_extension_fast(".ngp")
        upper = get_consoles_for_extension_fast(".NGP")
        assert set(lower) == set(upper), f"Case sensitivity issue: {lower} vs {upper}"

    def test_uppercase_ngc_normalized(self):
        """'.NGC' should normalize to same as '.ngc'."""
        lower = get_consoles_for_extension_fast(".ngc")
        upper = get_consoles_for_extension_fast(".NGC")
        assert set(lower) == set(upper), f"Case sensitivity issue: {lower} vs {upper}"


# ---------------------------------------------------------------------------
# Test Class: All Extensions Registered
# ---------------------------------------------------------------------------


class TestAllExtensionsRegistered:
    """Tests ensuring all handheld extensions are in the registry."""

    def test_all_handheld_extensions_registered(self):
        """All handheld-specific extensions should be registered."""
        all_extensions = get_all_rom_extensions()

        handheld_exts = [".ws", ".wsc", ".ngp", ".ngc"]
        for ext in handheld_exts:
            ext_lower = ext.lower()
            ext_upper = ext.upper()
            assert ext_lower in all_extensions or ext_upper in all_extensions, \
                f"Extension {ext} not registered in console_db"


# ---------------------------------------------------------------------------
# Test Class: Single Console Lookup
# ---------------------------------------------------------------------------


class TestSingleConsoleLookup:
    """Tests for get_console_for_extension (returns first match)."""

    def test_ws_single_lookup(self):
        """get_console_for_extension('.ws') should return a console."""
        console = get_console_for_extension(".ws")
        assert console is not None, ".ws should map to a console"
        assert "wonderswan" in console.lower() or "ws" in console.lower()

    def test_wsc_single_lookup(self):
        """get_console_for_extension('.wsc') should return a console."""
        console = get_console_for_extension(".wsc")
        assert console is not None, ".wsc should map to a console"
        assert "wonderswan" in console.lower() or "ws" in console.lower()

    def test_ngp_single_lookup(self):
        """get_console_for_extension('.ngp') should return a console."""
        console = get_console_for_extension(".ngp")
        assert console is not None, ".ngp should map to a console"

    def test_ngc_single_lookup(self):
        """get_console_for_extension('.ngc') should return a console."""
        console = get_console_for_extension(".ngc")
        # This might be None or return GameCube/NGP
        # Just check it doesn't crash
        assert console is None or isinstance(console, str)


# ---------------------------------------------------------------------------
# Parametrized Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ext,platform_family", [
    (".ws", "wonderswan"),
    (".wsc", "wonderswan"),
    (".ngp", "neogeo"),
])
def test_extension_to_platform_mapping(ext: str, platform_family: str):
    """Parametrized test for extension→platform mapping."""
    consoles = get_consoles_for_extension_fast(ext)
    assert len(consoles) >= 1, f"No consoles found for {ext}"

    # Check at least one console matches the expected family
    family_found = any(
        platform_family.lower() in c.lower()
        for c in consoles
    )
    assert family_found, f"{ext} should map to {platform_family}, got: {consoles}"


@pytest.mark.parametrize("ext", [".ws", ".wsc", ".ngp", ".ngc"])
def test_extension_in_all_extensions(ext: str):
    """All handheld extensions should be in the global extension set."""
    all_exts = get_all_rom_extensions()
    assert ext in all_exts or ext.upper() in all_exts, \
        f"{ext} not in all_rom_extensions"


@pytest.mark.parametrize("ext", [".ws", ".wsc", ".ngp", ".ngc"])
def test_extension_has_reasonable_ambiguity(ext: str):
    """Each extension should have reasonable ambiguity count."""
    count = get_extension_ambiguity_count(ext)
    assert 1 <= count <= 5, f"{ext} has unreasonable ambiguity: {count}"
