#!/usr/bin/env python3
"""
Test script for console mappings
"""

# Add the main project directory to the Python search path
import os
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import our module directly
from src.ui.console_mappings import CONSOLE_MAP, get_console_for_extension, EXTENSION_PRIORITY_MAP

# Test basic extensions
print("\nBasic extension mapping:")
print(f"NES: {get_console_for_extension('.nes')}")
print(f"GBA: {get_console_for_extension('.gba')}")
print(f"PS1: {get_console_for_extension('.iso')}")

# Test ambiguous extensions
print("\nAmbiguous extension mapping (default):")
print(f"CSO (PSP/PS2): {get_console_for_extension('.cso')}")
print(f"BIN (PS1/Atari): {get_console_for_extension('.bin')}")
print(f"CHD (PS2/Dreamcast): {get_console_for_extension('.chd')}")
print(f"SGX (PCE/SuperGrafx): {get_console_for_extension('.sgx')}")

# Test with content analysis
print("\nAmbiguous extension mapping (with content analysis):")
print(f"CSO with PSP hint: {get_console_for_extension('.cso', filename='Ridge_Racer_ULES00001.cso')}")
print(f"CSO with PS2 hint: {get_console_for_extension('.cso', filename='Gran_Turismo_4_SLUS20911.cso')}")

print(f"BIN with PS1 hint: {get_console_for_extension('.bin', filename='Crash_Bandicoot.bin')}")
print(f"BIN with Atari hint: {get_console_for_extension('.bin', filename='Asteroids_2600.bin')}")

print("\nExtension priority information:")
for ext, info in EXTENSION_PRIORITY_MAP.items():
    print(f"{ext}: {info['priority']}")

# Print stats
print("\nStatistics:")
print(f"Total unique extensions: {len(CONSOLE_MAP)}")
print(f"Ambiguous extensions: {len(EXTENSION_PRIORITY_MAP)}")
unique_consoles = set(CONSOLE_MAP.values())
print(f"Unique console types: {len(unique_consoles)}")
