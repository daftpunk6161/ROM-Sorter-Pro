#!/usr/bin/env python3
"""
ROM Sorter Pro - GUI Main Module

This module serves as the entry point for the ROM Sorter Pro GUI application.
It imports and uses the refactored GUI components.
"""

import logging
import sys
import os
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='logs/rom_sorter_gui.log',
    filemode='a'
)

# Make sure log directory exists
os.makedirs('logs', exist_ok=True)

# Add console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(console_handler)

logger = logging.getLogger(__name__)

# Import GUI core
try:
    from src.ui.gui_core import ROMSorterGUI
except ImportError as e:
    logger.error(f"Failed to import GUI modules: {e}")
    sys.exit(1)


def main():
    """Main function to start the ROM Sorter Pro GUI."""
    try:
        # Create and run the GUI
        app = ROMSorterGUI(title="ROM Sorter Pro 🎮 - Optimized v2.1.8")
        app.mainloop()
    except Exception as e:
        logger.error(f"Application crashed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
