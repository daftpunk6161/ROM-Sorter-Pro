"""
ROM Sorter Pro - Integrierte Drag & Drop Unterstützung

Dieses Modul kombiniert die verschiedenen Drag & Drop Implementierungen
und bietet eine einheitliche Schnittstelle für alle UI-Komponenten.
Es dient als Vermittler zwischen der Legacy-DND-Unterstützung und
der neuen, verbesserten DND-Funktionalität.
"""

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
    """
    Integrierte Drag & Drop Unterstützung, die beide DND-Systeme verwendet.
    """

    def __init__(self, widget: tk.Widget, callback: Optional[Callable[[List[str]], None]] = None):
        """
        Initialisiert die integrierte DND-Unterstützung.

        Args:
            widget: Das Widget, das DND unterstützen soll
            callback: Funktion, die bei Drop-Events aufgerufen wird
        """
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
        """
        Handler für TkinterDnD2 Drop-Events.
        """
        try:
            data = event.data
            if data:
                # Convert the data into a list of file paths
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
        """
        Handler für Drop-Events vom DragDropManager.
        """
        if self.callback:
            try:
                # Convert all paths to strings
                file_paths = [str(path) for path in files]
                self.callback(file_paths)
                logger.debug(f"DragDropManager Drop-Event für {len(files)} Dateien verarbeitet")
            except Exception as e:
                logger.error(f"Fehler bei der Verarbeitung des DragDropManager Drop-Events: {e}")

    def set_callback(self, callback: Callable[[List[str]], None]) -> None:
        """
        Setzt einen neuen Callback für Drop-Events.

        Args:
            callback: Die neue Callback-Funktion
        """
        self.callback = callback
        _global_dnd_manager.register_drop_callback(self.widget_id, self._on_files_dropped)

    def enable(self) -> None:
        """Aktiviert die DND-Unterstützung."""
        if TKDND_AVAILABLE and hasattr(self.widget, 'drop_target_register'):
            try:
                self.widget.drop_target_register('*')
            except Exception:
                pass

    def disable(self) -> None:
        """Deaktiviert die DND-Unterstützung."""
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
    """
    Erstellt ein Drop-Target-Widget, das beide DND-Systeme unterstützt.

    Args:
        parent: Das übergeordnete Widget
        callback: Funktion, die bei Drop-Events aufgerufen wird
        **kwargs: Zusätzliche Parameter für das Frame-Widget

    Returns:
        Ein Frame mit DND-Unterstützung
    """
    if TKDND_AVAILABLE:
        # Use the optimized version with Tkinterdnd2
        frame = OptimizedDragDropFrame(parent, callback=callback, **kwargs)
    else:
        # Fallback for simple version with our own DND support
        frame = tk.Frame(parent, **kwargs)
        IntegratedDnDSupport(frame, callback)

    return frame


def add_drop_support(widget: tk.Widget, callback: Callable[[List[str]], None]) -> IntegratedDnDSupport:
    """
    Fügt einem Widget DND-Unterstützung hinzu.

    Args:
        widget: Das Widget, das DND unterstützen soll
        callback: Funktion, die bei Drop-Events aufgerufen wird

    Returns:
        IntegratedDnDSupport-Objekt
    """
    return IntegratedDnDSupport(widget, callback)


def get_dnd_manager() -> DragDropManager:
    """
    Gibt den globalen DND-Manager zurück.

    Returns:
        DragDropManager-Instanz
    """
    return _global_dnd_manager
