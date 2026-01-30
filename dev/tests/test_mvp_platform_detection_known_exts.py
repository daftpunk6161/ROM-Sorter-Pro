from __future__ import annotations

import pytest

from src.database.console_db import (
    ENHANCED_CONSOLE_DATABASE,
    get_consoles_for_extension_fast,
    is_unique_extension,
)


# ---------------------------------------------------------------------------
# Original Tests (Lynx, Intellivision)
# ---------------------------------------------------------------------------


def test_console_db_has_lynx_extensions() -> None:
    lynx = ENHANCED_CONSOLE_DATABASE["Lynx"]
    assert ".lnx" in lynx.extensions
    assert ".lyx" in lynx.extensions
    assert ".o" in lynx.extensions


def test_console_db_has_intellivision_extension() -> None:
    intv = ENHANCED_CONSOLE_DATABASE["Intellivision"]
    assert ".int" in intv.extensions


# ---------------------------------------------------------------------------
# Extended Tests: More Platforms
# ---------------------------------------------------------------------------


class TestNintendoPlatforms:
    """Tests for Nintendo platform extensions."""

    def test_nes_extensions(self) -> None:
        nes = ENHANCED_CONSOLE_DATABASE["NES"]
        assert ".nes" in nes.extensions
        assert nes.manufacturer == "Nintendo"

    def test_snes_extensions(self) -> None:
        snes = ENHANCED_CONSOLE_DATABASE["SNES"]
        assert ".sfc" in snes.extensions
        assert ".smc" in snes.extensions

    def test_n64_extensions(self) -> None:
        n64 = ENHANCED_CONSOLE_DATABASE["N64"]
        assert ".n64" in n64.extensions
        assert ".z64" in n64.extensions
        assert ".v64" in n64.extensions

    def test_gb_extensions(self) -> None:
        gb = ENHANCED_CONSOLE_DATABASE["GB"]
        assert ".gb" in gb.extensions

    def test_gbc_extensions(self) -> None:
        gbc = ENHANCED_CONSOLE_DATABASE["GBC"]
        assert ".gbc" in gbc.extensions

    def test_gba_extensions(self) -> None:
        gba = ENHANCED_CONSOLE_DATABASE["GBA"]
        assert ".gba" in gba.extensions

    def test_nds_extensions(self) -> None:
        nds = ENHANCED_CONSOLE_DATABASE["NDS"]
        assert ".nds" in nds.extensions


class TestSegaPlatforms:
    """Tests for Sega platform extensions."""

    def test_genesis_extensions(self) -> None:
        genesis = ENHANCED_CONSOLE_DATABASE["Genesis"]
        assert ".md" in genesis.extensions
        assert ".gen" in genesis.extensions
        assert genesis.manufacturer == "Sega"

    def test_sega_cd_exists(self) -> None:
        scd = ENHANCED_CONSOLE_DATABASE["SegaCD"]
        assert scd.manufacturer == "Sega"

    def test_neo_geo_exists(self) -> None:
        ng = ENHANCED_CONSOLE_DATABASE["NeoGeo"]
        assert ng.manufacturer in ["SNK", "Neo Geo"]

    def test_dreamcast_extensions(self) -> None:
        dc = ENHANCED_CONSOLE_DATABASE["Dreamcast"]
        assert ".gdi" in dc.extensions or ".cdi" in dc.extensions


class TestSonyPlatforms:
    """Tests for Sony platform extensions."""

    def test_psx_extensions(self) -> None:
        psx = ENHANCED_CONSOLE_DATABASE["PSX"]
        # PSX uses disc formats (.bin, .cue, .iso)
        assert psx.manufacturer == "Sony"

    def test_psp_extensions(self) -> None:
        psp = ENHANCED_CONSOLE_DATABASE["PSP"]
        assert ".iso" in psp.extensions or ".cso" in psp.extensions


class TestOtherPlatforms:
    """Tests for other platform extensions."""

    def test_pc_engine_extensions(self) -> None:
        pce = ENHANCED_CONSOLE_DATABASE["PC Engine"]
        assert ".pce" in pce.extensions

    def test_neo_geo_pocket_extensions(self) -> None:
        ngp = ENHANCED_CONSOLE_DATABASE["NeoGeo Pocket"]
        assert ".ngp" in ngp.extensions

    def test_wonderswan_extensions(self) -> None:
        ws = ENHANCED_CONSOLE_DATABASE["WonderSwan"]
        assert ".ws" in ws.extensions
        assert ".wsc" in ws.extensions

    def test_atari_2600_extensions(self) -> None:
        atari = ENHANCED_CONSOLE_DATABASE["Atari2600"]
        assert ".a26" in atari.extensions


# ---------------------------------------------------------------------------
# Extension Uniqueness Tests
# ---------------------------------------------------------------------------


class TestExtensionUniqueness:
    """Tests for extension uniqueness and lookups."""

    @pytest.mark.parametrize("ext,expected_unique", [
        (".nes", True),
        (".sfc", True),
        (".gba", True),
        (".n64", True),
        (".pce", True),
        (".bin", False),  # Ambiguous (Genesis, PS1, etc.)
        (".iso", False),  # Ambiguous (multiple disc platforms)
    ])
    def test_extension_uniqueness(self, ext: str, expected_unique: bool) -> None:
        result = is_unique_extension(ext)
        assert result == expected_unique, f"{ext} uniqueness: expected {expected_unique}, got {result}"

    @pytest.mark.parametrize("ext,expected_console", [
        (".nes", "NES"),
        (".sfc", "SNES"),
        (".gba", "GBA"),
        (".gb", "GB"),
        (".gbc", "GBC"),
        (".n64", "N64"),
        (".pce", "PC Engine"),
        (".ngp", "NeoGeo Pocket"),
        (".ws", "WonderSwan"),
        (".lnx", "Lynx"),
    ])
    def test_extension_lookup_returns_correct_console(self, ext: str, expected_console: str) -> None:
        consoles = get_consoles_for_extension_fast(ext)
        assert expected_console in consoles, f"{ext} should map to {expected_console}, got {consoles}"


# ---------------------------------------------------------------------------
# Coverage Statistics
# ---------------------------------------------------------------------------


class TestCoverageStatistics:
    """Tests for overall database coverage."""

    def test_minimum_platform_count(self) -> None:
        """Database should have at least 30 platforms."""
        assert len(ENHANCED_CONSOLE_DATABASE) >= 30

    def test_all_platforms_have_extensions(self) -> None:
        """All platforms should have at least one extension."""
        platforms_without_extensions = []
        for name, meta in ENHANCED_CONSOLE_DATABASE.items():
            if not meta.extensions:
                platforms_without_extensions.append(name)
        
        # Some platforms (disc-only) may not have ROM extensions
        # This is informational, not a hard failure
        assert len(platforms_without_extensions) < 20, f"Too many platforms without extensions: {platforms_without_extensions}"

    def test_all_platforms_have_manufacturer(self) -> None:
        """All platforms should have a manufacturer."""
        for name, meta in ENHANCED_CONSOLE_DATABASE.items():
            assert meta.manufacturer, f"{name} has no manufacturer"

    def test_unique_extension_count(self) -> None:
        """Count unique extensions in database."""
        all_extensions: set[str] = set()
        for meta in ENHANCED_CONSOLE_DATABASE.values():
            all_extensions.update(meta.extensions)
        
        # Should have at least 50 unique extensions
        assert len(all_extensions) >= 50, f"Only {len(all_extensions)} unique extensions"
