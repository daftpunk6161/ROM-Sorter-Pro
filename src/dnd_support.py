"""
Native Drag & Drop Support für ROM Sorter
-----------------------------------------

Dieses Modul implementiert eine betriebssystemübergreifende Drag & Drop-Unterstützung
für Tkinter ohne externe Abhängigkeiten. Auf Windows wird die Win32-API über ctypes verwendet,
während auf anderen Betriebssystemen alternative Mechanismen eingesetzt werden.
"""

import os
import sys
import tkinter as tk
import platform
import logging
import ctypes
import weakref
import time
from typing import Callable, List, Optional, Union, Any, Set, Dict
from ctypes import POINTER, byref, c_char_p, c_uint, c_void_p, c_wchar_p, create_unicode_buffer
from ctypes.wintypes import BOOL, DWORD, HWND, LPARAM, LPCWSTR, POINT, RECT

# Logger Setup
logger = logging.getLogger(__name__)

# Operating system-specific implementations
WINDOWS = platform.system() == "Windows"
MACOS = platform.system() == "Darwin"
LINUX = platform.system() == "Linux"

# Status of the drag & drop support
DND_AVAILABLE = False
DND_MODE = "none"  # "native", "tkdnd", "none"

# Global variables for drag & drop condition
_active_drop_target = None
_drop_callbacks = {}


def enable_native_dnd() -> bool:
    """
    Aktiviert die native Drag & Drop-Unterstützung für das aktuelle Betriebssystem.

    Returns:
        bool: True, wenn die Unterstützung aktiviert werden konnte, sonst False
    """
    global DND_AVAILABLE, DND_MODE

    try:
        if WINDOWS:
# Windows-specific implementation
            success = _setup_windows_dnd()
            if success:
                logger.info("Native Windows Drag & Drop-Unterstützung aktiviert")
                DND_AVAILABLE = True
                DND_MODE = "native"
                return True

# Fallback on Tkinterdnd2, if available
        if _setup_tkinterdnd():
            logger.info("TkinterDnD Drag & Drop-Unterstützung aktiviert")
            DND_AVAILABLE = True
            DND_MODE = "tkdnd"
            return True

# No drag & drop available
        logger.warning("Keine Drag & Drop-Unterstützung verfügbar")
        DND_AVAILABLE = False
        DND_MODE = "none"
        return False

    except Exception as e:
        logger.error(f"Fehler beim Aktivieren von Drag & Drop: {e}")
        DND_AVAILABLE = False
        DND_MODE = "none"
        return False


# Windows-specific constants and functions
if WINDOWS:
# Define Windows constants
    WM_DROPFILES = 0x0233

# Import functions from shell32.dll
    try:
        _shell32 = ctypes.windll.shell32
        _DragAcceptFiles = _shell32.DragAcceptFiles
        _DragFinish = _shell32.DragFinish
        _DragQueryFileW = _shell32.DragQueryFileW
        _DragQueryPoint = _shell32.DragQueryPoint

# Set functional prototypes
        _DragAcceptFiles.argtypes = [HWND, BOOL]
        _DragFinish.argtypes = [HWND]
        _DragQueryFileW.argtypes = [HWND, DWORD, LPCWSTR, DWORD]
        _DragQueryFileW.restype = DWORD
        _DragQueryPoint.argtypes = [HWND, POINTER(POINT)]
        _DragQueryPoint.restype = BOOL
    except Exception as e:
        logger.error(f"Fehler beim Laden der Windows DnD-Funktionen: {e}")
        WM_DROPFILES = None
        _DragAcceptFiles = None
        _DragFinish = None
        _DragQueryFileW = None
        _DragQueryPoint = None

def _setup_windows_dnd() -> bool:
    """
    Richtet Windows-spezifische Drag & Drop-Funktionalität ein.

    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    if not WINDOWS:
        return False

    try:
        if (WM_DROPFILES is not None and
            _DragAcceptFiles is not None and
            _DragFinish is not None and
            _DragQueryFileW is not None and
            _DragQueryPoint is not None):

            logger.info("Windows Drag & Drop-Funktionen erfolgreich geladen")
            return True
        else:
            logger.error("Windows Drag & Drop-Funktionen konnten nicht geladen werden")
            return False

    except Exception as e:
        logger.error(f"Fehler beim Einrichten der Windows Drag & Drop-Unterstützung: {e}")
        import traceback
        traceback.print_exc()
        return False


# Tkinterdnd import and reference
TkinterDnD = None
DND_FILES = None

def _setup_tkinterdnd() -> bool:
    """
    Versucht, tkinterdnd2 zu importieren und zu initialisieren.

    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    global TkinterDnD, DND_FILES

    try:
# Try to import tkinterdnd2
        from tkinterdnd2 import TkinterDnD, DND_FILES

