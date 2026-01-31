"""Steam ROM Manager Integration - F90 Implementation.

Adds ROMs to Steam as non-Steam games.
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import vdf  # python-vdf for Steam config parsing


@dataclass
class SteamShortcut:
    """Steam non-Steam game shortcut."""

    app_name: str
    exe: str
    start_dir: str
    icon: str = ""
    shortcut_path: str = ""
    launch_options: str = ""
    is_hidden: bool = False
    allow_desktop_config: bool = True
    allow_overlay: bool = True
    openvr: bool = False
    devkit: bool = False
    devkit_game_id: str = ""
    devkit_override_app_id: int = 0
    last_play_time: int = 0
    flatpak_app_id: str = ""
    tags: List[str] = field(default_factory=list)

    @property
    def app_id(self) -> int:
        """Generate Steam app ID from exe and app_name."""
        # Steam uses CRC32 of "exe" + "app_name" for shortcut IDs
        unique_name = f"{self.exe}{self.app_name}"
        crc = self._crc32(unique_name.encode("utf-8"))
        # Shortcut app IDs are in a specific range
        return (crc | 0x80000000) & 0xFFFFFFFF

    def _crc32(self, data: bytes) -> int:
        """Calculate CRC32."""
        import binascii
        return binascii.crc32(data) & 0xFFFFFFFF


@dataclass
class ExportResult:
    """Export result."""

    success: bool
    added_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: List[str] = field(default_factory=list)
    shortcuts_file: str = ""


class SteamRomManager:
    """Manages ROM integration with Steam.

    Implements F90: Steam-ROM-Manager

    Features:
    - Add ROMs as non-Steam games
    - Emulator launch configuration
    - Tag/category support
    - Grid image support
    """

    def __init__(self, steam_path: Optional[str] = None):
        """Initialize Steam ROM manager.

        Args:
            steam_path: Path to Steam installation
        """
        self._steam_path = steam_path or self._find_steam_path()
        self._user_id: Optional[str] = None

    def _find_steam_path(self) -> str:
        """Find Steam installation path."""
        if os.name == "nt":
            # Windows
            paths = [
                os.path.expandvars(r"%ProgramFiles(x86)%\Steam"),
                os.path.expandvars(r"%ProgramFiles%\Steam"),
                r"C:\Steam",
            ]
        else:
            # Linux/macOS
            paths = [
                os.path.expanduser("~/.steam/steam"),
                os.path.expanduser("~/.local/share/Steam"),
                "/usr/share/steam",
            ]

        for path in paths:
            if os.path.exists(path):
                return path

        return ""

    def _get_user_data_path(self) -> Optional[Path]:
        """Get Steam userdata path for active user."""
        if not self._steam_path:
            return None

        userdata = Path(self._steam_path) / "userdata"
        if not userdata.exists():
            return None

        # Find user directories
        users = [d for d in userdata.iterdir() if d.is_dir() and d.name.isdigit()]

        if not users:
            return None

        # Use first user or specified user
        if self._user_id:
            for user in users:
                if user.name == self._user_id:
                    return user
        return users[0]

    def _get_shortcuts_path(self) -> Optional[Path]:
        """Get path to shortcuts.vdf."""
        user_path = self._get_user_data_path()
        if not user_path:
            return None

        return user_path / "config" / "shortcuts.vdf"

    def _load_shortcuts(self) -> Dict[str, Any]:
        """Load existing shortcuts."""
        shortcuts_path = self._get_shortcuts_path()
        if not shortcuts_path or not shortcuts_path.exists():
            return {"shortcuts": {}}

        try:
            with open(shortcuts_path, "rb") as f:
                return vdf.binary_load(f)
        except Exception:
            return {"shortcuts": {}}

    def _save_shortcuts(self, shortcuts: Dict[str, Any]) -> bool:
        """Save shortcuts to file."""
        shortcuts_path = self._get_shortcuts_path()
        if not shortcuts_path:
            return False

        shortcuts_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(shortcuts_path, "wb") as f:
                vdf.binary_dump(shortcuts, f)
            return True
        except Exception:
            return False

    def add_roms(
        self,
        roms: List[Dict[str, Any]],
        emulator_path: str,
        emulator_args: str = '"%ROM%"',
        category: str = "ROMs",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> ExportResult:
        """Add ROMs to Steam as non-Steam games.

        Args:
            roms: ROM list with 'path', 'name', 'platform'
            emulator_path: Path to emulator executable
            emulator_args: Emulator arguments (%ROM% replaced with path)
            category: Steam category/tag
            progress_callback: Progress callback

        Returns:
            ExportResult
        """
        result = ExportResult(success=True)

        if not self._steam_path:
            result.success = False
            result.errors.append("Steam installation not found")
            return result

        # Load existing shortcuts
        shortcuts_data = self._load_shortcuts()
        shortcuts = shortcuts_data.get("shortcuts", {})

        # Find next index
        if shortcuts:
            max_idx = max(int(k) for k in shortcuts.keys())
            next_idx = max_idx + 1
        else:
            next_idx = 0

        total = len(roms)

        for i, rom in enumerate(roms):
            rom_path = Path(rom.get("path", ""))
            name = rom.get("name", rom_path.stem)
            platform = rom.get("platform", "")

            if progress_callback:
                progress_callback(i + 1, total, name)

            if not rom_path.exists():
                result.skipped_count += 1
                result.errors.append(f"ROM not found: {rom_path}")
                continue

            # Build launch command
            args = emulator_args.replace("%ROM%", str(rom_path))
            args = args.replace("%ROMNAME%", rom_path.stem)
            args = args.replace("%ROMPATH%", str(rom_path.parent))

            # Create shortcut
            shortcut = SteamShortcut(
                app_name=name,
                exe=f'"{emulator_path}"',
                start_dir=f'"{Path(emulator_path).parent}"',
                launch_options=args,
                tags=[category, platform] if platform else [category],
            )

            # Check for duplicate
            is_duplicate = False
            for key, existing in shortcuts.items():
                if (
                    existing.get("AppName") == shortcut.app_name
                    and existing.get("exe") == shortcut.exe
                ):
                    # Update existing
                    shortcuts[key] = self._shortcut_to_dict(shortcut)
                    result.updated_count += 1
                    is_duplicate = True
                    break

            if not is_duplicate:
                shortcuts[str(next_idx)] = self._shortcut_to_dict(shortcut)
                next_idx += 1
                result.added_count += 1

        # Save shortcuts
        shortcuts_data["shortcuts"] = shortcuts
        if self._save_shortcuts(shortcuts_data):
            result.shortcuts_file = str(self._get_shortcuts_path())
        else:
            result.success = False
            result.errors.append("Failed to save shortcuts")

        return result

    def _shortcut_to_dict(self, shortcut: SteamShortcut) -> Dict[str, Any]:
        """Convert shortcut to VDF dict format."""
        return {
            "appid": shortcut.app_id,
            "AppName": shortcut.app_name,
            "exe": shortcut.exe,
            "StartDir": shortcut.start_dir,
            "icon": shortcut.icon,
            "ShortcutPath": shortcut.shortcut_path,
            "LaunchOptions": shortcut.launch_options,
            "IsHidden": 1 if shortcut.is_hidden else 0,
            "AllowDesktopConfig": 1 if shortcut.allow_desktop_config else 0,
            "AllowOverlay": 1 if shortcut.allow_overlay else 0,
            "OpenVR": 1 if shortcut.openvr else 0,
            "Devkit": 1 if shortcut.devkit else 0,
            "DevkitGameID": shortcut.devkit_game_id,
            "DevkitOverrideAppID": shortcut.devkit_override_app_id,
            "LastPlayTime": shortcut.last_play_time,
            "FlatpakAppID": shortcut.flatpak_app_id,
            "tags": {str(i): tag for i, tag in enumerate(shortcut.tags)},
        }

    def remove_rom(self, app_name: str) -> bool:
        """Remove ROM from Steam.

        Args:
            app_name: Name of the ROM/game

        Returns:
            True if removed
        """
        shortcuts_data = self._load_shortcuts()
        shortcuts = shortcuts_data.get("shortcuts", {})

        for key, shortcut in list(shortcuts.items()):
            if shortcut.get("AppName") == app_name:
                del shortcuts[key]
                shortcuts_data["shortcuts"] = shortcuts
                return self._save_shortcuts(shortcuts_data)

        return False

    def list_rom_shortcuts(self) -> List[SteamShortcut]:
        """List all ROM shortcuts (non-Steam games).

        Returns:
            List of shortcuts
        """
        shortcuts_data = self._load_shortcuts()
        shortcuts = shortcuts_data.get("shortcuts", {})

        result = []
        for data in shortcuts.values():
            shortcut = SteamShortcut(
                app_name=data.get("AppName", ""),
                exe=data.get("exe", ""),
                start_dir=data.get("StartDir", ""),
                icon=data.get("icon", ""),
                launch_options=data.get("LaunchOptions", ""),
                tags=list(data.get("tags", {}).values()),
            )
            result.append(shortcut)

        return result

    def set_grid_image(
        self,
        shortcut: SteamShortcut,
        image_path: str,
        image_type: str = "grid",
    ) -> bool:
        """Set grid/hero/logo image for shortcut.

        Args:
            shortcut: Shortcut to update
            image_path: Path to image
            image_type: 'grid', 'hero', 'logo', 'icon'

        Returns:
            True if set
        """
        user_path = self._get_user_data_path()
        if not user_path or not os.path.exists(image_path):
            return False

        grid_path = user_path / "config" / "grid"
        grid_path.mkdir(parents=True, exist_ok=True)

        # Steam grid image naming convention
        app_id = shortcut.app_id

        if image_type == "grid":
            dest_name = f"{app_id}p.png"  # Portrait grid
        elif image_type == "hero":
            dest_name = f"{app_id}_hero.png"
        elif image_type == "logo":
            dest_name = f"{app_id}_logo.png"
        elif image_type == "icon":
            dest_name = f"{app_id}_icon.png"
        else:
            return False

        try:
            import shutil
            shutil.copy2(image_path, grid_path / dest_name)
            return True
        except Exception:
            return False

    def get_emulator_presets(self) -> Dict[str, Dict[str, str]]:
        """Get common emulator presets.

        Returns:
            Dict of emulator presets
        """
        return {
            "retroarch": {
                "args": '-L "{CORE}" "{ROM}"',
                "description": "RetroArch with libretro core",
            },
            "dolphin": {
                "args": '-e "{ROM}"',
                "description": "Dolphin Emulator (GameCube/Wii)",
            },
            "pcsx2": {
                "args": '"{ROM}"',
                "description": "PCSX2 (PlayStation 2)",
            },
            "rpcs3": {
                "args": '"{ROM}"',
                "description": "RPCS3 (PlayStation 3)",
            },
            "yuzu": {
                "args": '"{ROM}"',
                "description": "Yuzu (Nintendo Switch)",
            },
            "ryujinx": {
                "args": '"{ROM}"',
                "description": "Ryujinx (Nintendo Switch)",
            },
            "cemu": {
                "args": '-g "{ROM}"',
                "description": "Cemu (Wii U)",
            },
            "duckstation": {
                "args": '"{ROM}"',
                "description": "DuckStation (PlayStation 1)",
            },
            "ppsspp": {
                "args": '"{ROM}"',
                "description": "PPSSPP (PSP)",
            },
        }

    def is_steam_running(self) -> bool:
        """Check if Steam is running.

        Returns:
            True if Steam is running
        """
        import subprocess

        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq steam.exe"],
                    capture_output=True,
                    text=True,
                )
                return "steam.exe" in result.stdout.lower()
            else:
                result = subprocess.run(
                    ["pgrep", "-x", "steam"],
                    capture_output=True,
                )
                return result.returncode == 0
        except Exception:
            return False

    def validate_steam_installation(self) -> Dict[str, Any]:
        """Validate Steam installation.

        Returns:
            Validation result
        """
        result = {
            "valid": False,
            "steam_path": self._steam_path,
            "userdata_found": False,
            "users": [],
            "shortcuts_path": None,
            "errors": [],
        }

        if not self._steam_path or not os.path.exists(self._steam_path):
            result["errors"].append("Steam installation not found")
            return result

        userdata = Path(self._steam_path) / "userdata"
        if userdata.exists():
            result["userdata_found"] = True
            result["users"] = [
                d.name for d in userdata.iterdir()
                if d.is_dir() and d.name.isdigit()
            ]

        shortcuts_path = self._get_shortcuts_path()
        if shortcuts_path:
            result["shortcuts_path"] = str(shortcuts_path)

        result["valid"] = result["userdata_found"] and len(result["users"]) > 0

        return result


# Fallback VDF implementation if python-vdf not installed
try:
    import vdf
except ImportError:
    # Simple VDF parser fallback
    class vdf:
        @staticmethod
        def binary_load(f):
            """Load binary VDF (simplified)."""
            return {"shortcuts": {}}

        @staticmethod
        def binary_dump(data, f):
            """Dump binary VDF (simplified)."""
            # Simplified binary VDF writer
            f.write(b"\x00shortcuts\x00")
            shortcuts = data.get("shortcuts", {})
            for idx, shortcut in shortcuts.items():
                f.write(b"\x00" + str(idx).encode() + b"\x00")
                for key, value in shortcut.items():
                    if isinstance(value, str):
                        f.write(b"\x01" + key.encode() + b"\x00" + value.encode() + b"\x00")
                    elif isinstance(value, int):
                        f.write(b"\x02" + key.encode() + b"\x00" + struct.pack("<I", value))
                    elif isinstance(value, dict):
                        f.write(b"\x00" + key.encode() + b"\x00")
                        for k, v in value.items():
                            f.write(b"\x01" + k.encode() + b"\x00" + str(v).encode() + b"\x00")
                        f.write(b"\x08")
                f.write(b"\x08")
            f.write(b"\x08\x08")
