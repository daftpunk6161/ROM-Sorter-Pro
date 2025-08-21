#!/usr/bin/env python3
"""
ROM Sorter Pro - GUI Core Module

This module contains the core functionality for the ROM Sorter Pro GUI.
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Union, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ..core.file_utils import create_directory_if_not_exists
from .gui_components import create_drop_zone
from .gui_handlers import setup_event_handlers
from .gui_scanner import setup_scanner_components
from .gui_dnd import setup_dnd_support

logger = logging.getLogger(__name__)


class ROMSorterGUI(tk.Tk):
    """Main GUI class for ROM Sorter Pro application."""

    def __init__(self, title="ROM Sorter Pro", width=1000, height=700):
        """Initialize the main GUI window.

        Args:
            title: Window title
            width: Initial window width
            height: Initial window height
        """
        super().__init__()
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.minsize(800, 600)

        # Setup core components
        self._setup_variables()
        self._setup_menu()
        self._setup_layout()

        # Setup additional components through imported modules
        self.components = {}
        self.handlers = {}

        # Setup components from other modules
        create_drop_zone(self)
        setup_event_handlers(self)
        setup_scanner_components(self)
        setup_dnd_support(self)

        logger.info("ROM Sorter GUI initialized")

    def _setup_variables(self):
        """Initialize variables for the application."""
        self.source_path = tk.StringVar()
        self.dest_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Ready")
        self.progress_value = tk.DoubleVar(value=0)

    def _setup_menu(self):
        """Create the main application menu."""
        # Menu setup will be implemented here
        pass

    def _setup_layout(self):
        """Create the main application layout."""
        # Layout setup will be implemented here
        pass
