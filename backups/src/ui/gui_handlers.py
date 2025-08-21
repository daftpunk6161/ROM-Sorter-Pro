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
    parent.handlers["on_files_dropped"] = lambda files: on_files_dropped(parent, files)
    parent.handlers["on_source_select"] = lambda: on_source_select(parent)
    parent.handlers["on_target_select"] = lambda: on_target_select(parent)
    parent.handlers["on_settings_click"] = lambda: on_settings_click(parent)
    parent.handlers["on_about_click"] = lambda: on_about_click(parent)

    # Setup button command bindings
    if "scan_button" in parent.components:
        parent.components["scan_button"].config(command=parent.handlers["on_scan_click"])

    if "start_button" in parent.components:
        parent.components["start_button"].config(command=parent.handlers["on_start_click"])

    if "stop_button" in parent.components:
        parent.components["stop_button"].config(command=parent.handlers["on_stop_click"])

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


def on_source_select(parent):
    """Handle source directory selection.

    Args:
        parent: Parent GUI instance
    """
    directory = filedialog.askdirectory(
        title="Select Source Directory",
        initialdir=os.path.expanduser("~")
    )

    if directory:
        parent.source_path.set(directory)
        logger.info(f"Source directory set to: {directory}")


def on_target_select(parent):
    """Handle target directory selection.

    Args:
        parent: Parent GUI instance
    """
    directory = filedialog.askdirectory(
        title="Select Target Directory",
        initialdir=os.path.expanduser("~")
    )

    if directory:
        parent.dest_path.set(directory)
        logger.info(f"Target directory set to: {directory}")


def on_settings_click(parent):
    """Open settings dialog.

    Args:
        parent: Parent GUI instance
    """
    # Implementation of settings dialog would go here
    messagebox.showinfo("Settings", "Settings dialog would open here.")


def on_about_click(parent):
    """Show about dialog.

    Args:
        parent: Parent GUI instance
    """
    messagebox.showinfo(
        "About ROM Sorter Pro",
        "ROM Sorter Pro v2.1.8\n\n"
        "A tool for organizing ROM files by console type.\n\n"
        "© 2025 ROM Sorter Pro Team"
    )


def on_files_dropped(parent, files):
    """Process dropped files.

    Args:
        parent: Parent GUI instance
        files: List of file paths
    """
    if not files:
        return

    logger.info(f"Processing {len(files)} dropped files")

    # If files contains directories, use the first one as source
    for file_path in files:
        if os.path.isdir(file_path):
            parent.source_path.set(file_path)
            logger.info(f"Source directory set to: {file_path}")
            break


def process_files(parent, source_dir, dest_dir, stop_event):
    """Process files in a separate thread. ARGS: Parent: Parent Gui Instance Source_dir: Source Directory Path Dest_dir: Destination Directory Path Stop_Event: Event to Signal Thread Termination"""
    from datetime import datetime

    try:
        # Set up scan statistics
        parent.scan_stats["start_time"] = datetime.now()
        parent.scan_stats["end_time"] = None
        parent.scan_stats["total_files"] = 0
        parent.scan_stats["processed_files"] = 0
        parent.scan_stats["success_count"] = 0
        parent.scan_stats["error_count"] = 0
        parent.scan_stats["skipped_count"] = 0
        parent.scan_stats["file_types"] = {}

        # Function to process each file
        def process_file(file_path):
            if stop_event.is_set():
                return

            try:
                # Update stats
                parent.scan_stats["processed_files"] += 1

                # Update file type stats
                ext = os.path.splitext(file_path)[1].lower()
                if ext not in parent.scan_stats["file_types"]:
                    parent.scan_stats["file_types"][ext] = 0
                parent.scan_stats["file_types"][ext] += 1

                # Here would be the actual file processing logic
                # For now, just simulate success
                parent.scan_stats["success_count"] += 1

                # Update UI periodically
                if parent.scan_stats["processed_files"] % 10 == 0:
                    progress = parent.scan_stats["processed_files"] / max(1, parent.scan_stats["total_files"])
                    parent.status_text.set(f"Processing file {parent.scan_stats['processed_files']} of {parent.scan_stats['total_files']}")
                    parent.progress_value.set(progress * 100)

                    # Update stats display
                    from .gui_scanner import update_scan_stats
                    update_scan_stats(parent)

            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                parent.scan_stats["error_count"] += 1

        # Start scanning the source directory
        logger.info(f"Starting scan of {source_dir}")

        # Get total file count first (rough estimate)
        file_count = 0
        for _ in parent.scanner.scan_directory(source_dir, recursive=True):
            file_count += 1
        parent.scan_stats["total_files"] = file_count

        # Start actual processing
        parent.scanner.start_scan(source_dir, process_file, recursive=True)

        # Wait for scan to complete or be stopped
        while parent.scanner.scan_thread and parent.scanner.scan_thread.is_alive():
            if stop_event.is_set():
                parent.scanner.stop_scan()
                break
            time.sleep(0.1)

        # Final update
        parent.scan_stats["end_time"] = datetime.now()
        from .gui_scanner import update_scan_stats
        update_scan_stats(parent)

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
