#!/usr/bin/env python3
"""
ROM Sorter Pro - GUI Drag and Drop Module

This module contains drag and drop functionality for the ROM Sorter Pro GUI.
"""

import logging
import os
import tkinter as tk
from pathlib import Path
from typing import List, Union, Callable

logger = logging.getLogger(__name__)

# Try to import the drag and drop dependencies
try:
    import tkinterdnd2
    DND_AVAILABLE = True
except ImportError:
    logger.warning("TkinterDnD2 not available. Drag and drop functionality will be disabled.")
    DND_AVAILABLE = False


def setup_dnd_support(parent):
    """Set up drag and drop support for the GUI.

    Args:
        parent: Parent GUI instance
    """
    if not DND_AVAILABLE:
        logger.warning("Drag and drop support is not available.")
        update_drop_zone_status(parent, enabled=False)
        return

    try:
        # Initialize TkinterDnD
        parent.tk.call('package', 'require', 'tkdnd')

        # Register the drop zone
        drop_zone = parent.components.get("drop_zone")
        if drop_zone:
            drop_zone.drop_target_register("*")
            drop_zone.dnd_bind("<<Drop>>", lambda e: on_drop(parent, e))

            # Update visual cues
            drop_zone.bind("<Enter>", lambda e: on_drag_enter(parent, e))
            drop_zone.bind("<Leave>", lambda e: on_drag_leave(parent, e))

        logger.info("Drag and drop support initialized")
        update_drop_zone_status(parent, enabled=True)

    except Exception as e:
        logger.error(f"Failed to initialize drag and drop support: {e}")
        update_drop_zone_status(parent, enabled=False)


def update_drop_zone_status(parent, enabled=True):
    """Update the drop zone appearance based on DnD availability.

    Args:
        parent: Parent GUI instance
        enabled: Whether DnD is enabled
    """
    drop_zone = parent.components.get("drop_zone")
    main_label = parent.components.get("drop_zone_main_label")
    sub_label = parent.components.get("drop_zone_sub_label")

    if not drop_zone or not main_label or not sub_label:
        return

    if enabled:
        main_label.config(text="Drop ROM Files Here")
        sub_label.config(text="or click to select files")
    else:
        main_label.config(text="Select ROM Files")
        sub_label.config(text="Drag and drop not available")


def on_drop(parent, event):
    """Handle drop events.

    Args:
        parent: Parent GUI instance
        event: Drop event
    """
    # Extract file paths from the drop data
    try:
        data = event.data
        paths = extract_paths_from_drop_data(data)

        if paths:
            parent.status_text.set(f"Dropped {len(paths)} file(s)")
            logger.info(f"Dropped {len(paths)} files")

            # Process the dropped files
            process_dropped_files(parent, paths)
        else:
            parent.status_text.set("No valid files found in drop")
            logger.warning("No valid files found in drop")

    except Exception as e:
        parent.status_text.set(f"Error processing dropped files: {e}")
        logger.error(f"Error in drop handler: {e}")


def on_drag_enter(parent, event):
    """Handle drag enter events.

    Args:
        parent: Parent GUI instance
        event: Event object
    """
    drop_zone = parent.components.get("drop_zone")
    if drop_zone:
        drop_zone.config(bg="#e0e0ff")  # Light blue background


def on_drag_leave(parent, event):
    """Handle drag leave events.

    Args:
        parent: Parent GUI instance
        event: Event object
    """
    drop_zone = parent.components.get("drop_zone")
    if drop_zone:
        drop_zone.config(bg="#f0f0f0")  # Restore original background


def extract_paths_from_drop_data(data: str) -> List[Path]:
    """Extract file and directory paths from drop data.

    Args:
        data: Drop data string

    Returns:
        List[Path]: List of paths
    """
    paths = []

    # Process drop data - this varies by platform
    if data.startswith("{"):
        # Windows format
        items = data.split("} {")
        for item in items:
            item = item.strip("{}")
            if os.path.exists(item):
                paths.append(Path(item))
    else:
        # Unix format
        items = data.split()
        for item in items:
            # Handle URL format (file://)
            if item.startswith("file://"):
                item = item[7:]  # Remove the file:// prefix

            # Decode URL encoding if needed (e.g. %20 for spaces)
            try:
                from urllib.parse import unquote
                item = unquote(item)
            except ImportError:
                pass

            if os.path.exists(item):
                paths.append(Path(item))

    return paths


def process_dropped_files(parent, paths: List[Path]):
    """Process the dropped files.

    Args:
        parent: Parent GUI instance
        paths: List of file paths
    """
    # Count files by type
    file_types = {}
    for path in paths:
        if path.is_file():
            ext = path.suffix.lower()
            file_types[ext] = file_types.get(ext, 0) + 1

    # Update statistics
    parent.scan_stats["total_files"] += len(paths)
    for ext, count in file_types.items():
        parent.scan_stats["file_types"][ext] = parent.scan_stats["file_types"].get(ext, 0) + count

    # Log the file types
    for ext, count in file_types.items():
        logger.info(f"Found {count} {ext} files")

    # Enable buttons if files were dropped
    if "start_button" in parent.components:
        parent.components["start_button"].config(state=tk.NORMAL)
