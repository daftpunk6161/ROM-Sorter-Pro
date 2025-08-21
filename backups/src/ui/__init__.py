"""
ROM-Sorter UI-Package

This package contains the user interface components for the ROM-Sorter application.
The UI has been built in a modular way to improve maintainability and extensibility.

Modules:
- app.py: Main application class that connects GUI and logic
- base.py: Basic UI components and styles
- custom_widgets.py: Enhanced widgets with additional functions
- main_window.py: Main window definition
- panels.py: Tab panels and other panel components
- widgets.py: Reusable UI widgets
- dialogs.py: Specialized dialog windows
- compat.py: Compatibility layer for migration
- theme_manager.py: Theme management with support for light/dark themes
- theme_integration.py: Integration of theme management into the GUI
- gui_dnd.py: Drag and drop functionality for the GUI
- integrated_dnd.py: Integration of different DND implementations
"""

from .base import STYLE, BaseApp, center_window, create_tooltip
from .widgets import FolderSelector, ToggleSwitch, FileListBox, ProgressDialog
from .panels import TabPanel, OptionsPanel, StatisticsPanel, LogPanel
from .custom_widgets import DragDropSupport, CustomTreeview
from .main_window import ROMSorterWindow
from .app import ROMSorterApp, main
from .dialogs import AboutDialog, SettingsDialog, ErrorDialog, show_error_dialog, show_about_dialog, show_settings_dialog
from .compat import is_ui_available, get_ui_mode

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
