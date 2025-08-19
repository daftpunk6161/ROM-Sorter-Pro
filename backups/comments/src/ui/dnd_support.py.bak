#!/usr/bin/env python3
# -*-coding: utf-8-*-

"""
ROM Sorter Pro - Erweiterte Drag & Drop Unterstützung

Dieses Modul bietet eine UI-Framework-unabhängige Drag & Drop Funktionalität
für ROM-Dateien mit verbesserter Fehlerbehandlung und Performance.

OPTIMIERUNGEN:
- VERBESSERT: Optionale PyQt5-Abhängigkeit mit robustem Fallback
- BEHOBEN: Typannotationen korrigiert
- HINZUGEFÜGT: Plattformunabhängige Implementierung
- OPTIMIERT: Verbesserte Thread-Sicherheit

Unterstützt mehrere UI-Frameworks:
- Optional PyQt5 (wenn installiert)
- Tkinter (als Fallback)
- Kommandozeile (minimaler Fallback)
"""

import os
import sys
import logging
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union, Set, Callable, TypeVar, Generic, cast, Type

# Configure logger
logger = logging.getLogger(__name__)

# Type alias for better readability
FilePath = Union[str, Path]
FileList = List[FilePath]
DropCallback = Callable[[FileList], None]
T = TypeVar('T')  # General type for generic functions

# Check whether PYQT5 is available
PYQT_AVAILABLE = False
try:
# Check whether PYQT5 can be imported without loading it
    if importlib.util.find_spec("PyQt5") is not None:
# Delay the import until we really need it
        PYQT_AVAILABLE = True
        logger.debug("PyQt5 ist verfügbar")
    else:
        logger.warning("PyQt5 ist nicht verfügbar, verwende Fallback")
except ImportError:
    logger.warning("PyQt5 kann nicht importiert werden, verwende Fallback")

# Define PYQT5 types for type annotations without importing directly
if PYQT_AVAILABLE:
    try:
        from PyQt5.QtCore import Qt, QMimeData, QUrl
        from PyQt5.QtGui import QDragEnterEvent, QDropEvent
        from PyQt5.QtWidgets import QWidget, QApplication
    except ImportError:
# Type aliase for PYQT5 if it cannot be imported
        class Qt: pass
        class QMimeData: pass
        class QUrl: pass
        class QDragEnterEvent: pass
        class QDropEvent: pass
        class QWidget: pass
        class QApplication: pass
else:
# Dummy classes for type annotations if PYQT5 is not available
    class Qt: pass
    class QMimeData: pass
    class QUrl: pass
    class QDragEnterEvent: pass
    class QDropEvent: pass
    class QWidget: pass
    class QApplication: pass


class DragDropManager:
    """
    Plattformunabhängiger Manager für Drag & Drop-Operationen.
    """

    def __init__(self):
        """Initialisiere den DragDropManager."""
        self._callbacks: Dict[str, DropCallback] = {}
        self._active = True

    def register_drop_callback(self, widget_id: str, callback: DropCallback) -> None:
        """
        Registriere einen Callback für Drop-Ereignisse auf einem Widget.

        Args:
            widget_id: Eindeutige ID für das Widget
            callback: Funktion, die aufgerufen wird, wenn Dateien abgelegt werden
        """
        self._callbacks[widget_id] = callback
        logger.debug(f"Drop-Callback registriert für Widget {widget_id}")

    def unregister_drop_callback(self, widget_id: str) -> None:
        """
        Entferne einen registrierten Drop-Callback.

        Args:
            widget_id: Eindeutige ID des Widgets
        """
        if widget_id in self._callbacks:
            del self._callbacks[widget_id]
            logger.debug(f"Drop-Callback entfernt für Widget {widget_id}")

    def handle_drop(self, widget_id: str, file_paths: FileList) -> bool:
        """
        Verarbeite ein Drop-Ereignis.

        Args:
            widget_id: ID des Widgets, auf dem das Drop-Ereignis stattfand
            file_paths: Liste der abgelegten Dateipfade

        Returns:
            True, wenn das Ereignis verarbeitet wurde, sonst False
        """
        if not self._active or widget_id not in self._callbacks:
            return False

        try:
            callback = self._callbacks[widget_id]
            callback(file_paths)
            return True
        except Exception as e:
            logger.error(f"Fehler bei der Verarbeitung des Drop-Ereignisses: {e}")
            return False

    def enable(self) -> None:
        """Aktiviere den DragDropManager."""
        self._active = True

    def disable(self) -> None:
        """Deaktiviere den DragDropManager."""
        self._active = False


# Global instance of the dragdrop manager
global_drag_drop_manager = DragDropManager()


