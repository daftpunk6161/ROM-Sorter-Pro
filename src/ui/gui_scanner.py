#!/usr/bin/env python3
"""
ROM Sorter Pro - GUI Scanner Module

This module contains scanner-related functionality for the ROM Sorter Pro GUI.
"""

import logging
import os
import tkinter as tk
from tkinter import ttk, Frame, Text, Scrollbar
from threading import Thread, Event
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def setup_scanner_components(parent):
    """Set up scanner-related components for the GUI.

    Args:
        parent: Parent GUI instance
    """
    # Create scanner components
    create_log_widget(parent)
    create_stats_widget(parent)

    # Initialize scanner-related attributes
    parent.scan_stats = {
        "start_time": None,
        "end_time": None,
        "total_files": 0,
        "processed_files": 0,
        "success_count": 0,
        "error_count": 0,
        "skipped_count": 0,
        "file_types": {}
    }


def create_log_widget(parent):
    """Create a log display widget.

    Args:
        parent: Parent GUI instance

    Returns:
        Frame: The log widget frame
    """
    frame = Frame(parent)

    # Label
    ttk.Label(frame, text="Processing Log:").pack(anchor=tk.W, padx=5)

    # Text widget with scrollbar
    text_frame = Frame(frame)
    scrollbar = Scrollbar(text_frame)
    log_text = Text(text_frame, height=10, width=50, yscrollcommand=scrollbar.set)
    scrollbar.config(command=log_text.yview)

    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    text_frame.pack(fill=tk.BOTH, expand=True, padx=5)

    # Pack the main frame
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    # Store references
    parent.components["log_widget"] = frame
    parent.components["log_text"] = log_text

    # Add logging handler
    setup_gui_logging_handler(parent, log_text)

    return frame


def create_stats_widget(parent):
    """Create a statistics display widget.

    Args:
        parent: Parent GUI instance

    Returns:
        Frame: The stats widget frame
    """
    frame = Frame(parent)

    # Label
    ttk.Label(frame, text="Processing Statistics:").pack(anchor=tk.W, padx=5)

    # Stats text
    stats_text = Text(frame, height=6, width=50)
    stats_text.insert(tk.END, "No processing data available")
    stats_text.config(state=tk.DISABLED)
    stats_text.pack(fill=tk.BOTH, expand=True, padx=5)

    # Pack the main frame
    frame.pack(fill=tk.X, padx=10, pady=5)

    # Store references
    parent.components["stats_widget"] = frame
    parent.components["stats_text"] = stats_text

    return frame


def setup_gui_logging_handler(parent, log_text):
    """Set up a handler to redirect logs to the GUI.

    Args:
        parent: Parent GUI instance
        log_text: Text widget for log display
    """
    class TextHandler(logging.Handler):
        def __init__(self, text_widget):
            super().__init__()
            self.text_widget = text_widget

        def emit(self, record):
            msg = self.format(record)

            def append():
                self.text_widget.config(state=tk.NORMAL)
                self.text_widget.insert(tk.END, msg + '\n')
                self.text_widget.see(tk.END)
                self.text_widget.config(state=tk.DISABLED)

            # Schedule the update in the main thread
            parent.after(0, append)

    # Create and add the handler
    text_handler = TextHandler(log_text)
    text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # Add to logger
    app_logger = logging.getLogger()
    app_logger.addHandler(text_handler)

    # Store reference to remove later if needed
    parent.text_log_handler = text_handler


def update_scan_stats(parent, **kwargs):
    """Update scanning statistics.

    Args:
        parent: Parent GUI instance
        **kwargs: Statistics to update
    """
    # Update stats dictionary
    for key, value in kwargs.items():
        if key in parent.scan_stats:
            parent.scan_stats[key] = value

    # Update the stats display
    if "stats_text" in parent.components:
        stats_text = parent.components["stats_text"]
        stats_text.config(state=tk.NORMAL)
        stats_text.delete(1.0, tk.END)

        # Format the stats
        lines = []
        if parent.scan_stats["start_time"]:
            lines.append(f"Started: {parent.scan_stats['start_time'].strftime('%H:%M:%S')}")

        if parent.scan_stats["end_time"]:
            lines.append(f"Finished: {parent.scan_stats['end_time'].strftime('%H:%M:%S')}")

            # Calculate duration if both start and end are available
            if parent.scan_stats["start_time"]:
                duration = parent.scan_stats["end_time"] - parent.scan_stats["start_time"]
                lines.append(f"Duration: {duration.total_seconds():.1f} seconds")

        lines.append(f"Total files: {parent.scan_stats['total_files']}")
        lines.append(f"Processed: {parent.scan_stats['processed_files']}")
        lines.append(f"Success: {parent.scan_stats['success_count']}")
        lines.append(f"Errors: {parent.scan_stats['error_count']}")
        lines.append(f"Skipped: {parent.scan_stats['skipped_count']}")

        # Add file type breakdown if any
        if parent.scan_stats["file_types"]:
            lines.append("\nFile types:")
            for ext, count in parent.scan_stats["file_types"].items():
                lines.append(f"  {ext}: {count}")

        # Update the text widget
        stats_text.insert(tk.END, "\n".join(lines))
        stats_text.config(state=tk.DISABLED)
