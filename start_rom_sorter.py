#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Startup Script

This script starts the ROM Sorter Pro application.
It checks the environment and starts the appropriate UI.
"""

import os
import sys
import logging
import argparse
import platform
from pathlib import Path

# Ensure logs directory exists
import os
os.makedirs('logs', exist_ok=True)

# Configure logging only for the startup file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='logs/rom_sorter_startup.log',
    filemode='a',
    # Don't add any handler for stdout/stderr to avoid duplicate logs
    handlers=[logging.FileHandler('logs/rom_sorter_startup.log', mode='a')]
)
logger = logging.getLogger(__name__)

def check_environment():
    """Checks the runtime environment."""
    # Check Python version
    py_version = platform.python_version_tuple()
    if int(py_version[0]) < 3 or (int(py_version[0]) == 3 and int(py_version[1]) < 8):
        print(f"WARNING: Python {platform.python_version()} detected. ROM Sorter Pro requires Python 3.8 or higher.")
        logger.warning(f"Outdated Python version: {platform.python_version()}")

# Detect Operating System
    os_name = platform.system()
    logger.info(f"Operating system: {os_name} {platform.version()}")

# Check Directories
    required_dirs = ["logs", "rom_databases", "temp"]
    for directory in required_dirs:
        os.makedirs(directory, exist_ok=True)

    return True

def parse_arguments():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(description="ROM Sorter Pro - Universal ROM Organizer")
    parser.add_argument("--cli", action="store_true", help="Start in command line mode")
    parser.add_argument("--scan", metavar="DIR", help="Directly scan the specified directory")
    parser.add_argument("--version", action="store_true", help="Show version information")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    return parser.parse_args()

def main():
    """Main function to start the application."""
    logger.info("Starting ROM Sorter Pro...")

# Check Environment
    if not check_environment():
        sys.exit(1)

    # Parse command line arguments
    args = parse_arguments()

    if args.version:
        print("ROM Sorter Pro v2.1.7")
        print("Copyright (c) 2025")
        sys.exit(0)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")

# Try to Add the SRC Directory to the Python Path
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

# Start the Application in the Desired Mode
    try:
        if args.cli:
            logger.info("Starting in CLI mode...")
            from src.cli.console_interface import start_cli
            start_cli(scan_dir=args.scan)
        else:
            logger.info("Starting in GUI mode with refactored UI...")
            try:
                # First we try to use the new modular structure
                from src.ui import main as start_gui
                exit_code = start_gui()
                if exit_code != 0:
                    logger.error(f"GUI returned error code: {exit_code}")
                    sys.exit(exit_code)
            except ImportError as e:
                logger.warning(f"Could not import new UI structure: {e}, falling back to old structure")
                # Fallback zur alten Struktur
                from src.ui.gui import main as start_gui_old
                exit_code = start_gui_old()
                if exit_code != 0:
                    logger.error(f"GUI returned error code: {exit_code}")
                    sys.exit(exit_code)

    except ImportError as e:
        logger.error(f"Error importing modules: {e}")
        print(f"Error: {e}")
        print("Please run 'python install_dependencies.py' to install all required dependencies.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting the application: {e}")
        print(f"Error: {e}")
        sys.exit(1)

    logger.info("ROM Sorter Pro terminated.")

if __name__ == "__main__":
    main()
