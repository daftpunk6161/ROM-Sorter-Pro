"""Batocera/RetroPie Exporter - F89 Implementation.

Exports ROMs in EmulationStation/Batocera/RetroPie format.
"""

from __future__ import annotations

import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from xml.dom import minidom


@dataclass
class ESSystem:
    """EmulationStation system configuration."""

    name: str
    fullname: str
    path: str
    extension: str
    command: str
    platform: str
    theme: str


# Default EmulationStation systems
ES_SYSTEMS: Dict[str, ESSystem] = {
    "nes": ESSystem(
        name="nes",
        fullname="Nintendo Entertainment System",
        path="/roms/nes",
        extension=".nes .NES .zip .ZIP .7z .7Z",
        command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ nes %ROM%",
        platform="nes",
        theme="nes",
    ),
    "snes": ESSystem(
        name="snes",
        fullname="Super Nintendo Entertainment System",
        path="/roms/snes",
        extension=".smc .SMC .sfc .SFC .zip .ZIP .7z .7Z",
        command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ snes %ROM%",
        platform="snes",
        theme="snes",
    ),
    "n64": ESSystem(
        name="n64",
        fullname="Nintendo 64",
        path="/roms/n64",
        extension=".z64 .Z64 .n64 .N64 .v64 .V64 .zip .ZIP",
        command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ n64 %ROM%",
        platform="n64",
        theme="n64",
    ),
    "gb": ESSystem(
        name="gb",
        fullname="Game Boy",
        path="/roms/gb",
        extension=".gb .GB .zip .ZIP .7z .7Z",
        command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ gb %ROM%",
        platform="gb",
        theme="gb",
    ),
    "gbc": ESSystem(
        name="gbc",
        fullname="Game Boy Color",
        path="/roms/gbc",
        extension=".gbc .GBC .zip .ZIP .7z .7Z",
        command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ gbc %ROM%",
        platform="gbc",
        theme="gbc",
    ),
    "gba": ESSystem(
        name="gba",
        fullname="Game Boy Advance",
        path="/roms/gba",
        extension=".gba .GBA .zip .ZIP .7z .7Z",
        command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ gba %ROM%",
        platform="gba",
        theme="gba",
    ),
    "genesis": ESSystem(
        name="genesis",
        fullname="Sega Genesis",
        path="/roms/genesis",
        extension=".md .MD .bin .BIN .gen .GEN .smd .SMD .zip .ZIP",
        command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ genesis %ROM%",
        platform="genesis",
        theme="genesis",
    ),
    "megadrive": ESSystem(
        name="megadrive",
        fullname="Sega Mega Drive",
        path="/roms/megadrive",
        extension=".md .MD .bin .BIN .gen .GEN .smd .SMD .zip .ZIP",
        command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ megadrive %ROM%",
        platform="megadrive",
        theme="megadrive",
    ),
    "psx": ESSystem(
        name="psx",
        fullname="Sony PlayStation",
        path="/roms/psx",
        extension=".cue .CUE .bin .BIN .iso .ISO .pbp .PBP .chd .CHD",
        command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ psx %ROM%",
        platform="psx",
        theme="psx",
    ),
    "psp": ESSystem(
        name="psp",
        fullname="Sony PSP",
        path="/roms/psp",
        extension=".iso .ISO .cso .CSO .pbp .PBP",
        command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ psp %ROM%",
        platform="psp",
        theme="psp",
    ),
    "arcade": ESSystem(
        name="arcade",
        fullname="Arcade",
        path="/roms/arcade",
        extension=".zip .ZIP .7z .7Z",
        command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ arcade %ROM%",
        platform="arcade",
        theme="arcade",
    ),
    "mame": ESSystem(
        name="mame",
        fullname="MAME",
        path="/roms/mame",
        extension=".zip .ZIP .7z .7Z",
        command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ mame %ROM%",
        platform="mame",
        theme="mame",
    ),
    "nds": ESSystem(
        name="nds",
        fullname="Nintendo DS",
        path="/roms/nds",
        extension=".nds .NDS .zip .ZIP",
        command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ nds %ROM%",
        platform="nds",
        theme="nds",
    ),
    "pce": ESSystem(
        name="pcengine",
        fullname="PC Engine / TurboGrafx-16",
        path="/roms/pcengine",
        extension=".pce .PCE .cue .CUE .zip .ZIP",
        command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ pcengine %ROM%",
        platform="pcengine",
        theme="pcengine",
    ),
}


