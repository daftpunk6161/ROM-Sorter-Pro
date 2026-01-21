#!/usr/bin/env python3
"""
ROM Sorter Pro - Console File Type Mappings

This module defines mappings between file extensions and console systems.
It contains cleaned up mappings from the original gui.py with duplicates removed.
"""

# Define the mapping of file extensions to console types
CONSOLE_MAP = {
    # Nintendo Handhelds
    '.gb': 'Nintendo_Game_Boy',
    '.sgb': 'Nintendo_Game_Boy',
    '.dmg': 'Nintendo_Game_Boy',
    '.gbc': 'Nintendo_Game_Boy_Color',
    '.gba': 'Nintendo_Game_Boy_Advance',
    '.agb': 'Nintendo_Game_Boy_Advance',
    '.mb': 'Nintendo_Game_Boy_Advance',
    '.nds': 'Nintendo_DS',
    '.dsi': 'Nintendo_DS',
    '.3ds': 'Nintendo_3DS',
    '.cia': 'Nintendo_3DS',
    '.3dsx': 'Nintendo_3DS',
    '.cci': 'Nintendo_3DS',
    '.cxi': 'Nintendo_3DS',
    '.app': 'Nintendo_3DS',

    # Nintendo Home Consoles
    '.nes': 'Nintendo_NES',
    '.unf': 'Nintendo_NES',
    '.unif': 'Nintendo_NES',
    '.fds': 'Nintendo_NES',
    '.nsf': 'Nintendo_NES',
    '.qd': 'Nintendo_NES',
    '.snes': 'Super_Nintendo',
    '.smc': 'Super_Nintendo',
    '.sfc': 'Super_Nintendo',
    '.fig': 'Super_Nintendo',
    '.swc': 'Super_Nintendo',
    '.st': 'Super_Nintendo',
    '.bs': 'Super_Nintendo',
    '.n64': 'Nintendo_64',
    '.v64': 'Nintendo_64',
    '.z64': 'Nintendo_64',
    '.u64': 'Nintendo_64',
    '.jst': 'Nintendo_64',
    '.mpk': 'Nintendo_64',
    '.fla': 'Nintendo_64',
    '.gcm': 'Nintendo_GameCube',
    '.gcz': 'Nintendo_GameCube',
    '.rvz': 'Nintendo_GameCube',
    '.wia': 'Nintendo_GameCube',
    '.ciso': 'Nintendo_GameCube',
    '.dol': 'Nintendo_GameCube',
    '.elf': 'Nintendo_GameCube',
    '.wbfs': 'Nintendo_Wii',
    '.wad': 'Nintendo_Wii',
    '.u8': 'Nintendo_Wii',
    '.tmd': 'Nintendo_Wii',
    '.tik': 'Nintendo_Wii',
    '.wud': 'Nintendo_Wii_U',
    '.wux': 'Nintendo_Wii_U',
    '.rpx': 'Nintendo_Wii_U',
    '.rpl': 'Nintendo_Wii_U',
    '.wua': 'Nintendo_Wii_U',
    '.xci': 'Nintendo_Switch',
    '.nsp': 'Nintendo_Switch',
    '.nsz': 'Nintendo_Switch',
    '.kip': 'Nintendo_Switch',
    '.nca': 'Nintendo_Switch',
    '.cert': 'Nintendo_Switch',

    # Sony Consoles
    '.iso': 'PlayStation',
    '.img': 'PlayStation',
    '.mdf': 'PlayStation',
    '.cue': 'PlayStation',
    '.ecm': 'PlayStation',
    '.mds': 'PlayStation_2',
    '.nrg': 'PlayStation_2',
    '.pkg': 'PlayStation_3',
    '.psn': 'PlayStation_3',
    '.p3t': 'PlayStation_3',
    '.pup': 'PlayStation_4',
    '.gp4': 'PlayStation_4',
    '.psp': 'PlayStation_Portable',
    '.pbp': 'PlayStation_Portable',
    '.vpk': 'PlayStation_Vita',
    '.psvgz': 'PlayStation_Vita',

    # Sega Consoles
    '.sms': 'Sega_Master_System',
    '.sg': 'Sega_Master_System',
    '.sc': 'Sega_Master_System',
    '.mv': 'Sega_Master_System',
    '.gg': 'Sega_Game_Gear',
    '.md': 'Sega_Genesis',
    '.gen': 'Sega_Genesis',
    '.smd': 'Sega_Genesis',
    '.sgd': 'Sega_Genesis',
    '.68k': 'Sega_Genesis',
    '.32x': 'Sega_32X',
    '.scd': 'Sega_CD',
    '.gdi': 'Sega_Dreamcast',
    '.cdi': 'Sega_Dreamcast',
    '.sat': 'Sega_Saturn',

    # Microsoft Consoles
    '.xbe': 'Xbox',
    '.xex': 'Xbox_360',
    '.xvd': 'Xbox_One',
    '.xvc': 'Xbox_Series',

    # Atari Consoles
    '.a26': 'Atari_2600',
    '.a52': 'Atari_5200',
    '.a78': 'Atari_7800',
    '.lnx': 'Atari_Lynx',
    '.lyx': 'Atari_Lynx',
    '.o': 'Atari_Lynx',
    '.jag': 'Atari_Jaguar',
    '.j64': 'Atari_Jaguar',
    '.ate': 'Atari_8bit',
    '.ast': 'Atari_ST',

    # NEC Consoles
    '.pce': 'PC_Engine',
    '.pc98': 'NEC_PC98',
    '.pc88': 'NEC_PC88',
    '.sgx': 'SuperGrafx',

    # SNK Consoles
    '.neo': 'Neo_Geo',
    '.ngp': 'Neo_Geo_Pocket',
    '.ngc': 'Neo_Geo_Pocket_Color',
    '.mvs': 'Neo_Geo_MVS',
    '.aes': 'Neo_Geo_AES',

    # Computer Systems
    '.adf': 'Amiga',
    '.adz': 'Amiga',
    '.dms': 'Amiga',
    '.ipf': 'Amiga',
    '.hdf': 'Amiga',
    '.d64': 'Commodore_64',
    '.t64': 'Commodore_64',
    '.tap': 'Commodore_64',
    '.prg': 'Commodore_64',
    '.p00': 'Commodore_64',
    '.crt': 'Commodore_64',
    '.d71': 'Commodore_128',
    '.d81': 'Commodore_128',
    '.dsk': 'Apple_II',
    '.nib': 'Apple_II',
    '.po': 'Apple_II',
    '.do': 'Apple_II',
}

