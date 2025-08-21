#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - Logger Module

This module provides a uniform configuration for logging throughout the project.
"""

import logging
import os
import sys
from pathlib import Path

def setup_logger(name, level=logging.INFO):
    """
    Creates a configured logger.

    Args:
        name: Name of the logger
        level: Log level

    Returns:
        Logger: The configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # If the logger already has handlers, return it
    if logger.handlers:
        return logger

    # Make sure the log directory exists
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)

    # File Handler for all logs
    file_handler = logging.FileHandler(logs_dir / 'rom_sorter.log', encoding='utf-8')
    file_handler.setLevel(level)

    # File Handler for Error
    error_handler = logging.FileHandler(logs_dir / 'rom_sorter_errors.log', encoding='utf-8')
    error_handler.setLevel(logging.WARNING)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handler
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)

    return logger
