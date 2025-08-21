#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - Import Path Checker

This script checks the Python import path and module structure
to diagnose import problems.
"""

import sys
import os
import importlib
import traceback

def check_path():
    """Checks the Python search path."""
    print("Python search path:")
    for i, path in enumerate(sys.path):
        print(f"  {i}: {path}")
    print()

def check_module(module_name):
    """
    Attempts to import a module and displays details.

    Args:
        module_name: The name of the module to import
    """
    print(f"Trying to import '{module_name}'...")
    try:
        module = importlib.import_module(module_name)
        print(f"  ✓ Success!")
        print(f"  Module path: {getattr(module, '__file__', 'Unknown')}")
        print(f"  Module package: {getattr(module, '__package__', 'No package')}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        traceback.print_exc()
    print()

def check_circular_imports():
    """Checks for possible circular imports in specific files."""
    problem_files = [
        "src/config/__init__.py",
        "src/ui/gui_core.py",
        "src/ui/gui.py"
    ]

    print("Checking problematic files:")
    for file_path in problem_files:
        abs_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(abs_path):
            print(f"  Untersuche {file_path}...")
            with open(abs_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                imports = [line.strip() for line in lines if 'import' in line]
                for imp in imports:
                    print(f"    - {imp}")
        else:
            print(f"  ✗ Datei nicht gefunden: {file_path}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("ROM Sorter Pro - Import-Diagnose")
    print("=" * 60)

    check_path()

    print("Modulimport-Tests:")
    print("-" * 40)
    modules_to_check = [
        "src",
        "src.ui",
        "src.ui.gui_core",
        "src.ui.gui_components",
        "src.ui.gui_scanner",
        "src.ui.gui_dnd",
        "src.ui.gui_handlers",
        "src.config",
    ]

    for module in modules_to_check:
        check_module(module)

    print("Zirkuläre Import-Analyse:")
    print("-" * 40)
    check_circular_imports()

    print("=" * 60)
