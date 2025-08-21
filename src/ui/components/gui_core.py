"""
ROM Sorter Pro - GUI Core Module

This module provides the core GUI components for ROM Sorter Pro.
"""

import tkinter as tk
from tkinter import ttk
import logging

logger = logging.getLogger(__name__)

class ROMSorterGUI:
    """
    Main GUI class for ROM Sorter Pro
    """

    def __init__(self, root=None):
        """
        Initialize the GUI

        Args:
            root: Optional root Tk instance
        """
        self.root = root if root else tk.Tk()
        self.root.title("ROM Sorter Pro")
        self.root.geometry("800x600")

        # Setup UI components
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components"""
        # Main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Welcome label
        ttk.Label(
            self.main_frame,
            text="Welcome to ROM Sorter Pro",
            font=("Arial", 16)
        ).pack(pady=20)

    def run(self):
        """Run the main GUI loop"""
        self.root.mainloop()
