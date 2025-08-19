#!/usr/bin/env python3
"""
ROM Sorter Pro - GUI Components Module

This module contains reusable UI components for the ROM Sorter Pro GUI.
"""

import logging
import tkinter as tk
from tkinter import ttk, Frame, Label, Button

logger = logging.getLogger(__name__)


def create_drop_zone(parent):
    """Create a drop zone for drag and drop functionality.

    Args:
        parent: Parent widget or window

    Returns:
        Frame: The drop zone frame
    """
    frame = Frame(parent, bg="#f0f0f0", bd=2, relief=tk.GROOVE)

    # Main label
    main_label = Label(frame, text="Drop ROM Files Here", font=("Arial", 16), bg="#f0f0f0")
    main_label.pack(pady=(20, 10))

    # Sub label
    sub_label = Label(frame, text="or click to select files", font=("Arial", 10), bg="#f0f0f0")
    sub_label.pack(pady=(0, 20))

    frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    # Store references in parent
    parent.components["drop_zone"] = frame
    parent.components["drop_zone_main_label"] = main_label
    parent.components["drop_zone_sub_label"] = sub_label

    return frame


def create_progress_bar(parent):
    """Create a progress bar with a label.

    Args:
        parent: Parent widget or window

    Returns:
        tuple: (progressbar, label)
    """
    frame = Frame(parent)

    # Progress bar
    progress = ttk.Progressbar(frame, orient=tk.HORIZONTAL,
                              length=100, mode='determinate',
                              variable=parent.progress_value)
    progress.pack(fill=tk.X, padx=20, pady=(5, 0))

    # Label
    label = Label(frame, textvariable=parent.status_text)
    label.pack(pady=(0, 5))

    frame.pack(fill=tk.X, padx=20, pady=5)

    # Store references in parent
    parent.components["progress_bar"] = progress
    parent.components["progress_label"] = label

    return progress, label


def create_button_panel(parent):
    """Create a panel with action buttons.

    Args:
        parent: Parent widget or window

    Returns:
        Frame: The button panel frame
    """
    frame = Frame(parent)

    # Scan button
    scan_btn = Button(frame, text="Scan", width=10)
    scan_btn.pack(side=tk.LEFT, padx=5)

    # Start button
    start_btn = Button(frame, text="Start", width=10)
    start_btn.pack(side=tk.LEFT, padx=5)
    start_btn.config(state=tk.DISABLED)

    # Stop button
    stop_btn = Button(frame, text="Stop", width=10)
    stop_btn.pack(side=tk.LEFT, padx=5)
    stop_btn.config(state=tk.DISABLED)

    frame.pack(pady=10)

    # Store references in parent
    parent.components["scan_button"] = scan_btn
    parent.components["start_button"] = start_btn
    parent.components["stop_button"] = stop_btn

    return frame
