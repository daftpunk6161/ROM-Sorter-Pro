#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Console Database
"""

import logging
from typing import Dict, List, Any, Set, Optional
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)


@dataclass
class EnhancedConsoleMeta:
    """Enhanced console metadata."""
    folder_name: str
    manufacturer: str
    release_year: int
    extensions: Set[str]
    priority: int = 0
    emulator_compatibility: Optional[List[str]] = None
    typical_rom_size_mb: float = 0.0
    patterns: Optional[List[str]] = None

    def __post_init__(self):
        if self.emulator_compatibility is None:
            self.emulator_compatibility = []
        if self.patterns is None:
            self.patterns = []
        # Ensure extensions start with a dot
        self.extensions = {
            ext if ext.startswith('.') else f'.{ext}'
            for ext in self.extensions
        }


# Central Console Database with Enhanced Metadata
ENHANCED_CONSOLE_DATABASE = {
    # Nintendo
    'NES': EnhancedConsoleMeta(
        folder_name='Nintendo NES',
        manufacturer='Nintendo',
        release_year=1983,
        extensions={'.nes'},
        priority=10,
        emulator_compatibility=['FCEUX', 'Nestopia', 'Mesen'],
        typical_rom_size_mb=0.5
    ),
    'SNES': EnhancedConsoleMeta(
        folder_name='Super Nintendo',
        manufacturer='Nintendo',
        release_year=1990,
        extensions={'.smc', '.sfc', '.fig', '.swc'},
        priority=10,
        emulator_compatibility=['Snes9x', 'ZSNES', 'bsnes', 'higan'],
        typical_rom_size_mb=2.0
    ),
    'N64': EnhancedConsoleMeta(
        folder_name='Nintendo 64',
        manufacturer='Nintendo',
        release_year=1996,
        extensions={'.n64', '.z64', '.v64', '.ndd'},
        priority=10,
        emulator_compatibility=['Project64', 'Mupen64Plus', 'BizHawk'],
        typical_rom_size_mb=16.0
    ),
    'GBA': EnhancedConsoleMeta(
        folder_name='Game Boy Advance',
        manufacturer='Nintendo',
        release_year=2001,
        extensions={'.gba'},
        priority=8,
        emulator_compatibility=['VisualBoyAdvance', 'mGBA', 'higan'],
        typical_rom_size_mb=4.0
    ),
    'GBC': EnhancedConsoleMeta(
        folder_name='Game Boy Color',
        manufacturer='Nintendo',
        release_year=1998,
        extensions={'.gbc'},
        priority=7,
        emulator_compatibility=['BGB', 'Gambatte', 'VisualBoyAdvance'],
        typical_rom_size_mb=0.5
    ),
    'GB': EnhancedConsoleMeta(
        folder_name='Game Boy',
        manufacturer='Nintendo',
        release_year=1989,
        extensions={'.gb'},
        priority=6,
        emulator_compatibility=['BGB', 'Gambatte', 'VisualBoyAdvance'],
        typical_rom_size_mb=0.25
    ),
    '3DS': EnhancedConsoleMeta(
        folder_name='Nintendo 3DS',
        manufacturer='Nintendo',
        release_year=2011,
        extensions={'.3ds', '.cia'},
        priority=11,
        emulator_compatibility=['Citra'],
        typical_rom_size_mb=1024.0
    ),
    'NDS': EnhancedConsoleMeta(
        folder_name='Nintendo DS',
        manufacturer='Nintendo',
        release_year=2004,
        extensions={'.nds'},
        priority=9,
        emulator_compatibility=['DeSmuME', 'melonDS'],
        typical_rom_size_mb=64.0
    ),
    'SWITCH': EnhancedConsoleMeta(
        folder_name='Nintendo Switch',
        manufacturer='Nintendo',
        release_year=2017,
        extensions={'.nsp', '.xci'},
        priority=12,
        emulator_compatibility=['Yuzu', 'Ryujinx'],
        typical_rom_size_mb=4096.0
    ),
    'FDS': EnhancedConsoleMeta(
        folder_name='Famicom Disk System',
        manufacturer='Nintendo',
        release_year=1986,
        extensions={'.fds'},
        priority=5,
        emulator_compatibility=['FCEUX', 'Nestopia'],
        typical_rom_size_mb=0.25
    ),

    # Sega
    'Genesis': EnhancedConsoleMeta(
        folder_name='Sega Genesis',
        manufacturer='Sega',
        release_year=1988,
        extensions={'.md', '.gen', '.smd', '.bin'},
        priority=10,
        emulator_compatibility=['Genesis Plus GX', 'Kega Fusion'],
        typical_rom_size_mb=3.0
    ),
    '32X': EnhancedConsoleMeta(
        folder_name='Sega 32X',
        manufacturer='Sega',
        release_year=1994,
        extensions={'.32x', '.bin'},
        priority=8,
        emulator_compatibility=['Kega Fusion', 'PicoDrive'],
        typical_rom_size_mb=4.0
    ),
    'SegaCD': EnhancedConsoleMeta(
        folder_name='Sega CD',
        manufacturer='Sega',
        release_year=1991,
        extensions={'.iso', '.cue', '.bin', '.chd'},
        priority=9,
        emulator_compatibility=['Kega Fusion', 'Genesis Plus GX'],
        typical_rom_size_mb=650.0
    ),
    'Dreamcast': EnhancedConsoleMeta(
        folder_name='Sega Dreamcast',
        manufacturer='Sega',
        release_year=1998,
        extensions={'.gdi', '.cdi', '.chd'},
        priority=11,
        emulator_compatibility=['Redream', 'Flycast', 'Reicast'],
        typical_rom_size_mb=1024.0
    ),

    # Sony
    'PSX': EnhancedConsoleMeta(
        folder_name='PlayStation',
        manufacturer='Sony',
        release_year=1994,
        extensions={'.iso', '.bin', '.cue', '.img', '.mdf', '.pbp'},
        priority=10,
        emulator_compatibility=['PCSX-ReARMed', 'Mednafen', 'DuckStation'],
        typical_rom_size_mb=650.0
    ),
    'PS2': EnhancedConsoleMeta(
        folder_name='PlayStation 2',
        manufacturer='Sony',
        release_year=2000,
        extensions={'.iso', '.bin', '.cue', '.img', '.mdf', '.chd'},
        priority=10,
        emulator_compatibility=['PCSX2'],
        typical_rom_size_mb=4700.0
    ),
    'PSP': EnhancedConsoleMeta(
        folder_name='PlayStation Portable',
        manufacturer='Sony',
        release_year=2004,
        extensions={'.iso', '.cso', '.pbp'},
        priority=9,
        emulator_compatibility=['PPSSPP'],
        typical_rom_size_mb=1800.0
    ),
    'PS3': EnhancedConsoleMeta(
        folder_name='PlayStation 3',
        manufacturer='Sony',
        release_year=2006,
        extensions={'.iso', '.pkg'},
        priority=12,
        emulator_compatibility=['RPCS3'],
        typical_rom_size_mb=25000.0
    ),

    # Atari
    'Atari2600': EnhancedConsoleMeta(
        folder_name='Atari 2600',
        manufacturer='Atari',
        release_year=1977,
        extensions={'.a26'},
        priority=6,
        emulator_compatibility=['Stella'],
        typical_rom_size_mb=0.004
    ),
    'Atari5200': EnhancedConsoleMeta(
        folder_name='Atari 5200',
        manufacturer='Atari',
        release_year=1982,
        extensions={'.a52'},
        priority=6,
        emulator_compatibility=['Atari800'],
        typical_rom_size_mb=0.016
    ),
    'Atari7800': EnhancedConsoleMeta(
        folder_name='Atari 7800',
        manufacturer='Atari',
        release_year=1986,
        extensions={'.a78'},
        priority=6,
        emulator_compatibility=['ProSystem'],
        typical_rom_size_mb=0.048
    ),
    'ZX Spectrum': EnhancedConsoleMeta(
        folder_name='Sinclair ZX Spectrum',
        manufacturer='Sinclair',
        release_year=1982,
        extensions={'.tzx', '.tap', '.z80', '.sna', '.trd', '.rzx'},
        priority=6,
        emulator_compatibility=['Fuse', 'Speccy', 'ZEsarUX'],
        typical_rom_size_mb=0.1
    ),
    'Jaguar': EnhancedConsoleMeta(
        folder_name='Atari Jaguar',
        manufacturer='Atari',
        release_year=1993,
        extensions={'.j64', '.jag'},
        priority=7,
        emulator_compatibility=['Virtual Jaguar'],
        typical_rom_size_mb=6.0
    ),
    'Lynx': EnhancedConsoleMeta(
        folder_name='Atari Lynx',
        manufacturer='Atari',
        release_year=1989,
        extensions={'.lnx', '.lyx', '.o'},
        priority=5,
        emulator_compatibility=['Mednafen', 'Handy'],
        typical_rom_size_mb=0.512
    ),

    'Intellivision': EnhancedConsoleMeta(
        folder_name='Mattel Intellivision',
        manufacturer='Mattel',
        release_year=1979,
        extensions={'.int'},
        priority=5,
        emulator_compatibility=['jzIntv', 'MAME'],
        typical_rom_size_mb=0.256,
    ),

# Snk
    'NeoGeo': EnhancedConsoleMeta(
        folder_name='Neo Geo',
        manufacturer='SNK',
        release_year=1990,
        extensions={'.neo'},
        priority=7,
        emulator_compatibility=['FinalBurn Neo', 'MAME'],
        typical_rom_size_mb=128.0
    ),
    'NeoGeo Pocket': EnhancedConsoleMeta(
        folder_name='Neo Geo Pocket',
        manufacturer='SNK',
        release_year=1998,
        extensions={'.ngp', '.ngc', '.npc'},
        priority=5,
        emulator_compatibility=['Mednafen', 'NeoPop'],
        typical_rom_size_mb=1.5
    ),

# Nec
    'PC Engine': EnhancedConsoleMeta(
        folder_name='PC Engine',
        manufacturer='NEC',
        release_year=1987,
        extensions={'.pce', '.sgx'},
        priority=6,
        emulator_compatibility=['Mednafen', 'Ootake'],
        typical_rom_size_mb=1.0
    ),
    'PC-FX': EnhancedConsoleMeta(
        folder_name='PC-FX',
        manufacturer='NEC',
        release_year=1994,
        extensions={'.cue', '.ccd'},
        priority=5,
        emulator_compatibility=['Mednafen'],
        typical_rom_size_mb=650.0
    ),

    # Buckets (non-console families)
    'Arcade': EnhancedConsoleMeta(
        folder_name='Arcade',
        manufacturer='Various',
        release_year=0,
        extensions=set(),
        priority=1,
        emulator_compatibility=['MAME', 'FBNeo'],
        typical_rom_size_mb=0.0
    ),
    'Pinball': EnhancedConsoleMeta(
        folder_name='Pinball',
        manufacturer='Various',
        release_year=0,
        extensions={'.vpx', '.vpt', '.fpt', '.ptm', '.directb2s'},
        priority=1,
        emulator_compatibility=['Visual Pinball', 'Future Pinball'],
        typical_rom_size_mb=0.0
    ),

    # Windows / PC
    'Windows': EnhancedConsoleMeta(
        folder_name='Windows PC',
        manufacturer='Microsoft',
        release_year=1985,
        # Keep this conservative; ISO is intentionally NOT included here (too ambiguous).
        extensions={'.exe', '.msi', '.bat', '.lnk'},
        priority=1,
        emulator_compatibility=[],
        typical_rom_size_mb=0.0
    ),
}


@lru_cache(maxsize=1)
def get_all_rom_extensions(include_dot: bool = True) -> Set[str]:
    """
    Get all supported ROM extensions from enhanced database.

    Args:
        include_dot: If True, returns extensions with leading dot (e.g. '.nes')
                    If False, returns extensions without dot (e.g. 'nes')

    Returns:
        Set of ROM extensions in requested format
    """
    extensions = set()
    for meta in ENHANCED_CONSOLE_DATABASE.values():
        if include_dot:
# Database Already Contains Extensions With Dots
            extensions.update(meta.extensions)
        else:
# Strip Leading Dot for Extensions Without Dot
            extensions.update(ext.lstrip('.') for ext in meta.extensions)
    return extensions


@lru_cache(maxsize=1)
def get_supported_consoles() -> List[Dict[str, Any]]:
    """Returns a Comprehensive List of All Supported Consoles."""
    consoles = []
    for console_name, meta in ENHANCED_CONSOLE_DATABASE.items():
        console_info = {
            'name': console_name,
            'folder_name': meta.folder_name,
            'manufacturer': meta.manufacturer,
            'release_year': meta.release_year,
            'extensions': list(meta.extensions),
            'priority': meta.priority,
            'emulators': list(meta.emulator_compatibility or []),
            'typical_size_mb': meta.typical_rom_size_mb
        }
        consoles.append(console_info)
    return consoles


def get_console_for_extension(extension: str) -> Optional[str]:
    """Returns the Console Name for a Specific Extension. Args: Extension: The File Extension (With Or Without Leading Dot) Return: Console Name Or None If the Extension is not supported"""
    if not extension.startswith('.'):
        extension = f'.{extension}'

    for console_name, meta in ENHANCED_CONSOLE_DATABASE.items():
        if extension in meta.extensions:
            return console_name
    return None


def get_consoles_by_manufacturer(
    manufacturer: Optional[str] = None
) -> Dict[str, EnhancedConsoleMeta]:
    """
    Returns consoles grouped by manufacturer.

    Args:
        manufacturer: Optional manufacturer name to filter by

    Returns:
        Dictionary with console names as keys and metadata as values
    """
    result = {}

    for console_name, meta in ENHANCED_CONSOLE_DATABASE.items():
        if (manufacturer is None or
                meta.manufacturer.lower() == manufacturer.lower()):
            result[console_name] = meta

    return result


def get_console_folder_for_extension(extension: str) -> Optional[str]:
    """Returns the Console Folder Name for a Specific Extension. Args: Extension: The File Extension (With Or Without Leading Dot) Return: Console Folder Name Or None If the Extension is not supported"""
    console_name = get_console_for_extension(extension)
    if console_name:
        return ENHANCED_CONSOLE_DATABASE[console_name].folder_name
    return None
