#!/bin/bash
# ROM Sorter Pro - Startup script for Linux/macOS
# Version 2.1.8
# Copyright (c) 2025

echo "Starting ROM Sorter Pro..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found!"
    echo "Please install Python 3.8 or higher."
    echo "Download: https://www.python.org/downloads/"
    exit 1
fi

# Check if virtual environment exists and activate it
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

# Check if dependencies are installed
python3 -c "import PyQt5" &> /dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    python3 install_dependencies.py
fi

# Start the application (GUI-first entry)
python3 start_rom_sorter.py "$@"

# Deactivate virtual environment if it was activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi

exit 0
