"""MiSTer FPGA Exporter - F69 Implementation.

Exports ROMs in MiSTer FPGA folder format.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class MiSTerCore(Enum):
    """MiSTer FPGA cores."""

    # Nintendo
    NES = auto()
    SNES = auto()
    GAMEBOY = auto()
    GBA = auto()
    N64 = auto()

    # Sega
    GENESIS = auto()
    SMS = auto()
    GAME_GEAR = auto()
    SATURN = auto()

    # Other
    TURBOGRAFX = auto()
    NEO_GEO = auto()
    ARCADE = auto()
    PSX = auto()
    ATARI2600 = auto()
    ATARI7800 = auto()


@dataclass
class MiSTerCoreConfig:
    """MiSTer core configuration."""

    core: MiSTerCore
    folder_name: str
    extensions: List[str]
    rbf_name: str  # Core filename
    supports_subfolders: bool = True


# MiSTer folder structure
MISTER_CORES: Dict[MiSTerCore, MiSTerCoreConfig] = {
    MiSTerCore.NES: MiSTerCoreConfig(
        core=MiSTerCore.NES,
        folder_name="NES",
        extensions=[".nes", ".fds", ".nsf"],
        rbf_name="NES",
        supports_subfolders=True,
    ),
    MiSTerCore.SNES: MiSTerCoreConfig(
        core=MiSTerCore.SNES,
        folder_name="SNES",
        extensions=[".sfc", ".smc", ".bs"],
        rbf_name="SNES",
        supports_subfolders=True,
    ),
    MiSTerCore.GAMEBOY: MiSTerCoreConfig(
        core=MiSTerCore.GAMEBOY,
        folder_name="GAMEBOY",
        extensions=[".gb", ".gbc"],
        rbf_name="Gameboy",
        supports_subfolders=True,
    ),
    MiSTerCore.GBA: MiSTerCoreConfig(
        core=MiSTerCore.GBA,
        folder_name="GBA",
        extensions=[".gba"],
        rbf_name="GBA",
        supports_subfolders=True,
    ),
    MiSTerCore.N64: MiSTerCoreConfig(
        core=MiSTerCore.N64,
        folder_name="N64",
        extensions=[".n64", ".z64", ".v64"],
        rbf_name="N64",
        supports_subfolders=True,
    ),
    MiSTerCore.GENESIS: MiSTerCoreConfig(
        core=MiSTerCore.GENESIS,
        folder_name="Genesis",
        extensions=[".md", ".bin", ".gen"],
        rbf_name="Genesis",
        supports_subfolders=True,
    ),
    MiSTerCore.SMS: MiSTerCoreConfig(
        core=MiSTerCore.SMS,
        folder_name="SMS",
        extensions=[".sms", ".sg"],
        rbf_name="SMS",
        supports_subfolders=True,
    ),
    MiSTerCore.GAME_GEAR: MiSTerCoreConfig(
        core=MiSTerCore.GAME_GEAR,
        folder_name="GameGear",
        extensions=[".gg"],
        rbf_name="SMS",  # Uses SMS core
        supports_subfolders=True,
    ),
    MiSTerCore.TURBOGRAFX: MiSTerCoreConfig(
        core=MiSTerCore.TURBOGRAFX,
        folder_name="TGFX16",
        extensions=[".pce", ".sgx"],
        rbf_name="TurboGrafx16",
        supports_subfolders=True,
    ),
    MiSTerCore.NEO_GEO: MiSTerCoreConfig(
        core=MiSTerCore.NEO_GEO,
        folder_name="NEOGEO",
        extensions=[".neo"],
        rbf_name="NeoGeo",
        supports_subfolders=True,
    ),
    MiSTerCore.ARCADE: MiSTerCoreConfig(
        core=MiSTerCore.ARCADE,
        folder_name="_Arcade",
        extensions=[".mra"],
        rbf_name="",  # Varies
        supports_subfolders=True,
    ),
    MiSTerCore.PSX: MiSTerCoreConfig(
        core=MiSTerCore.PSX,
        folder_name="PSX",
        extensions=[".cue", ".chd"],
        rbf_name="PSX",
        supports_subfolders=True,
    ),
    MiSTerCore.ATARI2600: MiSTerCoreConfig(
        core=MiSTerCore.ATARI2600,
        folder_name="ATARI2600",
        extensions=[".a26", ".bin"],
        rbf_name="Atari2600",
        supports_subfolders=True,
    ),
    MiSTerCore.ATARI7800: MiSTerCoreConfig(
        core=MiSTerCore.ATARI7800,
        folder_name="ATARI7800",
        extensions=[".a78", ".bin"],
        rbf_name="Atari7800",
        supports_subfolders=True,
    ),
    MiSTerCore.SATURN: MiSTerCoreConfig(
        core=MiSTerCore.SATURN,
        folder_name="Saturn",
        extensions=[".cue", ".chd"],
        rbf_name="Saturn",
        supports_subfolders=True,
    ),
}

# System name to MiSTer core mapping
SYSTEM_TO_CORE: Dict[str, MiSTerCore] = {
    "nes": MiSTerCore.NES,
    "nintendo entertainment system": MiSTerCore.NES,
    "famicom": MiSTerCore.NES,
    "snes": MiSTerCore.SNES,
    "super nintendo": MiSTerCore.SNES,
    "super famicom": MiSTerCore.SNES,
    "gb": MiSTerCore.GAMEBOY,
    "gameboy": MiSTerCore.GAMEBOY,
    "game boy": MiSTerCore.GAMEBOY,
    "gbc": MiSTerCore.GAMEBOY,
    "game boy color": MiSTerCore.GAMEBOY,
    "gba": MiSTerCore.GBA,
    "game boy advance": MiSTerCore.GBA,
    "n64": MiSTerCore.N64,
    "nintendo 64": MiSTerCore.N64,
    "genesis": MiSTerCore.GENESIS,
    "mega drive": MiSTerCore.GENESIS,
    "megadrive": MiSTerCore.GENESIS,
    "sms": MiSTerCore.SMS,
    "master system": MiSTerCore.SMS,
    "sega master system": MiSTerCore.SMS,
    "gg": MiSTerCore.GAME_GEAR,
    "game gear": MiSTerCore.GAME_GEAR,
    "tg16": MiSTerCore.TURBOGRAFX,
    "turbografx": MiSTerCore.TURBOGRAFX,
    "turbografx-16": MiSTerCore.TURBOGRAFX,
    "pc engine": MiSTerCore.TURBOGRAFX,
    "neogeo": MiSTerCore.NEO_GEO,
    "neo geo": MiSTerCore.NEO_GEO,
    "arcade": MiSTerCore.ARCADE,
    "psx": MiSTerCore.PSX,
    "playstation": MiSTerCore.PSX,
    "ps1": MiSTerCore.PSX,
    "atari 2600": MiSTerCore.ATARI2600,
    "atari2600": MiSTerCore.ATARI2600,
    "atari 7800": MiSTerCore.ATARI7800,
    "atari7800": MiSTerCore.ATARI7800,
    "saturn": MiSTerCore.SATURN,
    "sega saturn": MiSTerCore.SATURN,
}


@dataclass
class ExportResult:
    """Export result."""

    success: bool
    exported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    total_size_bytes: int = 0
    errors: List[str] = field(default_factory=list)


class MiSTerExporter:
    """MiSTer FPGA exporter.

    Implements F69: Export-to-MiSTer-SD

    Features:
    - MiSTer folder structure
    - Core-specific folders
    - Subfolder organization
    - Extension validation
    """

    def __init__(
        self,
        mister_path: str,
        create_subfolders: bool = True,
        organize_by_letter: bool = False,
        organize_by_region: bool = False,
    ):
        """Initialize MiSTer exporter.

        Args:
            mister_path: Path to MiSTer SD card root (/media/fat)
            create_subfolders: Create subfolders for organization
            organize_by_letter: Organize by first letter (A-Z, #)
            organize_by_region: Organize by region (USA, EUR, JPN, etc.)
        """
        self._mister_path = Path(mister_path)
        self._create_subfolders = create_subfolders
        self._organize_by_letter = organize_by_letter
        self._organize_by_region = organize_by_region

        self._games_path = self._mister_path / "games"

    def _get_core_for_system(self, system: str) -> Optional[MiSTerCore]:
        """Get MiSTer core for system name.

        Args:
            system: System name

        Returns:
            MiSTerCore or None
        """
        system_lower = system.lower()
        return SYSTEM_TO_CORE.get(system_lower)

    def _get_subfolder(self, name: str, region: Optional[str] = None) -> str:
        """Get subfolder name for organization.

        Args:
            name: ROM name
            region: Optional region

        Returns:
            Subfolder name
        """
        if self._organize_by_region and region:
            return region.upper()

        if self._organize_by_letter:
            first = name[0].upper() if name else "#"
            return first if first.isalpha() else "#"

        return ""

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for FAT32.

        Args:
            name: Original filename

        Returns:
            Sanitized filename
        """
        # Characters not allowed in FAT32
        invalid = '<>:"/\\|?*'
        result = name

        for char in invalid:
            result = result.replace(char, "_")

        # Trim trailing spaces/dots
        result = result.rstrip(". ")

        # Limit length
        if len(result) > 200:
            stem = Path(result).stem[:196]
            suffix = Path(result).suffix
            result = stem + suffix

        return result

    def export_roms(
        self,
        roms: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> ExportResult:
        """Export ROMs to MiSTer format.

        Args:
            roms: List of ROM dicts with path, system, name, region
            progress_callback: Progress callback(current, total, filename)
            cancel_token: Cancellation token

        Returns:
            ExportResult
        """
        result = ExportResult(success=True)

        total = len(roms)
        for i, rom in enumerate(roms):
            # Check cancellation
            if cancel_token and hasattr(cancel_token, "is_set") and cancel_token.is_set():
                result.success = False
                result.errors.append("Export cancelled")
                break

            rom_path = Path(rom.get("path", ""))
            system = rom.get("system", "")
            name = rom.get("name", rom_path.name)
            region = rom.get("region")

            if progress_callback:
                progress_callback(i + 1, total, name)

            # Get core
            core = self._get_core_for_system(system)
            if not core:
                result.skipped_count += 1
                continue

            config = MISTER_CORES.get(core)
            if not config:
                result.skipped_count += 1
                continue

            # Check extension
            ext = rom_path.suffix.lower()
            if ext not in config.extensions:
                result.skipped_count += 1
                continue

            # Build target path
            target_folder = self._games_path / config.folder_name

            if self._create_subfolders and config.supports_subfolders:
                subfolder = self._get_subfolder(name, region)
                if subfolder:
                    target_folder = target_folder / subfolder

            target_folder.mkdir(parents=True, exist_ok=True)

            # Sanitize and copy
            safe_name = self._sanitize_filename(rom_path.name)
            target_path = target_folder / safe_name

            try:
                if not rom_path.exists():
                    result.errors.append(f"Source not found: {rom_path}")
                    result.error_count += 1
                    continue

                shutil.copy2(rom_path, target_path)
                result.exported_count += 1
                result.total_size_bytes += rom_path.stat().st_size

            except Exception as e:
                result.errors.append(f"Failed to export {name}: {e}")
                result.error_count += 1

        result.success = result.error_count == 0
        return result

    def export_from_collection(
        self,
        collection_path: str,
        systems: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> ExportResult:
        """Export from a collection directory.

        Args:
            collection_path: Path to organized ROM collection
            systems: Optional list of systems to export
            progress_callback: Progress callback

        Returns:
            ExportResult
        """
        roms = []
        collection = Path(collection_path)

        for system_folder in collection.iterdir():
            if not system_folder.is_dir():
                continue

            system_name = system_folder.name

            # Filter systems
            if systems:
                if not any(s.lower() in system_name.lower() for s in systems):
                    continue

            # Check if we have a core for this system
            core = self._get_core_for_system(system_name)
            if not core:
                continue

            config = MISTER_CORES.get(core)
            if not config:
                continue

            # Scan ROMs
            for rom_file in system_folder.rglob("*"):
                if not rom_file.is_file():
                    continue

                ext = rom_file.suffix.lower()
                if ext not in config.extensions:
                    continue

                # Extract region from filename
                name = rom_file.stem
                region = None
                for r in ["USA", "EUR", "JPN", "World"]:
                    if f"({r})" in name:
                        region = r
                        break

                roms.append(
                    {
                        "path": str(rom_file),
                        "system": system_name,
                        "name": name,
                        "region": region,
                    }
                )

        return self.export_roms(roms, progress_callback)

    def get_supported_systems(self) -> List[Dict[str, Any]]:
        """Get list of supported systems.

        Returns:
            List of system info
        """
        result = []

        for core, config in MISTER_CORES.items():
            result.append(
                {
                    "core": core.name,
                    "folder": config.folder_name,
                    "extensions": config.extensions,
                    "rbf": config.rbf_name,
                }
            )

        return result

    def validate_sd_card(self) -> Dict[str, Any]:
        """Validate MiSTer SD card structure.

        Returns:
            Validation result
        """
        result = {
            "valid": False,
            "is_mister": False,
            "games_folder": False,
            "cores_found": [],
            "errors": [],
        }

        if not self._mister_path.exists():
            result["errors"].append(f"Path not found: {self._mister_path}")
            return result

        # Check for MiSTer indicators
        mister_markers = ["MiSTer", "config", "games"]
        found_markers = 0

        for marker in mister_markers:
            if (self._mister_path / marker).exists():
                found_markers += 1

        result["is_mister"] = found_markers >= 2

        # Check games folder
        if self._games_path.exists():
            result["games_folder"] = True

            # Check which cores have folders
            for core, config in MISTER_CORES.items():
                core_folder = self._games_path / config.folder_name
                if core_folder.exists():
                    result["cores_found"].append(config.folder_name)

        result["valid"] = result["is_mister"] or result["games_folder"]

        return result

    def create_folder_structure(self) -> bool:
        """Create standard MiSTer folder structure.

        Returns:
            True if successful
        """
        try:
            self._games_path.mkdir(parents=True, exist_ok=True)

            for core, config in MISTER_CORES.items():
                core_folder = self._games_path / config.folder_name
                core_folder.mkdir(exist_ok=True)

            return True

        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get exporter status.

        Returns:
            Status dict
        """
        validation = self.validate_sd_card()

        return {
            "mister_path": str(self._mister_path),
            "games_path": str(self._games_path),
            "is_valid": validation["valid"],
            "is_mister": validation["is_mister"],
            "cores_found": len(validation["cores_found"]),
            "organize_by_letter": self._organize_by_letter,
            "organize_by_region": self._organize_by_region,
        }