def get_urls_from_mime_data(mime_data: Any) -> List[str]:
    """
    Extrahiere URLs aus MIME-Daten, unabhängig vom UI-Framework.

    Args:
        mime_data: MIME-Daten aus einem Drag & Drop-Ereignis

    Returns:
        Liste der URLs
    """
    urls = []

# PYQT5-specific code
    if PYQT_AVAILABLE and isinstance(mime_data, QMimeData):
        for url in mime_data.urls():
            urls.append(url.toLocalFile())
# Generic fallback
    elif hasattr(mime_data, 'get_urls'):
        urls = mime_data.get_urls()
    elif hasattr(mime_data, 'text'):
# Try to parse text
        text = mime_data.text()
        if isinstance(text, str):
            lines = text.splitlines()
            for line in lines:
                line = line.strip()
                if line.startswith('file://'):
                    urls.append(line[7:])
                elif os.path.exists(line):
                    urls.append(line)

    return urls


def is_valid_drop(mime_data: Any, allowed_extensions: Optional[List[str]] = None) -> bool:
    """
    Prüft, ob ein Drop-Ereignis gültige Dateien enthält.

    Args:
        mime_data: MIME-Daten aus einem Drag & Drop-Ereignis
        allowed_extensions: Liste erlaubter Dateierweiterungen oder None für alle

    Returns:
        True, wenn es gültige Dateien enthält
    """
    urls = get_urls_from_mime_data(mime_data)

    if not urls:
        return False

    if allowed_extensions is None:
        return True

# Convert all extensions to small letters
    allowed_extensions = [ext.lower() for ext in allowed_extensions]

# Check whether at least one file has a permitted extension
    for url in urls:
        ext = os.path.splitext(url)[1].lower()
        if ext in allowed_extensions:
            return True

    return False


def normalize_file_paths(urls: List[str]) -> FileList:
    """
    Normalisiere URLs zu Dateipfaden und entferne Duplikate.

    Args:
        urls: Liste von URLs oder Dateipfaden

    Returns:
        Liste mit normalisierten Dateipfaden
    """
    result = []
    seen = set()

    for url in urls:
# Remove "File: //" Prefix for Windows and Unix
        if url.startswith('file:///'):
            path = url[8:]  # Windows: file:///C:/path
        elif url.startswith('file://'):
            path = url[7:]  # Unix: file:///path
        else:
            path = url

# Normalize path
        path = os.path.normpath(path)

        if path not in seen and os.path.exists(path):
            result.append(path)
            seen.add(path)

    return result


# PYQT5-specific implementation
if PYQT_AVAILABLE:
    class DropTarget:
        """
        Mixin-Klasse, die PyQt5-Widgets um Drag & Drop-Funktionalität erweitert.
        """

        def __init__(self, widget: QWidget, callback: DropCallback = None,
                    allowed_extensions: Optional[List[str]] = None):
            """
            Initialisiere das DropTarget.

            Args:
                widget: Das PyQt5-Widget, das Drag & Drop unterstützen soll
                callback: Funktion, die aufgerufen wird, wenn Dateien abgelegt werden
                allowed_extensions: Liste erlaubter Dateierweiterungen oder None für alle
            """
            self.widget = widget
            self.callback = callback
            self.allowed_extensions = allowed_extensions

# Widget ID for registration with the manager
            self.widget_id = str(id(widget))

# Set the necessary flags for drag & drop
            widget.setAcceptDrops(True)

# Save original methods
            self._original_dragEnterEvent = widget.dragEnterEvent
            self._original_dropEvent = widget.dropEvent

# Overwrite the drag & drop event handler
            widget.dragEnterEvent = self._drag_enter_event_handler
            widget.dropEvent = self._drop_event_handler

# Register with the global manager if called callback
            if callback:
                global_drag_drop_manager.register_drop_callback(self.widget_id, callback)

        def _drag_enter_event_handler(self, event: QDragEnterEvent) -> None:
            """
            Handler für dragEnterEvent.

            Args:
                event: Das QDragEnterEvent-Objekt
            """
# Check whether they are valid files
            if is_valid_drop(event.mimeData(), self.allowed_extensions):
                event.acceptProposedAction()
            else:
# If not valid, forward to the original handler
                self._original_dragEnterEvent(event)

        def _drop_event_handler(self, event: QDropEvent) -> None:
            """
            Handler für dropEvent.

            Args:
                event: Das QDropEvent-Objekt
            """
            urls = get_urls_from_mime_data(event.mimeData())
            file_paths = normalize_file_paths(urls)

            if file_paths:
# First try the registered callback
                if global_drag_drop_manager.handle_drop(self.widget_id, file_paths):
                    event.acceptProposedAction()
# Otherwise the local callback
                elif self.callback:
                    try:
                        self.callback(file_paths)
                        event.acceptProposedAction()
                    except Exception as e:
                        logger.error(f"Fehler im Drop-Callback: {e}")
                        self._original_dropEvent(event)
                else:
