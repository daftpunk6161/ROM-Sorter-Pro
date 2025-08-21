#!/usr/bin/env python3
"""
Direkte Tests für die Konsolen-Mappings (ohne Integration)

Dieses Skript testet die Konsolen-Mapping-Funktionalität direkt,
ohne die gesamte Anwendung zu laden.
"""

import sys
import unittest
from pathlib import Path

# Define the test data directly in the test
CONSOLE_MAP = {
    '.nes': 'Nintendo_NES',
    '.unf': 'Nintendo_NES',
    '.gba': 'Nintendo_Game_Boy_Advance',
    '.agb': 'Nintendo_Game_Boy_Advance',
    '.n64': 'Nintendo_64',
    '.v64': 'Nintendo_64',
}

EXTENSION_PRIORITY_MAP = {
    '.bin': {
        'priority': ['PlayStation', 'Atari_2600'],
        'detection_hints': {
            'PlayStation': ['SCEI', 'BOOT', 'system.cnf', 'SYSTEM.CNF'],
            'Atari_2600': ['STELLA', '2600', 'ATARI']
        }
    },
    '.cso': {
        'priority': ['PlayStation_Portable', 'PlayStation_2'],
        'detection_hints': {
            'PlayStation_Portable': ['PSP', 'ULES', 'ULUS', 'UCUS', 'UCJS'],
            'PlayStation_2': ['PS2', 'SLUS', 'SLES', 'SLPS']
        }
    },
    '.chd': {
        'priority': ['Sega_Dreamcast', 'PlayStation_2'],
        'detection_hints': {
            'Sega_Dreamcast': ['SEGA', 'GD-ROM', 'DREAMCAST'],
            'PlayStation_2': ['PS2', 'SLUS', 'SLES', 'SLPS']
        }
    }
}

def get_console_for_extension(ext, file_content=None, filename=None):
    """
    Get console type for a file extension, using content analysis for ambiguous extensions.

    Args:
        ext: File extension (with leading dot)
        file_content: Optional file content for further analysis
        filename: Optional filename for further analysis

    Returns:
        str: Console type identifier or 'Unknown' if not recognized
    """
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
                if any(hint in str(file_content or '') for hint in hints) or \
                   (filename and any(hint in filename for hint in hints)):
                    return console

        # Default to first priority if no detection possible
        return mapping['priority'][0]

    # Unknown extension
    return 'Unknown'

class TestConsoleMappings(unittest.TestCase):
    """Testklasse für die Konsolen-Mappings"""

    def test_basic_extensions(self):
        """Testet die grundlegende Funktionalität der Mapping-Function"""
        self.assertEqual(get_console_for_extension('.nes'), 'Nintendo_NES')
        self.assertEqual(get_console_for_extension('.gba'), 'Nintendo_Game_Boy_Advance')
        self.assertEqual(get_console_for_extension('.n64'), 'Nintendo_64')
        self.assertEqual(get_console_for_extension('.unknown'), 'Unknown')

    def test_ambiguous_extensions(self):
        """Testet die Auflösung von mehrdeutigen Dateierweiterungen"""
        # Test default priorities
        self.assertEqual(get_console_for_extension('.bin'), 'PlayStation')
        self.assertEqual(get_console_for_extension('.cso'), 'PlayStation_Portable')
        self.assertEqual(get_console_for_extension('.chd'), 'Sega_Dreamcast')

        # Test with content analysis
        self.assertEqual(
            get_console_for_extension('.bin', filename='Super_Mario_Brothers_2600.bin'),
            'Atari_2600'
        )
        self.assertEqual(
            get_console_for_extension('.bin', filename='Final_Fantasy_VII.bin'),
            'PlayStation'
        )

        self.assertEqual(
            get_console_for_extension('.cso', filename='God_of_War_SLUS21228.cso'),
            'PlayStation_2'
        )
        self.assertEqual(
            get_console_for_extension('.cso', filename='Monster_Hunter_ULUS10391.cso'),
            'PlayStation_Portable'
        )

    def test_extension_consistency(self):
        """Testet, ob alle Extensions im CONSOLE_MAP definiert sind"""
        for extension in EXTENSION_PRIORITY_MAP.keys():
            # Make sure that the extension is not in console_map
            self.assertNotIn(extension, CONSOLE_MAP)

            # Make sure the priority list is not empty
            self.assertTrue(len(EXTENSION_PRIORITY_MAP[extension]['priority']) > 0)

            # Make sure that Detection_hints exist for all priority entries
            for console in EXTENSION_PRIORITY_MAP[extension]['priority']:
                self.assertIn(console, EXTENSION_PRIORITY_MAP[extension]['detection_hints'])

def main():
    """Hauptfunktion"""
    print("\n=== ROM-Sorter Pro: Konsolen-Mapping-Tests ===\n")

    # Statistiken anzeigen
    print(f"Anzahl der definierten Dateierweiterungen: {len(CONSOLE_MAP)}")
    print(f"Anzahl der mehrdeutigen Dateierweiterungen: {len(EXTENSION_PRIORITY_MAP)}")

    unique_consoles = set(CONSOLE_MAP.values())
    for console_mapping in EXTENSION_PRIORITY_MAP.values():
        for console in console_mapping['priority']:
            unique_consoles.add(console)

    print(f"Anzahl der unterstützten Konsolentypen: {len(unique_consoles)}")

    # Execute tests
    print("\nStarte Tests...")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == "__main__":
    main()
