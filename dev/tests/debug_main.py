#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - Debug Script v2.1.7

This script runs the main application in debug mode for testing purposes.
"""

import sys
import traceback
import os

# Add the project to the Python path
sys.path.insert(0, '.')

try:
    from src.main import main
    # Call without parameters
    main()
except ImportError as e:
    print(f"Import error: {e}")
    traceback.print_exc()
except Exception as e:
    print(f"General error: {e}")
    traceback.print_exc()
