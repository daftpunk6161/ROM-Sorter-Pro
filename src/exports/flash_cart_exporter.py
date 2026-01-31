"""Flash Cart Exporter - F87 Implementation.

Exports ROMs in EverDrive/SD2SNES compatible format.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class FlashCartType(Enum):
    """Supported flash cart types."""

    # Nintendo
    EVERDRIVE_N8 = "everdrive_n8"  # NES
    EVERDRIVE_N8_PRO = "everdrive_n8_pro"
    POWERPAK = "powerpak"
    SD2SNES = "sd2snes"  # SNES / Super Famicom
    FXPAK_PRO = "fxpak_pro"
    EVERDRIVE_GB_X7 = "everdrive_gb_x7"  # Game Boy
    EVERDRIVE_GBA_X5 = "everdrive_gba_x5"  # GBA
    EVERDRIVE_64_X7 = "everdrive_64_x7"  # N64

    # Sega
    MEGA_EVERDRIVE_PRO = "mega_everdrive_pro"  # Genesis/Mega Drive
    EVERDRIVE_MD = "everdrive_md"
    MEGA_SD = "mega_sd"
    MASTER_EVERDRIVE_X7 = "master_everdrive_x7"  # Master System

    # Other
    TURBO_EVERDRIVE_PRO = "turbo_everdrive_pro"  # PC Engine/TurboGrafx


@dataclass
class ExportResult:
    """Result of an export operation."""

    success: bool
    exported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    total_size_bytes: int = 0
    errors: List[str] = field(default_factory=list)
    exported_files: List[str] = field(default_factory=list)


@dataclass
class CartConfig:
    """Configuration for a flash cart type."""

    cart_type: FlashCartType
    folder_structure: Dict[str, str]  # platform -> folder name
    supported_extensions: List[str]
    max_filename_length: int = 255
    requires_8_3_names: bool = False
    max_path_depth: int = 8
    special_folders: List[str] = field(default_factory=list)


# Default configurations for flash carts
CART_CONFIGS: Dict[FlashCartType, CartConfig] = {
    FlashCartType.SD2SNES: CartConfig(
        cart_type=FlashCartType.SD2SNES,
        folder_structure={
            "snes": "SNES",
            "sfc": "SNES",
            "super_famicom": "SNES",
        },
        supported_extensions=[".sfc", ".smc", ".bs", ".fig"],
        special_folders=["sd2snes"],
    ),
    FlashCartType.FXPAK_PRO: CartConfig(
        cart_type=FlashCartType.FXPAK_PRO,
        folder_structure={
            "snes": "SNES",
            "sfc": "SNES",
            "super_famicom": "SNES",
        },
        supported_extensions=[".sfc", ".smc", ".bs", ".fig"],
        special_folders=["sd2snes"],
    ),
    FlashCartType.EVERDRIVE_N8: CartConfig(
        cart_type=FlashCartType.EVERDRIVE_N8,
        folder_structure={
            "nes": "NES",
            "famicom": "NES",
        },
        supported_extensions=[".nes", ".fds", ".unf"],
        special_folders=["EDFC"],
    ),
    FlashCartType.EVERDRIVE_N8_PRO: CartConfig(
        cart_type=FlashCartType.EVERDRIVE_N8_PRO,
        folder_structure={
            "nes": "NES",
            "famicom": "NES",
            "fds": "FDS",
        },
        supported_extensions=[".nes", ".fds", ".unf", ".nsf"],
        special_folders=["EDFC"],
    ),
    FlashCartType.EVERDRIVE_GB_X7: CartConfig(
        cart_type=FlashCartType.EVERDRIVE_GB_X7,
        folder_structure={
            "gb": "GB",
            "gbc": "GBC",
            "gameboy": "GB",
            "gameboy_color": "GBC",
        },
        supported_extensions=[".gb", ".gbc"],
        special_folders=["EDGB"],
    ),
    FlashCartType.EVERDRIVE_GBA_X5: CartConfig(
        cart_type=FlashCartType.EVERDRIVE_GBA_X5,
        folder_structure={
            "gba": "GBA",
            "gameboy_advance": "GBA",
        },
        supported_extensions=[".gba", ".gb", ".gbc"],
        special_folders=["GBASYS"],
    ),
    FlashCartType.EVERDRIVE_64_X7: CartConfig(
        cart_type=FlashCartType.EVERDRIVE_64_X7,
        folder_structure={
            "n64": "N64",
            "nintendo_64": "N64",
        },
        supported_extensions=[".z64", ".n64", ".v64"],
        special_folders=["ED64"],
    ),
    FlashCartType.MEGA_EVERDRIVE_PRO: CartConfig(
        cart_type=FlashCartType.MEGA_EVERDRIVE_PRO,
        folder_structure={
            "genesis": "GENESIS",
            "megadrive": "MEGADRIVE",
            "mega_drive": "MEGADRIVE",
            "sms": "SMS",
            "master_system": "SMS",
            "32x": "32X",
            "segacd": "MEGA-CD",
            "mega_cd": "MEGA-CD",
        },
        supported_extensions=[".md", ".bin", ".gen", ".smd", ".sms", ".32x"],
        special_folders=["MEGA"],
    ),
    FlashCartType.MEGA_SD: CartConfig(
        cart_type=FlashCartType.MEGA_SD,
        folder_structure={
            "genesis": "md",
            "megadrive": "md",
            "segacd": "cd",
            "mega_cd": "cd",
            "32x": "32x",
        },
        supported_extensions=[".md", ".bin", ".gen", ".cue", ".chd"],
        special_folders=["MegaSD"],
    ),
    FlashCartType.TURBO_EVERDRIVE_PRO: CartConfig(
        cart_type=FlashCartType.TURBO_EVERDRIVE_PRO,
        folder_structure={
            "pce": "PCE",
            "pc_engine": "PCE",
            "tg16": "TG16",
            "turbografx": "TG16",
        },
        supported_extensions=[".pce", ".sgx", ".cue", ".chd"],
        special_folders=["TBED"],
    ),
}


class FlashCartExporter:
    """Exports ROMs for flash carts.

    Implements F87: Flash-Cart-Export

    Features:
    - EverDrive folder structure
    - SD2SNES/FXPak Pro compatibility
    - Filename sanitization
    - Size validation
    """

    def __init__(
        self,
        cart_type: FlashCartType = FlashCartType.SD2SNES,
        custom_config: Optional[CartConfig] = None,
    ):
        """Initialize exporter.

        Args:
            cart_type: Target flash cart type
            custom_config: Custom configuration override
        """
        self._cart_type = cart_type
        self._config = custom_config or CART_CONFIGS.get(
            cart_type,
            CART_CONFIGS[FlashCartType.SD2SNES],
        )

    def export(
        self,
        roms: List[Dict[str, Any]],
        target_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        organize_by_letter: bool = False,
        create_system_folders: bool = True,
    ) -> ExportResult:
        """Export ROMs to flash cart format.

        Args:
            roms: List of ROM dicts with 'path', 'platform', 'name'
            target_path: Target SD card / folder
            progress_callback: Callback(current, total, filename)
            organize_by_letter: Create A-Z subfolders
            create_system_folders: Create system folders

        Returns:
            ExportResult
        """
        result = ExportResult(success=True)
        target = Path(target_path)
        target.mkdir(parents=True, exist_ok=True)

        # Create special folders
        for special in self._config.special_folders:
            (target / special).mkdir(exist_ok=True)

        total = len(roms)

        for i, rom in enumerate(roms):
            rom_path = Path(rom.get("path", ""))
            platform = rom.get("platform", "unknown").lower()
            name = rom.get("name", rom_path.stem)

            if progress_callback:
                progress_callback(i + 1, total, name)

            # Check extension
            if rom_path.suffix.lower() not in self._config.supported_extensions:
                result.skipped_count += 1
                result.errors.append(f"Unsupported: {rom_path.name}")
                continue

            # Determine target folder
            if create_system_folders:
                folder_name = self._config.folder_structure.get(
                    platform,
                    platform.upper(),
                )
                dest_folder = target / folder_name
            else:
                dest_folder = target

            # Add letter subfolder if requested
            if organize_by_letter and name:
                first_char = name[0].upper()
                if first_char.isalpha():
                    dest_folder = dest_folder / first_char
                else:
                    dest_folder = dest_folder / "#"

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
                result.exported_files.append(str(dest_path))
            except Exception as e:
                result.error_count += 1
                result.errors.append(f"Failed: {rom_path.name} - {e}")

        result.success = result.error_count == 0
        return result

    def _sanitize_filename(self, name: str, extension: str) -> str:
        """Sanitize filename for FAT32 compatibility.

        Args:
            name: Original name
            extension: File extension

        Returns:
            Sanitized filename
        """
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, "_")

        # Remove leading/trailing spaces and dots
        name = name.strip(" .")

        # Handle 8.3 requirement
        if self._config.requires_8_3_names:
            name = name[:8]
            extension = extension[:4]

        # Truncate if needed
        max_len = self._config.max_filename_length - len(extension)
        if len(name) > max_len:
            name = name[:max_len]

        return f"{name}{extension}"

    def validate_target(self, target_path: str) -> Dict[str, Any]:
        """Validate target for export.

        Args:
            target_path: Target path

        Returns:
            Validation result
        """
        target = Path(target_path)

        result = {
            "valid": True,
            "exists": target.exists(),
            "is_directory": target.is_dir() if target.exists() else False,
            "free_space_gb": 0.0,
            "is_removable": False,
            "filesystem": "unknown",
            "warnings": [],
        }

        if target.exists():
            try:
                import shutil as sh

                usage = sh.disk_usage(target)
                result["free_space_gb"] = usage.free / (1024**3)

                if result["free_space_gb"] < 1:
                    result["warnings"].append("Less than 1 GB free space")
            except Exception:
                pass

        return result

    def get_supported_platforms(self) -> List[str]:
        """Get supported platforms for this cart.

        Returns:
            Platform list
        """
        return list(self._config.folder_structure.keys())

    def get_supported_extensions(self) -> List[str]:
        """Get supported file extensions.

        Returns:
            Extension list
        """
        return self._config.supported_extensions.copy()

    @staticmethod
    def get_available_carts() -> List[FlashCartType]:
        """Get all available cart types.

        Returns:
            List of cart types
        """
        return list(FlashCartType)

    @staticmethod
    def get_cart_info(cart_type: FlashCartType) -> Dict[str, Any]:
        """Get information about a cart type.

        Args:
            cart_type: Cart type

        Returns:
            Cart information
        """
        config = CART_CONFIGS.get(cart_type)
        if not config:
            return {"error": "Unknown cart type"}

        return {
            "name": cart_type.value,
            "platforms": list(config.folder_structure.keys()),
            "extensions": config.supported_extensions,
            "special_folders": config.special_folders,
            "max_filename_length": config.max_filename_length,
        }