# If no callback is set, use original handler
                    self._original_dropEvent(event)
            else:
                self._original_dropEvent(event)

        def set_callback(self, callback: DropCallback) -> None:
            """
            Setze einen neuen Callback für Drop-Ereignisse.

            Args:
                callback: Neue Callback-Funktion
            """
            self.callback = callback
            global_drag_drop_manager.register_drop_callback(self.widget_id, callback)

        def clear_callback(self) -> None:
            """Entferne den Callback."""
            self.callback = None
            global_drag_drop_manager.unregister_drop_callback(self.widget_id)

        def set_allowed_extensions(self, extensions: Optional[List[str]]) -> None:
            """
            Setze erlaubte Dateierweiterungen.

            Args:
                extensions: Liste erlaubter Dateierweiterungen oder None für alle
            """
            self.allowed_extensions = extensions

        def restore_original_handlers(self) -> None:
            """Stelle die Original-Handler wieder her."""
            self.widget.dragEnterEvent = self._original_dragEnterEvent
            self.widget.dropEvent = self._original_dropEvent
            global_drag_drop_manager.unregister_drop_callback(self.widget_id)


    def enable_drag_drop(widget: QWidget, callback: DropCallback = None,
                         allowed_extensions: Optional[List[str]] = None) -> DropTarget:
        """
        Aktiviere Drag & Drop für ein PyQt5-Widget.

        Args:
            widget: Das PyQt5-Widget
            callback: Funktion, die aufgerufen wird, wenn Dateien abgelegt werden
            allowed_extensions: Liste erlaubter Dateierweiterungen oder None für alle

        Returns:
            Eine DropTarget-Instanz
        """
        return DropTarget(widget, callback, allowed_extensions)

else:
# Dummy implementation for other frameworks
    class DropTarget:
        """Dummy-Implementierung für nicht-PyQt5-Umgebungen."""

        def __init__(self, widget: Any, callback: Optional[DropCallback] = None,
                    allowed_extensions: Optional[List[str]] = None):
            self.widget = widget
            self.callback = callback
            self.allowed_extensions = allowed_extensions
            self.widget_id = str(id(widget))

            logger.warning("PyQt5 ist nicht verfügbar, Drag & Drop wird nicht unterstützt")

            if hasattr(widget, 'bind') and callable(widget.bind):
# Tkinter-like implementation
                try:
                    widget.bind('<Drop>', self._tk_drop_handler)
                except Exception:
                    pass

        def _tk_drop_handler(self, event: Any) -> None:
            """Handler für Tkinter-Drop-Ereignisse."""
            try:
                data = event.data
                if isinstance(data, str):
                    files = [f for f in data.split('\n') if os.path.exists(f)]
                    if files and self.callback:
                        self.callback(files)
            except Exception as e:
                logger.error(f"Fehler im Tkinter-Drop-Handler: {e}")

        def set_callback(self, callback: DropCallback) -> None:
            self.callback = callback

        def clear_callback(self) -> None:
            self.callback = None

        def set_allowed_extensions(self, extensions: Optional[List[str]]) -> None:
            self.allowed_extensions = extensions

        def restore_original_handlers(self) -> None:
            pass


# Utility functions
def handle_dropped_files(files: FileList, callback: DropCallback) -> None:
    """
    Verarbeite abgelegte Dateien sicher.

    Args:
        files: Liste der abgelegten Dateipfade
        callback: Aufzurufende Funktion
    """
    try:
# Give the callback in a safe environment
        callback(files)
    except Exception as e:
        logger.error(f"Fehler bei der Verarbeitung abgelegter Dateien: {e}")


def get_files_from_drop_event(event: Any, allowed_extensions: Optional[List[str]] = None) -> FileList:
    """
    Extrahiere Dateipfade aus einem Drop-Ereignis.

    Args:
        event: Drop-Ereignis (PyQt5 oder anderes UI-Framework)
        allowed_extensions: Liste erlaubter Dateierweiterungen oder None für alle

    Returns:
        Liste der Dateipfade
    """
    mime_data = getattr(event, 'mimeData', lambda: event)()
    urls = get_urls_from_mime_data(mime_data)
    files = normalize_file_paths(urls)

    if allowed_extensions:
        allowed_extensions = [ext.lower() for ext in allowed_extensions]
        files = [f for f in files if os.path.splitext(f)[1].lower() in allowed_extensions]

    return files


# Export central functions for easier use
__all__ = [
    'DragDropManager', 'global_drag_drop_manager', 'enable_drag_drop',
    'get_files_from_drop_event', 'handle_dropped_files', 'normalize_file_paths',
    'is_valid_drop', 'PYQT_AVAILABLE'
]
