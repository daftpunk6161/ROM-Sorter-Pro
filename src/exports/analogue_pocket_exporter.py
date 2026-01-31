"""Analogue Pocket Exporter - F88 Implementation.

Exports ROMs in OpenFPGA format for Analogue Pocket.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class PocketCore(Enum):
    """Known Analogue Pocket cores."""

    # Nintendo
    SPIRITUALIZED_GBC = "Spiritualized.GBC"
    SPIRITUALIZED_GB = "Spiritualized.GB"
    BUDUDE2_GBA = "Budude2.GBA"
    AGARANDOM_NES = "agg23.NES"
    SPACEMEN3_SNES = "Spacemen3.SNES"

    # Sega
    ERICLEWIS_GENESIS = "ericlewis.Genesis"
    GENESIS_PLUS = "Spiritualized.Genesis"
    MASTER_SYSTEM = "Spiritualized.SMS"
    GAME_GEAR = "Spiritualized.GG"

    # Other
    PC_ENGINE = "Spiritualized.PCE"
    NEO_GEO = "Mazamars312.NeoGeo"
    ARCADE = "Coin-Op"


@dataclass
class PocketCoreConfig:
    """Configuration for a Pocket core."""

    core: PocketCore
    platform_ids: List[str]
    rom_folder: str
    supported_extensions: List[str]
    assets_folder: Optional[str] = None


# Core configurations
POCKET_CORES: Dict[PocketCore, PocketCoreConfig] = {
    PocketCore.SPIRITUALIZED_GBC: PocketCoreConfig(
        core=PocketCore.SPIRITUALIZED_GBC,
        platform_ids=["gbc", "gameboy_color"],
        rom_folder="Assets/gbc/common",
        supported_extensions=[".gbc", ".gb"],
    ),
    PocketCore.SPIRITUALIZED_GB: PocketCoreConfig(
        core=PocketCore.SPIRITUALIZED_GB,
        platform_ids=["gb", "gameboy"],
        rom_folder="Assets/gb/common",
        supported_extensions=[".gb"],
    ),
    PocketCore.BUDUDE2_GBA: PocketCoreConfig(
        core=PocketCore.BUDUDE2_GBA,
        platform_ids=["gba", "gameboy_advance"],
        rom_folder="Assets/gba/common",
        supported_extensions=[".gba"],
    ),
    PocketCore.AGARANDOM_NES: PocketCoreConfig(
        core=PocketCore.AGARANDOM_NES,
        platform_ids=["nes", "famicom"],
        rom_folder="Assets/nes/common",
        supported_extensions=[".nes"],
    ),
    PocketCore.SPACEMEN3_SNES: PocketCoreConfig(
        core=PocketCore.SPACEMEN3_SNES,
        platform_ids=["snes", "sfc", "super_famicom"],
        rom_folder="Assets/snes/common",
        supported_extensions=[".sfc", ".smc"],
    ),
    PocketCore.ERICLEWIS_GENESIS: PocketCoreConfig(
        core=PocketCore.ERICLEWIS_GENESIS,
        platform_ids=["genesis", "megadrive", "mega_drive"],
        rom_folder="Assets/genesis/common",
        supported_extensions=[".md", ".bin", ".gen"],
    ),
    PocketCore.MASTER_SYSTEM: PocketCoreConfig(
        core=PocketCore.MASTER_SYSTEM,
        platform_ids=["sms", "master_system"],
        rom_folder="Assets/sms/common",
        supported_extensions=[".sms"],
    ),
    PocketCore.GAME_GEAR: PocketCoreConfig(
        core=PocketCore.GAME_GEAR,
        platform_ids=["gg", "gamegear", "game_gear"],
        rom_folder="Assets/gg/common",
        supported_extensions=[".gg"],
    ),
    PocketCore.PC_ENGINE: PocketCoreConfig(
        core=PocketCore.PC_ENGINE,
        platform_ids=["pce", "pc_engine", "tg16", "turbografx"],
        rom_folder="Assets/pce/common",
        supported_extensions=[".pce", ".sgx"],
    ),
}


@dataclass
class ExportResult:
    """Result of export operation."""

    success: bool
    exported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    total_size_bytes: int = 0
    errors: List[str] = field(default_factory=list)
    cores_used: List[str] = field(default_factory=list)


class AnaloguePocketExporter:
    """Exports ROMs for Analogue Pocket.

    Implements F88: Analogue-Pocket-Export

    Features:
    - OpenFPGA folder structure
    - Core-specific organization
    - Assets folder management
    - JSON library generation
    """

    def __init__(self, custom_cores: Optional[Dict[str, PocketCoreConfig]] = None):
        """Initialize exporter.

        Args:
            custom_cores: Custom core configurations
        """
        self._cores = dict(POCKET_CORES)
        if custom_cores:
            self._cores.update(custom_cores)

    def export(
        self,
        roms: List[Dict[str, Any]],
        target_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        create_library_json: bool = True,
    ) -> ExportResult:
        """Export ROMs to Analogue Pocket format.

        Args:
            roms: List of ROM dicts with 'path', 'platform', 'name'
            target_path: Target SD card path
            progress_callback: Progress callback
            create_library_json: Create library.json files

        Returns:
            ExportResult
        """
        result = ExportResult(success=True)
        target = Path(target_path)
        target.mkdir(parents=True, exist_ok=True)

        # Create base folders
        (target / "Assets").mkdir(exist_ok=True)
        (target / "Cores").mkdir(exist_ok=True)
        (target / "Platforms").mkdir(exist_ok=True)

        total = len(roms)
        library_entries: Dict[str, List[Dict[str, str]]] = {}

        for i, rom in enumerate(roms):
            rom_path = Path(rom.get("path", ""))
            platform = rom.get("platform", "unknown").lower()
            name = rom.get("name", rom_path.stem)

            if progress_callback:
                progress_callback(i + 1, total, name)

            # Find matching core
            core_config = self._find_core_for_platform(platform)
            if not core_config:
                result.skipped_count += 1
                result.errors.append(f"No core for platform: {platform}")
                continue

            # Check extension
            if rom_path.suffix.lower() not in core_config.supported_extensions:
                result.skipped_count += 1
                result.errors.append(f"Unsupported extension: {rom_path.name}")
                continue

            # Create destination folder
            dest_folder = target / core_config.rom_folder
            dest_folder.mkdir(parents=True, exist_ok=True)

            # Sanitize filename
            safe_name = self._sanitize_filename(name, rom_path.suffix)
            dest_path = dest_folder / safe_name

            # Handle duplicates
            counter = 1
            while dest_path.exists():
                stem = Path(safe_name).stem
                suffix = Path(safe_name).suffix
                dest_path = dest_folder / f"{stem}_{counter}{suffix}"
                counter += 1

            # Copy file
            try:
                shutil.copy2(rom_path, dest_path)
                result.exported_count += 1
                result.total_size_bytes += dest_path.stat().st_size

                # Track for library
                core_name = core_config.core.value
                if core_name not in library_entries:
                    library_entries[core_name] = []
                    result.cores_used.append(core_name)

                library_entries[core_name].append({
                    "name": name,
                    "filename": safe_name,
                    "path": str(dest_path.relative_to(target)),
                })

            except Exception as e:
                result.error_count += 1
                result.errors.append(f"Failed: {rom_path.name} - {e}")

        # Create library JSON files
        if create_library_json and library_entries:
            self._create_library_files(target, library_entries)

        result.success = result.error_count == 0
        return result

    def _find_core_for_platform(self, platform: str) -> Optional[PocketCoreConfig]:
        """Find core config for platform."""
        platform_lower = platform.lower().replace("-", "_").replace(" ", "_")

        for config in self._cores.values():
            if platform_lower in config.platform_ids:
                return config

        return None

    def _sanitize_filename(self, name: str, extension: str) -> str:
        """Sanitize filename for FAT32."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, "_")

        name = name.strip(" .")

        # Pocket has some filename length limits
        max_len = 200 - len(extension)
        if len(name) > max_len:
            name = name[:max_len]

        return f"{name}{extension}"

    def _create_library_files(
        self,
        target: Path,
        library_entries: Dict[str, List[Dict[str, str]]],
    ) -> None:
        """Create library.json files for cores."""
        for core_name, entries in library_entries.items():
            # Create library folder
            lib_folder = target / "Assets" / core_name.split(".")[-1].lower()
            lib_folder.mkdir(parents=True, exist_ok=True)

            library_file = lib_folder / "library.json"
            library_data = {
                "core": core_name,
                "games": entries,
                "total": len(entries),
            }

            with open(library_file, "w", encoding="utf-8") as f:
                json.dump(library_data, f, indent=2)

    def get_supported_platforms(self) -> List[str]:
        """Get all supported platforms."""
        platforms = set()
        for config in self._cores.values():
            platforms.update(config.platform_ids)
        return sorted(platforms)

    def get_core_for_platform(self, platform: str) -> Optional[str]:
        """Get recommended core for platform."""
        config = self._find_core_for_platform(platform)
        return config.core.value if config else None

    @staticmethod
    def get_available_cores() -> List[PocketCore]:
        """Get available cores."""
        return list(PocketCore)

    def validate_sd_card(self, path: str) -> Dict[str, Any]:
        """Validate SD card for Pocket.

        Args:
            path: SD card path

        Returns:
            Validation result
        """
        target = Path(path)

        result = {
            "valid": True,
            "is_pocket_sd": False,
            "has_cores": False,
            "has_assets": False,
            "free_space_gb": 0.0,
            "warnings": [],
        }

        if not target.exists():
            result["valid"] = False
            result["warnings"].append("Path does not exist")
            return result

        # Check for Pocket structure
        result["has_cores"] = (target / "Cores").exists()
        result["has_assets"] = (target / "Assets").exists()
        result["is_pocket_sd"] = result["has_cores"] or result["has_assets"]

        # Check free space
        try:
            usage = shutil.disk_usage(target)
            result["free_space_gb"] = usage.free / (1024**3)
        except Exception:
            pass

        return result