# Register global
        globals()['TkinterDnD'] = TkinterDnD
        globals()['DND_FILES'] = DND_FILES

        logger.info("TkinterDnD erfolgreich importiert")
        return True

    except ImportError:
        logger.warning("TkinterDnD nicht verfügbar")
        return False
    except Exception as e:
        logger.error(f"Fehler bei TkinterDnD-Setup: {e}")
        return False


class DragDropMixin:
    """Mixin-Klasse, die Drag & Drop-Funktionalität zu Tkinter-Widgets hinzufügt."""

    def __init__(self, *args, **kwargs):
# Make sure that this method is not called without a parent class
        if not hasattr(self, 'winfo_id'):
            raise TypeError("DragDropMixin muss mit einer Tkinter-Widget-Klasse verwendet werden")

# Save drop callback
        self._drop_callback = None
        self._drop_enter_callback = None
        self._drop_leave_callback = None
        self._callbacks = set()

    def register_drop_target(self, callback: Callable[[List[str]], None]) -> bool:
        """
        Registriert dieses Widget als Drop-Ziel für Dateien.

        Args:
            callback: Funktion, die mit einer Liste von Dateipfaden aufgerufen wird, wenn Dateien gedroppt werden

        Returns:
            bool: True, wenn die Registrierung erfolgreich war, sonst False
        """
        global _drop_callbacks

        try:
            if not DND_AVAILABLE:
                logger.warning("Drag & Drop ist nicht verfügbar")
                return False

            self._drop_callback = callback
            widget_id = str(self.winfo_id())
            _drop_callbacks[widget_id] = callback

