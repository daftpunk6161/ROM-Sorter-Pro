"""Rom Sarter Pro - Integrated Drag & Drop Support This module Combines the Various Drag & Drop Implementation and Offers A Uniform Interface for All Ui Components. It serves as an intermediary the legacy dnd support and the new, impovered dnd functionality."""

import os
import logging
import tkinter as tk
from pathlib import Path
from typing import List, Union, Callable, Optional, Dict, Any

# Logger konfigurieren
logger = logging.getLogger(__name__)

# Importiere Legacy-DND-Unterstuetzung
from .gui_dnd import DND_AVAILABLE as TKDND_AVAILABLE, OptimizedDragDropFrame
from ..dnd_support import DragDropManager, FilePath, FileList, DropCallback

# Central DND manager for the entire application
_global_dnd_manager = DragDropManager()

# Status of the DND support
DND_AVAILABLE = TKDND_AVAILABLE
DND_MANAGER_AVAILABLE = True  # Always available because we have our own implementation


class IntegratedDnDSupport:
    """Integrated drag & drop support that both DND systems used."""

    def __init__(self, widget: tk.Widget, callback: Optional[Callable[[List[str]], None]] = None):
        """Initialized the integrated DND support. Args: Widget: The widget that is supposed to support DND Callback: Function that is called at drop events"""
        self.widget = widget
        self.callback = callback
        self.widget_id = str(id(widget))

        # Registriere beim globalen DND-Manager
        if callback:
            _global_dnd_manager.register_drop_callback(self.widget_id, self._on_files_dropped)

        # Tkinterdnd2 support, if available
        if TKDND_AVAILABLE and hasattr(widget, 'drop_target_register'):
            try:
                widget.drop_target_register('*')
                widget.dnd_bind('<<Drop>>', self._on_tk_drop)
                logger.debug(f"TkinterDnD2 Unterstützung für Widget {self.widget_id} aktiviert")
            except Exception as e:
                logger.warning(f"Fehler bei der TkinterDnD2-Initialisierung: {e}")

    def _on_tk_drop(self, event) -> None:
        """Handler for Tkinterdnd2 Drop events."""
        try:
            data = event.data
            if data:
                # Convert the Data Into a List of File Paths
                if data.startswith('{') and data.endswith('}'):
                    # Mehrere Dateien im Format {file1} {file2}
                    files = []
                    for item in data.strip('{}').split('} {'):
                        files.append(item)
                else:
                    # Einzelne Datei
                    files = [data]

                # Rufe den Callback auf
                if self.callback:
                    self.callback(files)
                    logger.debug(f"TkinterDnD2 Drop-Event für {len(files)} Dateien verarbeitet")
        except Exception as e:
            logger.error(f"Fehler bei der Verarbeitung des TkinterDnD2 Drop-Events: {e}")

    def _on_files_dropped(self, files: List[FilePath]) -> None:
        """Handler for drop events from the dragdrop manager."""
        if self.callback:
            try:
                # Convert all paths to strings
                file_paths = [str(path) for path in files]
                self.callback(file_paths)
                logger.debug(f"DragDropManager Drop-Event für {len(files)} Dateien verarbeitet")
            except Exception as e:
                logger.error(f"Fehler bei der Verarbeitung des DragDropManager Drop-Events: {e}")

    def set_callback(self, callback: Callable[[List[str]], None]) -> None:
        """Set A New Callback for Drop Events. Args: Callback: The New Callback Function"""
        self.callback = callback
        _global_dnd_manager.register_drop_callback(self.widget_id, self._on_files_dropped)

    def enable(self) -> None:
        """Activates the DND support."""
        if TKDND_AVAILABLE and hasattr(self.widget, 'drop_target_register'):
            try:
                self.widget.drop_target_register('*')
            except Exception:
                pass

    def disable(self) -> None:
        """Deactivates the DND support."""
        if TKDND_AVAILABLE and hasattr(self.widget, 'drop_target_unregister'):
            try:
                self.widget.drop_target_unregister()
            except Exception:
                pass

        # Entferne Callback vom globalen Manager
        _global_dnd_manager.unregister_drop_callback(self.widget_id)

    def __del__(self):
        """Cleanup beim Entfernen des Objekts."""
        try:
            self.disable()
        except Exception:
            pass


def create_drop_target(parent: tk.Widget, callback: Callable[[List[str]], None],
                      **kwargs) -> Union[tk.Frame, OptimizedDragDropFrame]:
    """Creates a drop-type widget that supports both dnd systems. Args: Parent: The Overarching Widget Callback: Function that is called at drop events ** Kwargs: Additional Parameters for the Frame Widget Return: A frame with dnd support"""
    if TKDND_AVAILABLE:
        # Use the optimized version with Tkinterdnd2
        frame = OptimizedDragDropFrame(parent, callback=callback, **kwargs)
    else:
        # Fallback for simple version with our own DND support
        frame = tk.Frame(parent, **kwargs)
        IntegratedDnDSupport(frame, callback)

    return frame


def add_drop_support(widget: tk.Widget, callback: Callable[[List[str]], None]) -> IntegratedDnDSupport:
    """Adds to a widget dnd support. ARGS: Widget: The Widget that is supposed to support dnd callback: Function that is called at drop events return: Integratedddddddddddddddddddddddddddddddddddddort Object"""
    return IntegratedDnDSupport(widget, callback)


def get_dnd_manager() -> DragDropManager:
    """Gives back the global DND manager. Return: Dragdrop Manager instance"""
    return _global_dnd_manager
