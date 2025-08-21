#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rome Sorter Pro - Ui module entry point Enables direct start of the UI module: python -m src.ui"""

import sys
def main():
    """Main entry point for the UI module."""
    try:
        from .gui import main as gui_main
        return gui_main()
    except ImportError:
        import logging
        logging.error("Could not import gui module. UI may not be available.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