# For the DirectWindows handler
            self._callbacks.add(callback)

            if DND_MODE == "native":
                if WINDOWS:
                    return self._register_windows_drop_target()
            elif DND_MODE == "tkdnd":
                return self._register_tkdnd_drop_target()

            return False
        except Exception as e:
            logger.error(f"Fehler bei der Registrierung als Drop-Ziel: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _register_windows_drop_target(self) -> bool:
        """Registriert das Widget als Drop-Ziel unter Windows."""
        try:
# Set a flag to prevent the widget from being registered twice
            if hasattr(self, '_drop_target_registered') and self._drop_target_registered:
                logger.warning(f"Widget {self.winfo_id()} ist bereits als Drop-Target registriert")
                return True

# Check whether the widget is a top level window
            is_toplevel = False
            try:
# A top level window can interact with World Cup
                self.tk.call('wm', 'title', self._w)
                is_toplevel = True
            except:
# Non-top level widgets throw a mistake
                pass

            if is_toplevel:
# Top level windows can be registered directly as a drop target
                hwnd = self.winfo_id()
                _DragAcceptFiles(hwnd, True)

# Overwrite the tkinter event treatment for WM_Dropfiles
                old_window_proc = self.tk.call('winfo', 'toplevel', self._w)

                def _window_proc(hwnd, message, wparam, lparam):
                    if message == WM_DROPFILES:
                        self._handle_windows_drop(wparam)
                        return 0
                    return old_window_proc(hwnd, message, wparam, lparam)

                self.tk.call('wm', 'protocol', self._w, 'WM_DROPFILES', _window_proc)

                logger.info(f"Windows Drop-Target erfolgreich registriert für Top-Level-Widget {self.winfo_id()}")
                self._drop_target_registered = True
                return True
            else:
# For non-top level widgets we have to use the overarching window
                try:
# Find the overarching top level window
                    toplevel = self.winfo_toplevel()

# Register the top level window as a drop-down star
                    hwnd = toplevel.winfo_id()
                    _DragAcceptFiles(hwnd, True)

# Save a reference to the current widget at the top level
                    if not hasattr(toplevel, '_dnd_widgets'):
                        toplevel._dnd_widgets = {}

                    toplevel._dnd_widgets[str(id(self))] = weakref.ref(self)

# If the top level window does not yet have a drop handler
                    if not hasattr(toplevel, '_drop_handler_installed'):
# Overwrite the tkinter event treatment for WM_Dropfiles
                        def _toplevel_drop_handler(hwnd, message, wparam, lparam):
                            if message == WM_DROPFILES:
# Call up all registered widget handler
                                file_paths = _extract_drop_file_paths(wparam)
                                _DragFinish(wparam)

# Get a mouse position in the drop
                                point = POINT()
                                _DragQueryPoint(wparam, ctypes.byref(point))

# Find the widget under the mouse pointer
                                x, y = point.x, point.y

# Call up every handler
                                for widget_ref in toplevel._dnd_widgets.values():
                                    widget = widget_ref()
                                    if widget:
                                        try:
# Convert the coordinates
                                            widget_x = widget.winfo_rootx() - toplevel.winfo_rootx()
                                            widget_y = widget.winfo_rooty() - toplevel.winfo_rooty()
                                            widget_width = widget.winfo_width()
                                            widget_height = widget.winfo_height()

# Check whether the drop was within the widget
                                            if (widget_x <= x <= widget_x + widget_width and
                                                    widget_y <= y <= widget_y + widget_height):

# Call up the widget handler - but only once!
# Save the edited event flag
                                                if not hasattr(toplevel, '_last_drop_handled'):
                                                    toplevel._last_drop_handled = 0

# Prevent double events within a short time
                                                current_time = int(time.time() * 1000)  # Millisekunden
                                                if (current_time - toplevel._last_drop_handled) < 500:  # 500ms Schutz
                                                    logger.warning("Doppeltes Drop-Event erkannt, wird ignoriert")
                                                    break

# Marking event as edited
                                                toplevel._last_drop_handled = current_time

# Callback calls
                                                for callback in widget._callbacks:
                                                    callback(file_paths)
                                                break
                                        except Exception as handler_err:
                                            logger.error(f"Fehler im Drop-Handler: {handler_err}")

                                return 0

# Standard treatment for all other news
                            return toplevel._original_window_proc(hwnd, message, wparam, lparam)

# Install the handler
                        toplevel._drop_handler_installed = True
                        toplevel._original_window_proc = toplevel.tk.call('winfo', 'toplevel', toplevel._w)
                        toplevel.tk.call('wm', 'protocol', toplevel._w, 'WM_DROPFILES', _toplevel_drop_handler)

                    logger.info(f"Windows Drop-Target erfolgreich registriert für Widget über Top-Level-Fenster")
                    self._drop_target_registered = True
                    return True

                except Exception as toplevel_err:
                    logger.error(f"Fehler bei der Registrierung über Top-Level: {toplevel_err}")
                    return False
        except Exception as e:
            logger.error(f"Fehler bei Windows Drop-Target-Registrierung: {e}")
            import traceback
            traceback.print_exc()
            return False

def _extract_drop_file_paths(hdrop) -> List[str]:
    """Extrahiert Dateipfade aus einem Windows-Drop-Handle."""
    try:
# Determine the number of dropped files
        file_count = _DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
        paths = []

# Extract all file paths
        for i in range(file_count):
# Two runs: first determine size, then call up the path
            buffer_size = _DragQueryFileW(hdrop, i, None, 0) + 1
            buffer = ctypes.create_unicode_buffer(buffer_size)
            _DragQueryFileW(hdrop, i, buffer, buffer_size)
            paths.append(buffer.value)

# Debug edition
        logger.debug(f"Extrahierte Pfade aus Windows Drop: {paths}")
        return paths
    except Exception as e:
        logger.error(f"Fehler beim Extrahieren der Drop-Dateien: {e}")
        import traceback
        traceback.print_exc()
        return []

    def _register_tkdnd_drop_target(self) -> bool:
        """Registriert das Widget als Drop-Ziel mit TkinterDnD."""
        try:
# Use tkinterdnd methods
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._handle_tkdnd_drop)
            self.dnd_bind('<<DragEnter>>', self._handle_tkdnd_enter)
            self.dnd_bind('<<DragLeave>>', self._handle_tkdnd_leave)

            logger.info(f"TkinterDnD Drop-Target erfolgreich registriert für Widget {self.winfo_id()}")
            return True
        except Exception as e:
            logger.error(f"Fehler bei TkinterDnD Drop-Target-Registrierung: {e}")
            return False

    def _handle_windows_drop(self, hdrop):
        """Verarbeitet Windows-Drop-Events."""
        try:
# Extract all the dropped file paths
            file_count = _DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
            paths = []

            for i in range(file_count):
# Two runs: first determine size, then call up the path
                buffer_size = _DragQueryFileW(hdrop, i, None, 0) + 1
                buffer = ctypes.create_unicode_buffer(buffer_size)
                _DragQueryFileW(hdrop, i, buffer, buffer_size)
                paths.append(buffer.value)

# Complete the event and call callback
            _DragFinish(hdrop)

            if self._drop_callback and paths:
                self._drop_callback(paths)
        except Exception as e:
            logger.error(f"Fehler bei der Windows Drop-Verarbeitung: {e}")
            if hdrop:
                _DragFinish(hdrop)

    def _handle_tkdnd_drop(self, event):
        """Verarbeitet TkinterDnD Drop-Events."""
        try:
            if hasattr(event, 'data') and event.data:
# Extract paths from event data
                paths = self._extract_paths_from_data(event.data)

                if self._drop_callback and paths:
                    self._drop_callback(paths)
        except Exception as e:
            logger.error(f"Fehler bei der TkinterDnD Drop-Verarbeitung: {e}")

    def _handle_tkdnd_enter(self, event):
        """Verarbeitet TkinterDnD DragEnter-Events."""
        try:
            if self._drop_enter_callback:
                self._drop_enter_callback()
        except Exception as e:
            logger.error(f"Fehler bei der TkinterDnD DragEnter-Verarbeitung: {e}")

    def _handle_tkdnd_leave(self, event):
        """Verarbeitet TkinterDnD DragLeave-Events."""
        try:
            if self._drop_leave_callback:
                self._drop_leave_callback()
        except Exception as e:
            logger.error(f"Fehler bei der TkinterDnD DragLeave-Verarbeitung: {e}")

    def _extract_paths_from_data(self, data) -> List[str]:
        """
        Extrahiert Dateipfade aus TkinterDnD-Daten.

        Args:
            data: Event-Daten von TkinterDnD

        Returns:
            Liste von Dateipfaden
        """
        paths = []

        if not data:
            return paths

# Convert to string
        data_str = str(data).strip()

# Windows Explorer Specific Format with Casted Brackets
        if data_str.startswith('{') and data_str.endswith('}'):
            clean_path = data_str.strip('{}')
            if os.path.exists(clean_path):
                return [clean_path]

# URL format
        if data_str.startswith('file:'):
            import urllib.parse

            if ' file:' in data_str:  # Mehrere URLs
                for part in data_str.split():
                    if part.startswith('file:'):
                        try:
                            path = urllib.parse.unquote(part[5:])
                            if os.name == 'nt' and path.startswith('/'):
                                path = path[1:]
                            if os.path.exists(path):
                                paths.append(path)
                        except:
                            pass
            else:  # Einzelne URL
                try:
                    path = urllib.parse.unquote(data_str[5:])
                    if os.name == 'nt' and path.startswith('/'):
                        path = path[1:]
                    if os.path.exists(path):
                        paths.append(path)
                except:
                    pass

# Standard space separation
        elif ' ' in data_str:
            for part in data_str.split():
                clean = part.strip('"\'{} ')
                if os.path.exists(clean):
                    paths.append(clean)

# Line breaks
        elif '\n' in data_str or '\r' in data_str:
            for line in re.split(r'\r\n|\r|\n', data_str):
                clean = line.strip('"\'{} ')
                if clean and os.path.exists(clean):
                    paths.append(clean)

# Individual path
        elif os.path.exists(data_str):
            paths.append(data_str)

# Cleaning paths
        return [os.path.normpath(p) for p in paths]

    def set_drop_enter_callback(self, callback: Callable[[], None]):
        """Setzt den Callback für DragEnter-Events."""
        self._drop_enter_callback = callback

    def set_drop_leave_callback(self, callback: Callable[[], None]):
        """Setzt den Callback für DragLeave-Events."""
        self._drop_leave_callback = callback


class DropFrame(tk.Frame, DragDropMixin):
    """Ein Tkinter Frame mit Drag & Drop-Unterstützung."""

    def __init__(self, master=None, drop_callback=None, on_drop=None, **kwargs):
        tk.Frame.__init__(self, master, **kwargs)
        DragDropMixin.__init__(self)

# Support for both callback parameters (for compatibility)
        callback = on_drop if on_drop is not None else drop_callback

        if callback:
            self.register_drop_target(callback)


def init_drag_drop():
    """
    Initialisiert die Drag & Drop-Unterstützung.
    Muss vor der Erstellung des Hauptfensters aufgerufen werden.

    Returns:
        bool: True wenn Drag & Drop verfügbar ist, sonst False
    """
    return enable_native_dnd()


def patch_tkinter_root(root):
    """
    Patcht ein bestehendes Tkinter-Root-Fenster mit Drag & Drop-Funktionalität.

    Args:
        root: Tkinter Root-Fenster

    Returns:
        bool: True bei Erfolg, sonst False
    """
    try:
        if DND_MODE == "tkdnd":
# Activate the tkinterdnd for the root window
            TkinterDnD._require(root.tk)

# Add methods
            root.drop_target_register = lambda *args, **kw: TkinterDnD._drop_target_register(root.tk, *args, **kw)
            root.dnd_bind = lambda *args, **kw: TkinterDnD._dnd_bind(root.tk, *args, **kw)

            return True

        return False
    except Exception as e:
        logger.error(f"Fehler beim Patchen des Tkinter-Root-Fensters: {e}")
        return False


def is_dnd_available():
    """
    Prüft, ob Drag & Drop verfügbar ist.

    Returns:
        bool: True wenn verfügbar, sonst False
    """
    return DND_AVAILABLE


def get_dnd_mode():
    """
    Gibt den aktuellen Drag & Drop-Modus zurück.

    Returns:
        str: "native", "tkdnd" oder "none"
    """
    return DND_MODE