@dataclass
class ExportResult:
    """Export result."""

    success: bool
    exported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    total_size_bytes: int = 0
    systems_created: List[str] = field(default_factory=list)
    gamelist_created: bool = False
    errors: List[str] = field(default_factory=list)


class BatoceraExporter:
    """Exports ROMs for Batocera.

    Implements F89: Batocera/RetroPie-Export

    Features:
    - Batocera folder structure (/roms/system/)
    - gamelist.xml generation
    - System detection
    """

    # Batocera-specific paths
    ROMS_BASE = "roms"
    BIOS_BASE = "bios"

    def __init__(self, custom_systems: Optional[Dict[str, ESSystem]] = None):
        """Initialize exporter.

        Args:
            custom_systems: Custom system configurations
        """
        self._systems = dict(ES_SYSTEMS)
        if custom_systems:
            self._systems.update(custom_systems)

    def export(
        self,
        roms: List[Dict[str, Any]],
        target_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        create_gamelists: bool = True,
        include_metadata: bool = True,
    ) -> ExportResult:
        """Export ROMs to Batocera format.

        Args:
            roms: ROM list with 'path', 'platform', 'name', optional metadata
            target_path: Target SD card / share path
            progress_callback: Progress callback
            create_gamelists: Create gamelist.xml files
            include_metadata: Include metadata in gamelists

        Returns:
            ExportResult
        """
        result = ExportResult(success=True)
        target = Path(target_path)
        roms_base = target / self.ROMS_BASE
        roms_base.mkdir(parents=True, exist_ok=True)

        # Track games per system for gamelists
        games_per_system: Dict[str, List[Dict[str, Any]]] = {}

        total = len(roms)

        for i, rom in enumerate(roms):
            rom_path = Path(rom.get("path", ""))
            platform = rom.get("platform", "unknown").lower()
            name = rom.get("name", rom_path.stem)

            if progress_callback:
                progress_callback(i + 1, total, name)

            # Find system config
            system = self._find_system(platform)
            if not system:
                result.skipped_count += 1
                result.errors.append(f"Unknown platform: {platform}")
                continue

            # Create system folder
            system_folder = roms_base / system.name
            system_folder.mkdir(exist_ok=True)

            if system.name not in result.systems_created:
                result.systems_created.append(system.name)

            # Copy ROM
            dest_path = system_folder / rom_path.name

            # Handle duplicates
            counter = 1
            while dest_path.exists():
                stem = rom_path.stem
                suffix = rom_path.suffix
                dest_path = system_folder / f"{stem}_{counter}{suffix}"
                counter += 1

            try:
                shutil.copy2(rom_path, dest_path)
                result.exported_count += 1
                result.total_size_bytes += dest_path.stat().st_size

                # Track for gamelist
                if system.name not in games_per_system:
                    games_per_system[system.name] = []

                game_entry = {
                    "path": f"./{dest_path.name}",
                    "name": name,
                }

                if include_metadata:
                    game_entry.update({
                        "desc": rom.get("description", ""),
                        "developer": rom.get("developer", ""),
                        "publisher": rom.get("publisher", ""),
                        "genre": rom.get("genre", ""),
                        "releasedate": rom.get("release_date", ""),
                        "players": rom.get("players", ""),
                        "rating": rom.get("rating", ""),
                        "region": rom.get("region", ""),
                    })

                games_per_system[system.name].append(game_entry)

            except Exception as e:
                result.error_count += 1
                result.errors.append(f"Failed: {rom_path.name} - {e}")

        # Create gamelists
        if create_gamelists and games_per_system:
            for system_name, games in games_per_system.items():
                gamelist_path = roms_base / system_name / "gamelist.xml"
                self._create_gamelist(gamelist_path, games)
            result.gamelist_created = True

        result.success = result.error_count == 0
        return result

    def _find_system(self, platform: str) -> Optional[ESSystem]:
        """Find system configuration for platform."""
        platform_lower = platform.lower().replace("-", "").replace("_", "").replace(" ", "")

        # Direct match
        if platform_lower in self._systems:
            return self._systems[platform_lower]

        # Alias mapping
        aliases = {
            "megadrive": "genesis",
            "md": "genesis",
            "sfc": "snes",
            "superfamicom": "snes",
            "famicom": "nes",
            "fc": "nes",
            "gameboycolor": "gbc",
            "gameboyadvance": "gba",
            "gameboy": "gb",
            "nintendo64": "n64",
            "playstation": "psx",
            "ps1": "psx",
            "nintendods": "nds",
            "pcengine": "pce",
            "turbografx": "pce",
            "tg16": "pce",
        }

        mapped = aliases.get(platform_lower)
        if mapped and mapped in self._systems:
            return self._systems[mapped]

        return None

    def _create_gamelist(
        self,
        path: Path,
        games: List[Dict[str, Any]],
    ) -> None:
        """Create gamelist.xml file."""
        root = ET.Element("gameList")

        for game in games:
            game_elem = ET.SubElement(root, "game")

            for key, value in game.items():
                if value:  # Only add non-empty values
                    child = ET.SubElement(game_elem, key)
                    child.text = str(value)

        # Pretty print
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")

        with open(path, "w", encoding="utf-8") as f:
            f.write(xml_str)

    def get_supported_systems(self) -> List[str]:
        """Get supported systems."""
        return list(self._systems.keys())

    def create_es_systems_config(self, target_path: str) -> str:
        """Create es_systems.cfg for EmulationStation.

        Args:
            target_path: Config directory

        Returns:
            Path to created file
        """
        target = Path(target_path)
        target.mkdir(parents=True, exist_ok=True)

        root = ET.Element("systemList")

        for system in self._systems.values():
            sys_elem = ET.SubElement(root, "system")

            ET.SubElement(sys_elem, "name").text = system.name
            ET.SubElement(sys_elem, "fullname").text = system.fullname
            ET.SubElement(sys_elem, "path").text = system.path
            ET.SubElement(sys_elem, "extension").text = system.extension
            ET.SubElement(sys_elem, "command").text = system.command
            ET.SubElement(sys_elem, "platform").text = system.platform
            ET.SubElement(sys_elem, "theme").text = system.theme

        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        config_path = target / "es_systems.cfg"

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(xml_str)

        return str(config_path)


class RetroPieExporter(BatoceraExporter):
    """Exports ROMs for RetroPie.

    Same structure as Batocera but with RetroPie-specific paths.
    """

    ROMS_BASE = "RetroPie/roms"
    BIOS_BASE = "RetroPie/BIOS"

    def __init__(self, custom_systems: Optional[Dict[str, ESSystem]] = None):
        """Initialize RetroPie exporter."""
        super().__init__(custom_systems)

        # Update paths for RetroPie
        for system in self._systems.values():
            system.path = f"~/RetroPie/roms/{system.name}"

    def create_retropie_structure(self, target_path: str) -> List[str]:
        """Create basic RetroPie folder structure.

        Args:
            target_path: Target SD card

        Returns:
            Created folders
        """
        target = Path(target_path)
        folders = [
            "RetroPie/roms",
            "RetroPie/BIOS",
            "RetroPie/retropiemenu",
            "RetroPie/splashscreens",
        ]

        created = []
        for folder in folders:
            path = target / folder
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path))

        # Create system folders
        for system in self._systems.values():
            system_path = target / "RetroPie/roms" / system.name
            system_path.mkdir(exist_ok=True)
            created.append(str(system_path))

        return created
