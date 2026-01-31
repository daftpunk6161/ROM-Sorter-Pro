"""Core Mapping - F84 Implementation.

Manages RetroArch core assignments for different platforms and ROM types.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class CorePriority(Enum):
    """Core priority levels."""

    PREFERRED = 1
    ALTERNATIVE = 2
    FALLBACK = 3
    LEGACY = 4


@dataclass
class CoreConfig:
    """Configuration for a libretro core."""

    core_name: str
    core_path: str
    display_name: str
    supported_extensions: List[str] = field(default_factory=list)
    priority: CorePriority = CorePriority.PREFERRED
    requires_bios: bool = False
    bios_files: List[str] = field(default_factory=list)
    default_options: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass
class CoreMatch:
    """A matched core for a ROM."""

    core_config: CoreConfig
    match_score: float
    match_reason: str


# Default core recommendations per platform
DEFAULT_CORE_MAPPING: Dict[str, List[Dict[str, Any]]] = {
    "nes": [
        {
            "core_name": "mesen",
            "display_name": "Mesen",
            "extensions": [".nes", ".fds", ".unf"],
            "priority": CorePriority.PREFERRED,
        },
        {
            "core_name": "nestopia",
            "display_name": "Nestopia UE",
            "extensions": [".nes", ".fds", ".unf"],
            "priority": CorePriority.ALTERNATIVE,
        },
        {
            "core_name": "fceumm",
            "display_name": "FCEUmm",
            "extensions": [".nes", ".fds", ".unf"],
            "priority": CorePriority.FALLBACK,
        },
    ],
    "snes": [
        {
            "core_name": "bsnes",
            "display_name": "bsnes",
            "extensions": [".sfc", ".smc", ".bs"],
            "priority": CorePriority.PREFERRED,
        },
        {
            "core_name": "snes9x",
            "display_name": "Snes9x",
            "extensions": [".sfc", ".smc", ".bs"],
            "priority": CorePriority.ALTERNATIVE,
        },
        {
            "core_name": "mesen-s",
            "display_name": "Mesen-S",
            "extensions": [".sfc", ".smc", ".bs", ".gb", ".gbc"],
            "priority": CorePriority.ALTERNATIVE,
        },
    ],
    "n64": [
        {
            "core_name": "mupen64plus_next",
            "display_name": "Mupen64Plus-Next",
            "extensions": [".n64", ".z64", ".v64"],
            "priority": CorePriority.PREFERRED,
        },
        {
            "core_name": "parallel_n64",
            "display_name": "ParaLLEl N64",
            "extensions": [".n64", ".z64", ".v64"],
            "priority": CorePriority.ALTERNATIVE,
        },
    ],
    "gb": [
        {
            "core_name": "gambatte",
            "display_name": "Gambatte",
            "extensions": [".gb", ".gbc"],
            "priority": CorePriority.PREFERRED,
        },
        {
            "core_name": "sameboy",
            "display_name": "SameBoy",
            "extensions": [".gb", ".gbc"],
            "priority": CorePriority.ALTERNATIVE,
        },
        {
            "core_name": "mgba",
            "display_name": "mGBA",
            "extensions": [".gb", ".gbc", ".gba"],
            "priority": CorePriority.FALLBACK,
        },
    ],
    "gba": [
        {
            "core_name": "mgba",
            "display_name": "mGBA",
            "extensions": [".gba", ".gb", ".gbc"],
            "priority": CorePriority.PREFERRED,
        },
        {
            "core_name": "vba_next",
            "display_name": "VBA Next",
            "extensions": [".gba", ".gb", ".gbc"],
            "priority": CorePriority.FALLBACK,
        },
    ],
    "genesis": [
        {
            "core_name": "genesis_plus_gx",
            "display_name": "Genesis Plus GX",
            "extensions": [".md", ".gen", ".smd", ".32x", ".sms", ".gg"],
            "priority": CorePriority.PREFERRED,
        },
        {
            "core_name": "picodrive",
            "display_name": "PicoDrive",
            "extensions": [".md", ".gen", ".smd", ".32x", ".sms"],
            "priority": CorePriority.ALTERNATIVE,
        },
    ],
    "psx": [
        {
            "core_name": "duckstation",
            "display_name": "DuckStation",
            "extensions": [".cue", ".bin", ".chd", ".pbp", ".iso"],
            "priority": CorePriority.PREFERRED,
            "requires_bios": True,
            "bios_files": ["scph5501.bin", "scph5500.bin", "scph5502.bin"],
        },
        {
            "core_name": "beetle_psx",
            "display_name": "Beetle PSX",
            "extensions": [".cue", ".bin", ".chd", ".pbp", ".iso"],
            "priority": CorePriority.ALTERNATIVE,
            "requires_bios": True,
        },
        {
            "core_name": "pcsx_rearmed",
            "display_name": "PCSX ReARMed",
            "extensions": [".cue", ".bin", ".chd", ".pbp", ".iso"],
            "priority": CorePriority.FALLBACK,
        },
    ],
    "arcade": [
        {
            "core_name": "fbneo",
            "display_name": "FinalBurn Neo",
            "extensions": [".zip", ".7z"],
            "priority": CorePriority.PREFERRED,
        },
        {
            "core_name": "mame",
            "display_name": "MAME",
            "extensions": [".zip", ".7z", ".chd"],
            "priority": CorePriority.ALTERNATIVE,
        },
    ],
    "psp": [
        {
            "core_name": "ppsspp",
            "display_name": "PPSSPP",
            "extensions": [".iso", ".cso", ".pbp"],
            "priority": CorePriority.PREFERRED,
        },
    ],
    "nds": [
        {
            "core_name": "melonds",
            "display_name": "melonDS",
            "extensions": [".nds", ".dsi"],
            "priority": CorePriority.PREFERRED,
            "requires_bios": True,
            "bios_files": ["bios7.bin", "bios9.bin", "firmware.bin"],
        },
        {
            "core_name": "desmume",
            "display_name": "DeSmuME",
            "extensions": [".nds"],
            "priority": CorePriority.ALTERNATIVE,
        },
    ],
}


class CoreMapping:
    """Manages core assignments for platforms.

    Implements F84: Core-Zuordnung

    Features:
    - Default core recommendations per platform
    - User-configurable core assignments
    - Automatic core detection
    - BIOS requirements tracking
    """

    def __init__(
        self,
        cores_directory: Optional[str] = None,
        config_path: Optional[str] = None,
    ):
        """Initialize core mapping.

        Args:
            cores_directory: Path to RetroArch cores
            config_path: Path to custom config file
        """
        self._cores_dir = cores_directory
        self._config_path = config_path
        self._custom_mappings: Dict[str, List[CoreConfig]] = {}
        self._discovered_cores: Dict[str, str] = {}

        if config_path and Path(config_path).exists():
            self._load_config()

        if cores_directory:
            self._discover_cores()

    def _discover_cores(self) -> None:
        """Discover available cores in directory."""
        if not self._cores_dir or not Path(self._cores_dir).exists():
            return

        cores_path = Path(self._cores_dir)

        # Common core extensions
        extensions = [".dll", ".so", ".dylib"]

        for ext in extensions:
            for core_file in cores_path.glob(f"*_libretro{ext}"):
                core_name = core_file.stem.replace("_libretro", "")
                self._discovered_cores[core_name] = str(core_file)

    def _load_config(self) -> None:
        """Load custom configuration."""
        if not self._config_path:
            return

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for platform, cores in data.get("mappings", {}).items():
                self._custom_mappings[platform] = []
                for core_data in cores:
                    self._custom_mappings[platform].append(
                        CoreConfig(
                            core_name=core_data.get("core_name", ""),
                            core_path=core_data.get("core_path", ""),
                            display_name=core_data.get("display_name", ""),
                            supported_extensions=core_data.get("extensions", []),
                            priority=CorePriority(
                                core_data.get("priority", CorePriority.PREFERRED.value)
                            ),
                            requires_bios=core_data.get("requires_bios", False),
                            bios_files=core_data.get("bios_files", []),
                            default_options=core_data.get("options", {}),
                        )
                    )
        except Exception:
            pass

    def save_config(self) -> bool:
        """Save configuration to file.

        Returns:
            True if saved
        """
        if not self._config_path:
            return False

        try:
            data = {"mappings": {}}

            for platform, cores in self._custom_mappings.items():
                data["mappings"][platform] = []
                for core in cores:
                    data["mappings"][platform].append(
                        {
                            "core_name": core.core_name,
                            "core_path": core.core_path,
                            "display_name": core.display_name,
                            "extensions": core.supported_extensions,
                            "priority": core.priority.value,
                            "requires_bios": core.requires_bios,
                            "bios_files": core.bios_files,
                            "options": core.default_options,
                        }
                    )

            Path(self._config_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            return True
        except Exception:
            return False

    def get_cores_for_platform(
        self,
        platform: str,
        only_available: bool = False,
    ) -> List[CoreConfig]:
        """Get recommended cores for platform.

        Args:
            platform: Platform identifier
            only_available: Only return discovered cores

        Returns:
            List of core configurations
        """
        platform_lower = platform.lower()

        # Check custom mappings first
        if platform_lower in self._custom_mappings:
            cores = self._custom_mappings[platform_lower]
        elif platform_lower in DEFAULT_CORE_MAPPING:
            # Build CoreConfig from defaults
            cores = []
            for default in DEFAULT_CORE_MAPPING[platform_lower]:
                core_path = self._discovered_cores.get(default["core_name"], "")
                cores.append(
                    CoreConfig(
                        core_name=default["core_name"],
                        core_path=core_path,
                        display_name=default["display_name"],
                        supported_extensions=default.get("extensions", []),
                        priority=default.get("priority", CorePriority.PREFERRED),
                        requires_bios=default.get("requires_bios", False),
                        bios_files=default.get("bios_files", []),
                    )
                )
        else:
            return []

        if only_available:
            cores = [c for c in cores if c.core_path and Path(c.core_path).exists()]

        # Sort by priority
        return sorted(cores, key=lambda c: c.priority.value)

    def get_core_for_rom(
        self,
        rom_path: str,
        platform: Optional[str] = None,
    ) -> Optional[CoreMatch]:
        """Get best core for a ROM.

        Args:
            rom_path: Path to ROM file
            platform: Platform hint (optional)

        Returns:
            CoreMatch or None
        """
        extension = Path(rom_path).suffix.lower()

        # If platform specified, use it
        if platform:
            cores = self.get_cores_for_platform(platform, only_available=True)
            for core in cores:
                if extension in core.supported_extensions or not core.supported_extensions:
                    return CoreMatch(
                        core_config=core,
                        match_score=1.0 - (core.priority.value - 1) * 0.1,
                        match_reason=f"Platform match: {platform}",
                    )

        # Try to match by extension
        best_match: Optional[CoreMatch] = None
        best_score = 0.0

        for platform_key in DEFAULT_CORE_MAPPING:
            cores = self.get_cores_for_platform(platform_key, only_available=True)
            for core in cores:
                if extension in core.supported_extensions:
                    score = 1.0 - (core.priority.value - 1) * 0.1
                    if score > best_score:
                        best_score = score
                        best_match = CoreMatch(
                            core_config=core,
                            match_score=score,
                            match_reason=f"Extension match: {extension}",
                        )

        return best_match

    def set_core_for_platform(
        self,
        platform: str,
        core_config: CoreConfig,
        priority: Optional[CorePriority] = None,
    ) -> None:
        """Set custom core for platform.

        Args:
            platform: Platform identifier
            core_config: Core configuration
            priority: Override priority
        """
        platform_lower = platform.lower()

        if platform_lower not in self._custom_mappings:
            self._custom_mappings[platform_lower] = []

        if priority:
            core_config.priority = priority

        # Check if core already exists
        existing_idx = None
        for i, c in enumerate(self._custom_mappings[platform_lower]):
            if c.core_name == core_config.core_name:
                existing_idx = i
                break

        if existing_idx is not None:
            self._custom_mappings[platform_lower][existing_idx] = core_config
        else:
            self._custom_mappings[platform_lower].append(core_config)

        # Re-sort by priority
        self._custom_mappings[platform_lower].sort(key=lambda c: c.priority.value)

    def remove_core_from_platform(
        self,
        platform: str,
        core_name: str,
    ) -> bool:
        """Remove core from platform mapping.

        Args:
            platform: Platform identifier
            core_name: Core name to remove

        Returns:
            True if removed
        """
        platform_lower = platform.lower()

        if platform_lower not in self._custom_mappings:
            return False

        original_len = len(self._custom_mappings[platform_lower])
        self._custom_mappings[platform_lower] = [
            c
            for c in self._custom_mappings[platform_lower]
            if c.core_name != core_name
        ]

        return len(self._custom_mappings[platform_lower]) < original_len

    def get_discovered_cores(self) -> Dict[str, str]:
        """Get all discovered cores.

        Returns:
            Dict of core_name -> core_path
        """
        return dict(self._discovered_cores)

    def get_supported_platforms(self) -> List[str]:
        """Get list of supported platforms.

        Returns:
            Platform identifiers
        """
        platforms = set(DEFAULT_CORE_MAPPING.keys())
        platforms.update(self._custom_mappings.keys())
        return sorted(platforms)

    def check_bios_requirements(
        self,
        core_config: CoreConfig,
        bios_directory: str,
    ) -> Dict[str, bool]:
        """Check if required BIOS files exist.

        Args:
            core_config: Core configuration
            bios_directory: Path to BIOS directory

        Returns:
            Dict of bios_file -> exists
        """
        result = {}
        bios_path = Path(bios_directory)

        for bios_file in core_config.bios_files:
            result[bios_file] = (bios_path / bios_file).exists()

        return result
