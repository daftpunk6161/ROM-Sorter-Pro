#!/usr/bin/env python3
"""
ROM Sorter Pro - GUI Handlers Module

This module contains event handlers and callbacks for the ROM Sorter Pro GUI.
"""

import logging
import os
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
from threading import Thread, Event

logger = logging.getLogger(__name__)


def setup_event_handlers(parent):
    """Set up all event handlers for the GUI.

    Args:
        parent: Parent GUI instance
    """
    # Store handler references
    parent.handlers["on_scan_click"] = lambda: on_scan_click(parent)
    parent.handlers["on_start_click"] = lambda: on_start_click(parent)
    parent.handlers["on_stop_click"] = lambda: on_stop_click(parent)
    parent.handlers["on_drop_zone_click"] = lambda: on_drop_zone_click(parent)
    parent.handlers["on_exit"] = lambda: on_exit(parent)

    # Connect handlers to components
    if "scan_button" in parent.components:
        parent.components["scan_button"].config(command=parent.handlers["on_scan_click"])

    if "start_button" in parent.components:
        parent.components["start_button"].config(command=parent.handlers["on_start_click"])

    if "stop_button" in parent.components:
        parent.components["stop_button"].config(command=parent.handlers["on_stop_click"])

    if "drop_zone" in parent.components:
        parent.components["drop_zone"].bind("<Button-1>", lambda e: parent.handlers["on_drop_zone_click"]())

    # Set window close handler
    parent.protocol("WM_DELETE_WINDOW", parent.handlers["on_exit"])


def on_scan_click(parent):
    """Handle scan button click event.

    Args:
        parent: Parent GUI instance
    """
    source_dir = filedialog.askdirectory(title="Select Source Directory")
    if not source_dir:
        return

    parent.source_path.set(source_dir)
    parent.status_text.set(f"Selected source: {source_dir}")
    logger.info(f"Source directory selected: {source_dir}")

    # Enable start button once source is selected
    if "start_button" in parent.components:
        parent.components["start_button"].config(state=tk.NORMAL)


def on_start_click(parent):
    """Handle start button click event.

    Args:
        parent: Parent GUI instance
    """
    source_dir = parent.source_path.get()
    if not source_dir or not os.path.exists(source_dir):
        messagebox.showerror("Error", "Please select a valid source directory first.")
        return

    # Ask for destination if not set
    dest_dir = parent.dest_path.get()
    if not dest_dir:
        dest_dir = filedialog.askdirectory(title="Select Destination Directory")
        if not dest_dir:
            return
        parent.dest_path.set(dest_dir)

    # Create destination if it doesn't exist
    try:
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        messagebox.showerror("Error", f"Could not create destination directory: {e}")
        return

    # Update UI
    parent.status_text.set("Starting processing...")
    parent.progress_value.set(0)

    if "stop_button" in parent.components:
        parent.components["stop_button"].config(state=tk.NORMAL)

    if "start_button" in parent.components:
        parent.components["start_button"].config(state=tk.DISABLED)

    # Create stop event for the worker thread
    parent.stop_event = Event()

    # Start worker thread
    parent.worker_thread = Thread(
        target=process_files,
        args=(parent, source_dir, dest_dir, parent.stop_event)
    )
    parent.worker_thread.daemon = True
    parent.worker_thread.start()


def on_stop_click(parent):
    """Handle stop button click event.

    Args:
        parent: Parent GUI instance
    """
    if hasattr(parent, "stop_event") and parent.stop_event:
        parent.status_text.set("Stopping...")
        parent.stop_event.set()


def on_drop_zone_click(parent):
    """Handle click on drop zone.

    Args:
        parent: Parent GUI instance
    """
    files = filedialog.askopenfilenames(
        title="Select ROM files",
        filetypes=[
            ("ROM files", "*.rom *.bin *.iso *.cue *.chd *.gba *.nds *.z64 *.n64"),
            ("Archive files", "*.zip *.7z *.rar"),
            ("All files", "*.*")
        ]
    )

    if files:
        # Process selected files
        parent.status_text.set(f"Selected {len(files)} file(s)")
        logger.info(f"Selected {len(files)} files via file dialog")


def on_exit(parent):
    """Handle application exit event.

    Args:
        parent: Parent GUI instance
    """
    if hasattr(parent, "stop_event") and parent.stop_event:
        parent.stop_event.set()

    if hasattr(parent, "worker_thread") and parent.worker_thread and parent.worker_thread.is_alive():
        if messagebox.askyesno("Confirm Exit", "Processing is still running. Do you want to exit anyway?"):
            parent.destroy()
    else:
        parent.destroy()


def process_files(parent, source_dir, dest_dir, stop_event):
    """Process files in a separate thread.

    Args:
        parent: Parent GUI instance
        source_dir: Source directory path
        dest_dir: Destination directory path
        stop_event: Event to signal thread termination
    """
    try:
        # This is a placeholder for the actual processing logic
        import time
        total_files = 100  # This would be determined by scanning source_dir

        for i in range(total_files):
            if stop_event.is_set():
                break

            # Update progress
            progress = (i + 1) / total_files
            parent.progress_value.set(progress * 100)
            parent.status_text.set(f"Processing file {i+1} of {total_files}")

            # Simulate processing time
            time.sleep(0.05)

        if not stop_event.is_set():
            parent.status_text.set("Processing complete!")
        else:
            parent.status_text.set("Processing stopped by user.")

    except Exception as e:
        logger.error(f"Error in processing thread: {e}")
        parent.status_text.set(f"Error: {e}")

    finally:
        # Update UI when done
        parent.after(0, lambda: update_ui_after_processing(parent))


def update_ui_after_processing(parent):
    """Update UI components after processing is complete.

    Args:
        parent: Parent GUI instance
    """
    if "start_button" in parent.components:
        parent.components["start_button"].config(state=tk.NORMAL)

    if "stop_button" in parent.components:
        parent.components["stop_button"].config(state=tk.DISABLED)
