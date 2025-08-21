#!/usr/bin/env python3
"""
Integration Test for the Console Mapping Functionality

This script tests the functionality of the console mapping in the context
of the entire ROM-Sorter-Pro application.
"""

import os
import sys
import unittest
from pathlib import Path

# Add the main directory to the search path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the required modules
try:
    from src.ui.console_mappings import CONSOLE_MAP, get_console_for_extension, EXTENSION_PRIORITY_MAP
    print("[✓] Console mapping module successfully imported")
except ImportError as e:
    print(f"[✗] Error importing the console mapping module: {e}")
    sys.exit(1)

class TestConsoleMappings(unittest.TestCase):
    """Test class for console mappings"""

    def test_basic_extensions(self):
        """Tests the basic functionality of the mapping function"""
        self.assertEqual(get_console_for_extension('.nes'), 'Nintendo_NES')
        self.assertEqual(get_console_for_extension('.gba'), 'Nintendo_Game_Boy_Advance')
        self.assertEqual(get_console_for_extension('.n64'), 'Nintendo_64')
        self.assertEqual(get_console_for_extension('.unknown'), 'Unknown')

    def test_ambiguous_extensions(self):
        """Tests the resolution of ambiguous file extensions"""
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

            # Make sure detection_hints exist for all priority entries
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

    # Run tests
    print("\nStarting tests...")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == "__main__":
    main()