# Handle problematic extensions (previously duplicates)
# For files that can belong to multiple systems, we create separate mappings
EXTENSION_PRIORITY_MAP = {
    # PlayStation/PlayStation 2
    '.bin': {
        'priority': ['PlayStation', 'Atari_2600'],
        'detection_hints': {
            'PlayStation': ['SCEI', 'BOOT', 'system.cnf', 'SYSTEM.CNF'],
            'Atari_2600': ['STELLA', '2600', 'ATARI']
        }
    },

    # PlayStation Portable/PlayStation 2
    '.cso': {
        'priority': ['PlayStation_Portable', 'PlayStation_2'],
        'detection_hints': {
            'PlayStation_Portable': ['PSP', 'ULES', 'ULUS', 'UCUS', 'UCJS'],
            'PlayStation_2': ['PS2', 'SLUS', 'SLES', 'SLPS']
        }
    },

    # Sega Dreamcast/PlayStation 2
    '.chd': {
        'priority': ['Sega_Dreamcast', 'PlayStation_2'],
        'detection_hints': {
            'Sega_Dreamcast': ['SEGA', 'GD-ROM', 'DREAMCAST'],
            'PlayStation_2': ['PS2', 'SLUS', 'SLES', 'SLPS']
        }
    }
}

# Function to resolve file extension to console type
def get_console_for_extension(ext, file_content=None, filename=None):
    """Get console type for a file extension, using content analysis for ambiguous extensions. ARGS: Ext: File Extension (With Leading Dot) File_Content: Optional File Content for Further Analysis Filename: Optional Filename for Further Analysis Return: Str: Console Type Identifier or 'Unknown' if not Recognizedizedizedizedized"""
    ext = ext.lower()

    # Direct mapping
    if ext in CONSOLE_MAP:
        return CONSOLE_MAP[ext]

    # Ambiguous extension that needs resolution
    if ext in EXTENSION_PRIORITY_MAP:
        mapping = EXTENSION_PRIORITY_MAP[ext]

        # If we have content or filename for analysis
        if file_content or filename:
            for console in mapping['priority']:
                hints = mapping['detection_hints'].get(console, [])

                # Check if any hints match the content or filename
                if any(hint in str(file_content) for hint in hints) or \
                   (filename and any(hint in filename for hint in hints)):
                    return console

        # Default to first priority if no detection possible
        return mapping['priority'][0]

    # Unknown extension
    return 'Unknown'
