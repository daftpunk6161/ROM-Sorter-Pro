"""
GUI Drag and Drop Support Module for ROM Sorter Pro.
This module provides compatibility shims for drag & drop operations.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Callable, Any, Optional
import tkinter as tk

# Configure logging
logger = logging.getLogger(__name__)

# DND availability flag
DND_AVAILABLE = True

class OptimizedDragDropFrame(tk.Frame):
    """Frame with optimized drag and drop support."""

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.drop_callback = None

    def set_drop_callback(self, callback):
        self.drop_callback = callback

class DragDropSupport:
    """Base class for drag and drop support."""

    def __init__(self):
        """Initialize the drag and drop support."""
        self.enabled = False
        self.initialized = False

    def setup(self, widget):
        """Set up drag and drop for a widget."""
        logger.warning("Base setup method called, no actual implementation")
        return False

    def is_available(self):
        """Check if drag and drop is available."""
        return self.enabled and self.initialized


# Default instance for import compatibility
dnd_support = DragDropSupport()


def setup_drag_drop(widget, callback=None):
    """Set up drag and drop for a widget with the best available implementation."""
    try:
        from src.dnd_support import setup_dnd
        return setup_dnd(widget, callback)
    except ImportError:
        logger.warning("Failed to import core dnd_support module, using fallback")
        return dnd_support.setup(widget)


def get_drop_handler():
    """Get the appropriate drop handler based on available implementations."""
    try:
        from src.dnd_support import DropHandler
        return DropHandler
    except ImportError:
        logger.warning("Failed to import DropHandler, using dummy implementation")

        # Dummy implementation
        class DummyDropHandler:
            def __init__(self, callback=None):
                self.callback = callback

            def handle_drop(self, files):
                logger.warning("Dummy drop handler called with files: %s", files)
                if self.callback and callable(self.callback):
                    self.callback(files)

        return DummyDropHandler
