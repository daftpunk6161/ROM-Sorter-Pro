#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - Main Module v2.1.7 (Compatibility Layer)

This is a compatibility wrapper around the main GUI module.
It redirects to the standard GUI implementation to avoid duplication.
"""

import os
import sys
import traceback
import logging
import logging.config
import importlib

# Ensure that the directory is in the search path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

def setup_logging():
    """Configures the logging system."""
    try:
        from ..logging_config import configure_logging
        configure_logging()
    except (ImportError, AttributeError):
        # Fallback to basic configuration if the module is not found
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

def show_error_and_exit(error_message):
    """Shows an error message and exits the application."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("ROM Sorter Pro - Error", error_message)
        root.destroy()
    except Exception:
        print(f"Error: {error_message}")
    finally:
        sys.exit(1)

def main():
    """Main application function - redirects to the standard GUI."""
    # Configure logging
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Import the main GUI module and run its main function
        logger.info("Redirecting to main GUI module...")

        # Try to use the standard main function from gui.py
        try:
            from .gui import main as gui_main
            gui_main()
        except ImportError:
            # Fallback to direct import of GUI core
            from .gui_core import ROMSorterGUI
            app = ROMSorterGUI()
            logger.info("ROM Sorter Pro GUI started")
            app.mainloop()
            logger.info("ROM Sorter Pro terminated")
    except ImportError as e:
        show_error_and_exit(f"Error importing GUI modules: {e}\n\n"
                           f"Details:\n{traceback.format_exc()}")
    except Exception as e:
        show_error_and_exit(f"An unexpected error occurred: {e}\n\n"
                           f"Details:\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()
