#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for the refactored GUI structure.

This test verifies that the refactored GUI can be loaded correctly.
"""

import os
import sys

# Add the project directory to the search path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

def test_gui_imports():
    """Tests if all required GUI modules can be imported."""
    try:
        from src.ui import gui_core
        from src.ui import gui_components
        from src.ui import gui_scanner
        from src.ui import gui_dnd
        from src.ui import gui_handlers
        from src.ui import gui
        print("✓ All GUI modules were successfully imported.")
        return True
    except ImportError as e:
        print(f"✗ Error importing GUI modules: {e}")
        return False

def test_gui_initialization():
    """Tests if the GUI can be initialized."""
    try:
        # For testing purposes only, we terminate the application immediately after initialization
        import tkinter as tk

        # Patch tkinter.Tk to prevent mainloop
        original_mainloop = tk.Tk.mainloop
        tk.Tk.mainloop = lambda self: None

        try:
            from src.ui.gui_core import ROMSorterGUI
            app = ROMSorterGUI()
            print("✓ GUI initialization successful.")
            return True
        finally:
            # Restore the original mainloop
            tk.Tk.mainloop = original_mainloop
    except Exception as e:
        print(f"✗ Fehler bei der GUI-Initialisierung: {e}")
        return False

if __name__ == "__main__":
    print("Teste GUI-Refactoring...")
    print("-" * 40)

    imports_success = test_gui_imports()
    if imports_success:
        init_success = test_gui_initialization()
    else:
        init_success = False

    print("-" * 40)
    if imports_success and init_success:
        print("✓ Alle Tests erfolgreich!")
        sys.exit(0)
    else:
        print("✗ Es sind Fehler aufgetreten!")
        sys.exit(1)
