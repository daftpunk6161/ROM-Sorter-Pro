"""Per-Game Settings - F86 Implementation.

Manages emulator settings on a per-ROM basis.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class SettingsScope(Enum):
    """Settings scope levels."""

    GLOBAL = "global"  # Applies to all games
    PLATFORM = "platform"  # Applies to platform
    CORE = "core"  # Applies to specific core
    DIRECTORY = "directory"  # Applies to directory
    ROM = "rom"  # Applies to specific ROM


@dataclass
class GameConfig:
    """Configuration for a specific game."""

    rom_path: str
    rom_name: str
    scope: SettingsScope = SettingsScope.ROM

    # Emulator settings
    preferred_core: str = ""
    fullscreen: bool = True
    vsync: bool = True
    aspect_ratio: str = "auto"
    integer_scaling: bool = False
    shader: str = ""

    # Video settings
    resolution_scale: int = 1
    bilinear_filter: bool = False
    scanlines: bool = False

    # Audio settings
    audio_latency: int = 64
    audio_sync: bool = True

    # Input settings
    controller_profile: str = ""
    turbo_enabled: bool = False

    # Overrides from RetroArch
    retroarch_overrides: Dict[str, Any] = field(default_factory=dict)

    # Custom options per core
    core_options: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Launch arguments
    extra_arguments: List[str] = field(default_factory=list)

    # Notes
    notes: str = ""
    tags: List[str] = field(default_factory=list)


class GameSettings:
    """Manages per-game emulator settings.

    Implements F86: Per-Game-Settings

    Features:
    - Per-ROM configuration
    - Hierarchical settings (global -> platform -> core -> game)
    - RetroArch override compatibility
    - Core-specific options
    """

    def __init__(self, settings_path: str):
        """Initialize game settings.

        Args:
            settings_path: Path to settings storage
        """
        self._settings_path = Path(settings_path)
        self._settings_path.mkdir(parents=True, exist_ok=True)

        self._global_settings: Dict[str, Any] = {}
        self._platform_settings: Dict[str, Dict[str, Any]] = {}
        self._core_settings: Dict[str, Dict[str, Any]] = {}
        self._game_settings: Dict[str, GameConfig] = {}

        self._load_settings()

    def _load_settings(self) -> None:
        """Load all settings from disk."""
        # Load global
        global_path = self._settings_path / "global.json"
        if global_path.exists():
            try:
                with open(global_path, "r", encoding="utf-8") as f:
                    self._global_settings = json.load(f)
            except Exception:
                pass

        # Load platform settings
        platforms_path = self._settings_path / "platforms"
        if platforms_path.exists():
            for file in platforms_path.glob("*.json"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        self._platform_settings[file.stem] = json.load(f)
                except Exception:
                    pass

        # Load core settings
        cores_path = self._settings_path / "cores"
        if cores_path.exists():
            for file in cores_path.glob("*.json"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        self._core_settings[file.stem] = json.load(f)
                except Exception:
                    pass

        # Load game settings
        games_path = self._settings_path / "games"
        if games_path.exists():
            for file in games_path.glob("*.json"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self._game_settings[file.stem] = self._dict_to_config(data)
                except Exception:
                    pass

    def _save_settings(self) -> None:
        """Save all settings to disk."""
        # Save global
        global_path = self._settings_path / "global.json"
        with open(global_path, "w", encoding="utf-8") as f:
            json.dump(self._global_settings, f, indent=2)

        # Save platform settings
        platforms_path = self._settings_path / "platforms"
        platforms_path.mkdir(exist_ok=True)
        for name, settings in self._platform_settings.items():
            with open(platforms_path / f"{name}.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)

        # Save core settings
        cores_path = self._settings_path / "cores"
        cores_path.mkdir(exist_ok=True)
        for name, settings in self._core_settings.items():
            with open(cores_path / f"{name}.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)

        # Save game settings
        games_path = self._settings_path / "games"
        games_path.mkdir(exist_ok=True)
        for key, config in self._game_settings.items():
            with open(games_path / f"{key}.json", "w", encoding="utf-8") as f:
                json.dump(self._config_to_dict(config), f, indent=2)

    def _dict_to_config(self, data: Dict[str, Any]) -> GameConfig:
        """Convert dict to GameConfig."""
        return GameConfig(
            rom_path=data.get("rom_path", ""),
            rom_name=data.get("rom_name", ""),
            scope=SettingsScope(data.get("scope", "rom")),
            preferred_core=data.get("preferred_core", ""),
            fullscreen=data.get("fullscreen", True),
            vsync=data.get("vsync", True),
            aspect_ratio=data.get("aspect_ratio", "auto"),
            integer_scaling=data.get("integer_scaling", False),
            shader=data.get("shader", ""),
            resolution_scale=data.get("resolution_scale", 1),
            bilinear_filter=data.get("bilinear_filter", False),
            scanlines=data.get("scanlines", False),
            audio_latency=data.get("audio_latency", 64),
            audio_sync=data.get("audio_sync", True),
            controller_profile=data.get("controller_profile", ""),
            turbo_enabled=data.get("turbo_enabled", False),
            retroarch_overrides=data.get("retroarch_overrides", {}),
            core_options=data.get("core_options", {}),
            extra_arguments=data.get("extra_arguments", []),
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
        )

    def _config_to_dict(self, config: GameConfig) -> Dict[str, Any]:
        """Convert GameConfig to dict."""
        return {
            "rom_path": config.rom_path,
            "rom_name": config.rom_name,
            "scope": config.scope.value,
            "preferred_core": config.preferred_core,
            "fullscreen": config.fullscreen,
            "vsync": config.vsync,
            "aspect_ratio": config.aspect_ratio,
            "integer_scaling": config.integer_scaling,
            "shader": config.shader,
            "resolution_scale": config.resolution_scale,
            "bilinear_filter": config.bilinear_filter,
            "scanlines": config.scanlines,
            "audio_latency": config.audio_latency,
            "audio_sync": config.audio_sync,
            "controller_profile": config.controller_profile,
            "turbo_enabled": config.turbo_enabled,
            "retroarch_overrides": config.retroarch_overrides,
            "core_options": config.core_options,
            "extra_arguments": config.extra_arguments,
            "notes": config.notes,
            "tags": config.tags,
        }

    def _get_rom_key(self, rom_path: str) -> str:
        """Get storage key for ROM."""
        # Use hash of path for unique key
        path = Path(rom_path)
        return f"{path.stem}_{hash(str(path)) & 0xFFFFFFFF:08x}"

    def get_config(
        self,
        rom_path: str,
        platform: Optional[str] = None,
        core: Optional[str] = None,
    ) -> GameConfig:
        """Get effective configuration for a ROM.

        Merges settings in order: global -> platform -> core -> game

        Args:
            rom_path: Path to ROM
            platform: Platform identifier
            core: Core name

        Returns:
            Merged GameConfig
        """
        # Start with defaults
        config = GameConfig(
            rom_path=rom_path,
            rom_name=Path(rom_path).stem,
        )

        # Apply global settings
        self._apply_settings(config, self._global_settings)

        # Apply platform settings
        if platform and platform in self._platform_settings:
            self._apply_settings(config, self._platform_settings[platform])

        # Apply core settings
        if core and core in self._core_settings:
            self._apply_settings(config, self._core_settings[core])

        # Apply game-specific settings
        key = self._get_rom_key(rom_path)
        if key in self._game_settings:
            game_config = self._game_settings[key]
            # Copy all non-default values
            self._apply_config(config, game_config)

        return config

    def _apply_settings(self, config: GameConfig, settings: Dict[str, Any]) -> None:
        """Apply settings dict to config."""
        for key, value in settings.items():
            if hasattr(config, key) and value is not None:
                if key == "scope":
                    setattr(config, key, SettingsScope(value))
                else:
                    setattr(config, key, value)

    def _apply_config(self, target: GameConfig, source: GameConfig) -> None:
        """Apply source config to target."""
        # Only apply non-default values
        default = GameConfig(rom_path="", rom_name="")

        for attr in [
            "preferred_core",
            "fullscreen",
            "vsync",
            "aspect_ratio",
            "integer_scaling",
            "shader",
            "resolution_scale",
            "bilinear_filter",
            "scanlines",
            "audio_latency",
            "audio_sync",
            "controller_profile",
            "turbo_enabled",
            "notes",
        ]:
            source_val = getattr(source, attr)
            default_val = getattr(default, attr)
            if source_val != default_val:
                setattr(target, attr, source_val)

        # Merge dicts
        if source.retroarch_overrides:
            target.retroarch_overrides.update(source.retroarch_overrides)
        if source.core_options:
            target.core_options.update(source.core_options)
        if source.extra_arguments:
            target.extra_arguments.extend(source.extra_arguments)
        if source.tags:
            target.tags = list(set(target.tags + source.tags))

    def set_config(
        self,
        rom_path: str,
        config: GameConfig,
        save: bool = True,
    ) -> None:
        """Set configuration for a ROM.

        Args:
            rom_path: Path to ROM
            config: Configuration to set
            save: Save to disk
        """
        key = self._get_rom_key(rom_path)
        config.rom_path = rom_path
        config.rom_name = Path(rom_path).stem
        self._game_settings[key] = config

        if save:
            self._save_settings()

    def update_config(
        self,
        rom_path: str,
        updates: Dict[str, Any],
        save: bool = True,
    ) -> GameConfig:
        """Update specific settings for a ROM.

        Args:
            rom_path: Path to ROM
            updates: Settings to update
            save: Save to disk

        Returns:
            Updated config
        """
        key = self._get_rom_key(rom_path)

        if key in self._game_settings:
            config = self._game_settings[key]
        else:
            config = GameConfig(
                rom_path=rom_path,
                rom_name=Path(rom_path).stem,
            )

        for attr, value in updates.items():
            if hasattr(config, attr):
                if attr == "scope":
                    setattr(config, attr, SettingsScope(value))
                else:
                    setattr(config, attr, value)

        self._game_settings[key] = config

        if save:
            self._save_settings()

        return config

    def delete_config(self, rom_path: str, save: bool = True) -> bool:
        """Delete configuration for a ROM.

        Args:
            rom_path: Path to ROM
            save: Save to disk

        Returns:
            True if deleted
        """
        key = self._get_rom_key(rom_path)
        if key in self._game_settings:
            del self._game_settings[key]
            if save:
                # Remove file
                games_path = self._settings_path / "games" / f"{key}.json"
                if games_path.exists():
                    games_path.unlink()
            return True
        return False

    def set_global_setting(
        self,
        key: str,
        value: Any,
        save: bool = True,
    ) -> None:
        """Set a global setting.

        Args:
            key: Setting key
            value: Setting value
            save: Save to disk
        """
        self._global_settings[key] = value
        if save:
            self._save_settings()

    def set_platform_setting(
        self,
        platform: str,
        key: str,
        value: Any,
        save: bool = True,
    ) -> None:
        """Set a platform-wide setting.

        Args:
            platform: Platform identifier
            key: Setting key
            value: Setting value
            save: Save to disk
        """
        if platform not in self._platform_settings:
            self._platform_settings[platform] = {}

        self._platform_settings[platform][key] = value
        if save:
            self._save_settings()

    def set_core_setting(
        self,
        core: str,
        key: str,
        value: Any,
        save: bool = True,
    ) -> None:
        """Set a core-wide setting.

        Args:
            core: Core name
            key: Setting key
            value: Setting value
            save: Save to disk
        """
        if core not in self._core_settings:
            self._core_settings[core] = {}

        self._core_settings[core][key] = value
        if save:
            self._save_settings()

    def export_retroarch_overrides(
        self,
        rom_path: str,
        output_path: str,
    ) -> bool:
        """Export settings as RetroArch override file.

        Args:
            rom_path: ROM path
            output_path: Override file path

        Returns:
            True if exported
        """
        config = self.get_config(rom_path)

        override_content = [
            "# RetroArch Game Override",
            f"# Generated for: {config.rom_name}",
            "",
        ]

        if config.preferred_core:
            override_content.append(f'core = "{config.preferred_core}"')

        if config.aspect_ratio != "auto":
            override_content.append(f'aspect_ratio_index = "{config.aspect_ratio}"')

        if config.shader:
            override_content.append(f'video_shader = "{config.shader}"')

        # Add core options
        for core_name, options in config.core_options.items():
            for opt_key, opt_val in options.items():
                override_content.append(f'{opt_key} = "{opt_val}"')

        # Add custom overrides
        for key, value in config.retroarch_overrides.items():
            if isinstance(value, bool):
                override_content.append(f'{key} = "{str(value).lower()}"')
            elif isinstance(value, (int, float)):
                override_content.append(f'{key} = "{value}"')
            else:
                override_content.append(f'{key} = "{value}"')

        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(override_content))
            return True
        except Exception:
            return False

    def import_retroarch_overrides(
        self,
        rom_path: str,
        override_path: str,
    ) -> bool:
        """Import RetroArch override file.

        Args:
            rom_path: ROM path
            override_path: Override file path

        Returns:
            True if imported
        """
        if not Path(override_path).exists():
            return False

        try:
            overrides: Dict[str, Any] = {}

            with open(override_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"')

                        # Convert types
                        if value.lower() in ("true", "false"):
                            value = value.lower() == "true"
                        elif value.isdigit():
                            value = int(value)
                        elif value.replace(".", "").isdigit():
                            value = float(value)

                        overrides[key] = value

            self.update_config(rom_path, {"retroarch_overrides": overrides})
            return True
        except Exception:
            return False

    def list_games_with_config(self) -> List[GameConfig]:
        """Get all games with custom configuration.

        Returns:
            List of game configs
        """
        return list(self._game_settings.values())

    def search_by_tag(self, tag: str) -> List[GameConfig]:
        """Find games with specific tag.

        Args:
            tag: Tag to search

        Returns:
            Matching configs
        """
        tag_lower = tag.lower()
        return [
            config
            for config in self._game_settings.values()
            if any(t.lower() == tag_lower for t in config.tags)
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get settings statistics.

        Returns:
            Statistics dict
        """
        all_tags: List[str] = []
        cores_used: List[str] = []
        shaders_used: List[str] = []

        for config in self._game_settings.values():
            all_tags.extend(config.tags)
            if config.preferred_core:
                cores_used.append(config.preferred_core)
            if config.shader:
                shaders_used.append(config.shader)

        return {
            "total_games": len(self._game_settings),
            "platforms_configured": len(self._platform_settings),
            "cores_configured": len(self._core_settings),
            "unique_tags": len(set(all_tags)),
            "most_used_cores": sorted(
                set(cores_used), key=cores_used.count, reverse=True
            )[:5],
            "most_used_shaders": sorted(
                set(shaders_used), key=shaders_used.count, reverse=True
            )[:5],
        }
