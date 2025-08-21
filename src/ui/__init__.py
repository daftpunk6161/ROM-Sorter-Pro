"""Rom sorter Ui-package V2.1.8-Adjusted This package contains the user interface components for the ROM sorter application. The UI was modular to improve the maintenance and expandability. Core modules: - App.py: Main application class that connects GUI and logic - base.py: basic UI components and styles - Main_window.py: Definition of the main window - Widgets.py: Reusable Ui-Widgets - Custom_widgets.py: Extended widgets with additional functions -Panels.py: Tab panels and other panel components - Dialogs.py: Specialized dialog boxes - Theme_manager.py: Theme management with support for Helle/Dark Themes - enhanced_theme.py: simplified theme-api"""

# Grundlegende UI-Komponenten
from .base import STYLE, BaseApp, center_window, create_tooltip
from .main_window import ROMSorterWindow
from .app import ROMSorterApp, main

# Widgets and Ui elements
from .widgets import FolderSelector, ToggleSwitch, FileListBox, ProgressDialog
from .panels import TabPanel, OptionsPanel, StatisticsPanel, LogPanel
from .custom_widgets import DragDropSupport, CustomTreeview
from .dialogs import (
    AboutDialog, SettingsDialog, ErrorDialog,
    show_error_dialog, show_about_dialog, show_settings_dialog
)

# Theme-System
try:
    from .theme_manager import ThemeManager, Theme, ThemeType, ColorScheme
    from .theme_integration import ThemeIntegrator
    from .enhanced_theme import (
        get_current_theme, apply_theme_to_widget, register_for_theme_updates,
        register_theme_callback, set_theme, initialize_theme_system
    )
    THEME_SUPPORT = True
except ImportError:
    THEME_SUPPORT = False

# Drag & Drop Support
# Define defaults first to avoid circular imports
DND_AVAILABLE = False
DND_MANAGER_AVAILABLE = False
IntegratedDnDSupport = None
create_drop_target = None
add_drop_support = None
get_dnd_manager = None

# Now try importing safely
def _initialize_dnd():
    """Initialize DND support without circular imports"""
    global DND_AVAILABLE, DND_MANAGER_AVAILABLE, IntegratedDnDSupport
    global create_drop_target, add_drop_support, get_dnd_manager

    try:
        from .integrated_dnd import (
            DND_AVAILABLE as _DND_AVAILABLE,
            DND_MANAGER_AVAILABLE as _DND_MANAGER_AVAILABLE,
            IntegratedDnDSupport as _IntegratedDnDSupport,
            create_drop_target as _create_drop_target,
            add_drop_support as _add_drop_support,
            get_dnd_manager as _get_dnd_manager
        )
        DND_AVAILABLE = _DND_AVAILABLE
        DND_MANAGER_AVAILABLE = _DND_MANAGER_AVAILABLE
        IntegratedDnDSupport = _IntegratedDnDSupport
        create_drop_target = _create_drop_target
        add_drop_support = _add_drop_support
        get_dnd_manager = _get_dnd_manager
    except ImportError:
        # Fallback to GUI-DnD
        try:
            from .gui_dnd import DND_AVAILABLE as _DND_AVAILABLE
            DND_AVAILABLE = _DND_AVAILABLE
            DND_MANAGER_AVAILABLE = False
        except ImportError:
            DND_AVAILABLE = False
            DND_MANAGER_AVAILABLE = False

# Initialize DND support
_initialize_dnd()

# UI status and mode functions
def is_ui_available():
    """Check if UI is available.

    Returns:
        bool: True if UI is available, False otherwise
    """
    try:
        import tkinter
        return True
    except ImportError:
        return False

def get_ui_mode():
    """Get the UI mode.

    Returns:
        str: UI mode (tkinter, qt, cli)
    """
    if not is_ui_available():
        return "cli"

    # Check for Qt
    try:
        # Try to import either PyQt5 or PyQt6
        try:
            import PyQt5
            return "qt"
        except ImportError:
            try:
                import PyQt6
                return "qt"
            except ImportError:
                pass
    except Exception:
        pass

    # Default to Tkinter
    return "tkinter"

# Exposing the main function for starting the application
__all__ = [
    'STYLE', 'BaseApp', 'center_window', 'create_tooltip',
    'FolderSelector', 'ToggleSwitch', 'FileListBox', 'ProgressDialog',
    'ThemeManager', 'Theme', 'ThemeType', 'ColorScheme', 'ThemeIntegrator', 'THEME_SUPPORT',
    'get_current_theme', 'apply_theme_to_widget', 'register_for_theme_updates',
    'register_theme_callback', 'set_theme', 'initialize_theme_system',
    'TabPanel', 'OptionsPanel', 'StatisticsPanel', 'LogPanel',
    'DragDropSupport', 'CustomTreeview',
    'ROMSorterWindow', 'ROMSorterApp', 'main',
    'AboutDialog', 'SettingsDialog', 'ErrorDialog',
    'show_error_dialog', 'show_about_dialog', 'show_settings_dialog',
    'is_ui_available', 'get_ui_mode',
    'DND_AVAILABLE', 'DND_MANAGER_AVAILABLE', 'IntegratedDnDSupport',
    'create_drop_target', 'add_drop_support', 'get_dnd_manager'
]
