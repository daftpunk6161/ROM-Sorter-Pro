#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Rome Sorter Pro - Topic This Module Implements A Flexible Theme System for Rome Sorter Pro, which Allows Customizing The User Interface With Different Themes, Including Light and Dark Modes, Custom Color Schemes, And Customizable Ui Elements. Features: - Support for Light and Dark Themes - Custom Theme Creation - Automatic Thematic Detection Based on System Settings - Saving and Loading Themes From Configuration Files - Integration with Pyqt and Web Interface"""

import os
import json
import logging
import platform
import colorsys
from enum import Enum
from typing import Dict, Any, Optional, List

# Configure logger
logger = logging.getLogger(__name__)


class ThemeType(Enum):
    """Enum for the different theme types."""
    LIGHT = "light"
    DARK = "dark"
    CUSTOM = "custom"


class ColorScheme:
    """Manages A Color Scheme for a Theme."""

    def __init__(self,
                 primary: str = "#3498db",
                 secondary: str = "#2ecc71",
                 background: str = "#ffffff",
                 text: str = "#333333",
                 accent: str = "#9b59b6",
                 error: str = "#e74c3c",
                 warning: str = "#f39c12",
                 success: str = "#2ecc71",
                 border: str = "#dddddd"):
        """Initialized the color scheme. Args: Primary: primary color for UI elements Secondary: secondary color for UI elements Background: background color Text: text color Accent: accent color for highlights Error: Color for error messages Warning: color for warnings Success: Color for success reports Border: Color for edges and dividing lines"""
        self.primary = primary
        self.secondary = secondary
        self.background = background
        self.text = text
        self.accent = accent
        self.error = error
        self.warning = warning
        self.success = success
        self.border = border

    @classmethod
    def from_dict(cls, color_dict: Dict[str, str]) -> 'ColorScheme':
        """Creates a color scheme from a dictionary. Args: Color_dict: Dictionary with color definitions Return: Color Cheme Instance"""
        return cls(**{k: v for k, v in color_dict.items()
                   if k in ['primary', 'secondary', 'background', 'text',
                           'accent', 'error', 'warning', 'success', 'border']})

    def to_dict(self) -> Dict[str, str]:
        """Convert the Color Scheme Into a dictionary. Return: Dictionary with color definitions"""
        return {
            'primary': self.primary,
            'secondary': self.secondary,
            'background': self.background,
            'text': self.text,
            'accent': self.accent,
            'error': self.error,
            'warning': self.warning,
            'success': self.success,
            'border': self.border
        }

    @classmethod
    def create_dark_scheme(cls) -> 'ColorScheme':
        """Creates a Dark Color Scheme. Return: Colorscheme instance for a Dark Theme"""
        return cls(
            primary="#3498db",
            secondary="#2ecc71",
            background="#121212",
            text="#e0e0e0",
            accent="#9b59b6",
            error="#ff5252",
            warning="#ffb142",
            success="#2ecc71",
            border="#2d2d2d"
        )

    @classmethod
    def create_light_scheme(cls) -> 'ColorScheme':
        """Creates a Bright Color Scheme. Return: Colorscheme Instance for A Light Theme"""
        return cls(
            primary="#2980b9",
            secondary="#27ae60",
            background="#ffffff",
            text="#333333",
            accent="#8e44ad",
            error="#e74c3c",
            warning="#f39c12",
            success="#2ecc71",
            border="#dddddd"
        )

    def invert(self) -> 'ColorScheme':
        """Inverts the color scheme (light too dark or vice versa). Return: Inverted color scheme"""
        inverted = ColorScheme()

        # Invert the main colors
        inverted.background = self._invert_color(self.background)
        inverted.text = self._invert_color(self.text)
        inverted.border = self._invert_color(self.border)

        # For other colors, keep the color but adapts to the brightness
        inverted.primary = self._adjust_brightness(self.primary, is_background=False)
        inverted.secondary = self._adjust_brightness(self.secondary, is_background=False)
        inverted.accent = self._adjust_brightness(self.accent, is_background=False)
        inverted.error = self._adjust_brightness(self.error, is_background=False)
        inverted.warning = self._adjust_brightness(self.warning, is_background=False)
        inverted.success = self._adjust_brightness(self.success, is_background=False)

        return inverted

    def _invert_color(self, hex_color: str) -> str:
        """
        Invertiert eine Farbe.

        Args:
            hex_color: Hex-Farbcode (z.B. "#ffffff")

        Returns:
            Invertierter Hex-Farbcode
        """
        # Remove the #symbol and convert to RGB
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)

        # Invert the values
        r, g, b = 255 - r, 255 - g, 255 - b

        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

    def _adjust_brightness(self, hex_color: str, is_background: bool = True) -> str:
        """If the Brightness of a Color Adapts, but Keep the Color. ARGS: Hex_color: Hex Color Code (e.G. "#FFFFFFFF") IS_BACKGROUND: Whether it is a background color return: adapted hex color code"""
        # Remove the #symbol and convert to RGB
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)

        # Convert to HSV
        r, g, b = r/255.0, g/255.0, b/255.0
        h, s, v = colorsys.rgb_to_hsv(r, g, b)

        # Adapt the brightness
        if is_background:
            # For backgrounds: if light, then make dark and vice versa
            v = 0.1 if v > 0.5 else 0.9
        else:
            # For other colors: adapter the brightness
            v = min(1.0, v * 1.2) if v < 0.5 else max(0.0, v * 0.8)

        # Convert back to RGB
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        r, g, b = int(r*255), int(g*255), int(b*255)

        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"


class Theme:
    """Represents a complete theme with a color scheme and design settings."""

    def __init__(self,
                 name: str,
                 type: ThemeType = ThemeType.LIGHT,
                 colors: Optional[ColorScheme] = None,
                 font_family: str = "Arial, sans-serif",
                 font_size: int = 12,
                 border_radius: int = 4,
                 spacing: int = 8,
                 use_system_defaults: bool = False):
        """Initialized the theme. Args: Name: name of the theme Type: Type of the theme (Light, Dark, Custom) Colors: Colorscheme for the theme FONT_FAMALY: Standard font family font_size: standard script size Border_radius: Radius for rounded corners Spacing: Standard distance between elements use_system_defaults: Whether system specifications should be used"""
        self.name = name
        self.type = type
        self.colors = colors or (
            ColorScheme.create_light_scheme()
            if type == ThemeType.LIGHT
            else ColorScheme.create_dark_scheme()
        )
        self.font_family = font_family
        self.font_size = font_size
        self.border_radius = border_radius
        self.spacing = spacing
        self.use_system_defaults = use_system_defaults

    @classmethod
    def from_dict(cls, theme_dict: Dict[str, Any]) -> 'Theme':
        """Creates a theme from a dictionary. Args: Theme_dict: Dictionary with theme Definitions Return: Theme Instance"""
        # Farbschema extrahieren
        color_scheme = None
        if 'colors' in theme_dict:
            color_scheme = ColorScheme.from_dict(theme_dict['colors'])

        # ThemeType konvertieren
        theme_type = ThemeType(theme_dict.get('type', 'light'))

        # Theme erstellen
        return cls(
            name=theme_dict.get('name', 'Custom Theme'),
            type=theme_type,
            colors=color_scheme,
            font_family=theme_dict.get('font_family', 'Arial, sans-serif'),
            font_size=theme_dict.get('font_size', 12),
            border_radius=theme_dict.get('border_radius', 4),
            spacing=theme_dict.get('spacing', 8),
            use_system_defaults=theme_dict.get('use_system_defaults', False)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the theme into a dictionary. Return: Dictionary with theme definitions"""
        return {
            'name': self.name,
            'type': self.type.value,
            'colors': self.colors.to_dict(),
            'font_family': self.font_family,
            'font_size': self.font_size,
            'border_radius': self.border_radius,
            'spacing': self.spacing,
            'use_system_defaults': self.use_system_defaults
        }

    def generate_qt_stylesheet(self, scale: float = 1.0) -> str:
        """Generates A Qt Stylesheet from the theme. Return: Qt Stylesheet as a String"""
        colors = self.colors
        try:
            scale_value = float(scale or 1.0)
        except Exception:
            scale_value = 1.0
        if scale_value <= 0:
            scale_value = 1.0
        scale_value = max(0.8, min(scale_value, 1.2))
        font_size = max(8, int(round(self.font_size * scale_value)))
        border_radius = max(2, int(round(self.border_radius * scale_value)))
        spacing = max(4, int(round(self.spacing * scale_value)))
        min_btn_width = max(60, int(round(80 * scale_value)))

        return f"""
        /* Hauptfenster */
        QMainWindow, QDialog, QWidget {{
            background-color: {colors.background};
            color: {colors.text};
            font-family: {self.font_family};
            font-size: {font_size}pt;
        }}

        /* Menüs und Menüleisten */
        QMenuBar, QMenu {{
            background-color: {colors.background};
            color: {colors.text};
            border: 1px solid {colors.border};
        }}

        QMenuBar::item:selected, QMenu::item:selected {{
            background-color: {colors.primary};
            color: {'white' if self.type == ThemeType.DARK else 'white'};
        }}

        /* Schaltflächen */
        QPushButton {{
            background-color: {colors.primary};
            color: {'white' if self.type == ThemeType.DARK else 'white'};
            border: none;
            border-radius: {border_radius}px;
            padding: {spacing}px;
            min-width: {min_btn_width}px;
        }}

        QPushButton:hover {{
            background-color: {self._lighten_or_darken(colors.primary, 0.1)};
        }}

        QPushButton:pressed {{
            background-color: {self._lighten_or_darken(colors.primary, 0.2)};
        }}

        /* Sekundäre Schaltflächen */
        QPushButton[secondary="true"] {{
            background-color: {colors.secondary};
        }}

        QPushButton[secondary="true"]:hover {{
            background-color: {self._lighten_or_darken(colors.secondary, 0.1)};
        }}

        /* Eingabefelder */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: {self._lighten_or_darken(colors.background, 0.05)};
            color: {colors.text};
            border: 1px solid {colors.border};
            border-radius: {self.border_radius}px;
            padding: {self.spacing - 2}px;
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {colors.primary};
        }}

        /* Listen und Tabellen */
        QListView, QTreeView, QTableView {{
            background-color: {self._lighten_or_darken(colors.background, 0.03)};
            color: {colors.text};
            border: 1px solid {colors.border};
            border-radius: {self.border_radius}px;
        }}

        QListView::item:selected, QTreeView::item:selected, QTableView::item:selected {{
            background-color: {colors.primary};
            color: {'white' if self.type == ThemeType.DARK else 'white'};
        }}

        /* Tableader */
        QHeaderView::section {{
            background-color: {self._lighten_or_darken(colors.background, 0.1)};
            color: {colors.text};
            padding: 5px;
            border: none;
            border-right: 1px solid {colors.border};
            border-bottom: 1px solid {colors.border};
        }}

        /* Scrollbars */
        QScrollBar:vertical {{
            background-color: {self._lighten_or_darken(colors.background, 0.05)};
            width: 12px;
            margin: 0px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {self._lighten_or_darken(colors.border, 0.1)};
            border-radius: 5px;
            min-height: 20px;
            margin: 2px;
        }}

        QScrollBar:horizontal {{
            background-color: {self._lighten_or_darken(colors.background, 0.05)};
            height: 12px;
            margin: 0px;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {self._lighten_or_darken(colors.border, 0.1)};
            border-radius: 5px;
            min-width: 20px;
            margin: 2px;
        }}

        /* Tabs */
        QTabWidget::pane {{
            border: 1px solid {colors.border};
            border-radius: {self.border_radius}px;
            top: -1px;
        }}

        QTabBar::tab {{
            background-color: {self._lighten_or_darken(colors.background, 0.1)};
            color: {colors.text};
            border: 1px solid {colors.border};
            border-bottom: none;
            border-top-left-radius: {self.border_radius}px;
            border-top-right-radius: {self.border_radius}px;
            padding: 5px 10px;
            margin-right: 2px;
        }}

        QTabBar::tab:selected {{
            background-color: {colors.background};
            border-bottom: none;
        }}

        /* Statusbar */
        QStatusBar {{
            background-color: {self._lighten_or_darken(colors.background, 0.05)};
            color: {colors.text};
            border-top: 1px solid {colors.border};
        }}

        /* Trennlinien */
        QFrame[frameShape="4"], QFrame[frameShape="HLine"] {{
            background-color: {colors.border};
            border: none;
            max-height: 1px;
            margin: {self.spacing}px 0;
        }}

        QFrame[frameShape="5"], QFrame[frameShape="VLine"] {{
            background-color: {colors.border};
            border: none;
            max-width: 1px;
            margin: 0 {self.spacing}px;
        }}

        /* Tooltips */
        QToolTip {{
            background-color: {self._lighten_or_darken(colors.background, 0.1)};
            color: {colors.text};
            border: 1px solid {colors.border};
            border-radius: {self.border_radius}px;
            padding: 2px;
        }}

        /* Progressbar */
        QProgressBar {{
            background-color: {self._lighten_or_darken(colors.background, 0.05)};
            color: {colors.text};
            border: 1px solid {colors.border};
            border-radius: {self.border_radius}px;
            text-align: center;
        }}

        QProgressBar::chunk {{
            background-color: {colors.primary};
            width: 1px;
        }}

        /* Gruppierungen */
        QGroupBox {{
            border: 1px solid {colors.border};
            border-radius: {self.border_radius}px;
            margin-top: 20px;
            font-weight: bold;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 5px;
            color: {colors.text};
        }}
        """

    def generate_css(self) -> str:
        """Generates A CSS Stylesheet for Web Applications. Return: CSS Stylesheet as a String"""
        colors = self.colors

        return f"""
        :root {{
            --primary-color: {colors.primary};
            --secondary-color: {colors.secondary};
            --background-color: {colors.background};
            --text-color: {colors.text};
            --accent-color: {colors.accent};
            --error-color: {colors.error};
            --warning-color: {colors.warning};
            --success-color: {colors.success};
            --border-color: {colors.border};
            --font-family: {self.font_family};
            --font-size: {self.font_size}px;
            --border-radius: {self.border_radius}px;
            --spacing: {self.spacing}px;
        }}

        body {{
            background-color: var(--background-color);
            color: var(--text-color);
            font-family: var(--font-family);
            font-size: var(--font-size);
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }}

        /* Headers */
        h1, h2, h3, h4, h5, h6 {{
            color: var(--text-color);
            margin-top: calc(var(--spacing) * 2);
            margin-bottom: var(--spacing);
        }}

        /* Links */
        a {{
            color: var(--primary-color);
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        /* Buttons */
        button, .button, input[type="button"], input[type="submit"] {{
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: var(--border-radius);
            padding: var(--spacing);
            cursor: pointer;
            font-family: var(--font-family);
            font-size: var(--font-size);
            transition: background-color 0.2s;
        }}

        button:hover, .button:hover, input[type="button"]:hover, input[type="submit"]:hover {{
            background-color: {self._lighten_or_darken(colors.primary, 0.1)};
        }}

        button.secondary, .button.secondary {{
            background-color: var(--secondary-color);
        }}

        button.secondary:hover, .button.secondary:hover {{
            background-color: {self._lighten_or_darken(colors.secondary, 0.1)};
        }}

        /* Form Elements */
        input, textarea, select {{
            background-color: {self._lighten_or_darken(colors.background, 0.05)};
            color: var(--text-color);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            padding: calc(var(--spacing) / 2);
            font-family: var(--font-family);
            font-size: var(--font-size);
        }}

        input:focus, textarea:focus, select:focus {{
            border-color: var(--primary-color);
            outline: none;
        }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: var(--spacing) 0;
        }}

        th, td {{
            text-align: left;
            padding: calc(var(--spacing) / 2);
            border-bottom: 1px solid var(--border-color);
        }}

        th {{
            background-color: {self._lighten_or_darken(colors.background, 0.1)};
        }}

        tbody tr:hover {{
            background-color: {self._lighten_or_darken(colors.background, 0.03)};
        }}

        /* Cards */
        .card {{
            background-color: {self._lighten_or_darken(colors.background, 0.03)};
            border-radius: var(--border-radius);
            border: 1px solid var(--border-color);
            padding: var(--spacing);
            margin-bottom: var(--spacing);
        }}

        /* Navigation */
        nav {{
            background-color: {self._lighten_or_darken(colors.background, 0.05)};
            padding: var(--spacing);
            border-bottom: 1px solid var(--border-color);
        }}

        nav ul {{
            list-style-type: none;
            margin: 0;
            padding: 0;
            display: flex;
        }}

        nav li {{
            margin-right: var(--spacing);
        }}

        nav a {{
            color: var(--text-color);
            text-decoration: none;
            padding: calc(var(--spacing) / 2);
        }}

        nav a:hover, nav a.active {{
            color: var(--primary-color);
        }}

        /* Alerts */
        .alert {{
            padding: var(--spacing);
            border-radius: var(--border-radius);
            margin-bottom: var(--spacing);
        }}

        .alert.error {{
            background-color: {self._alpha_blend(colors.error, colors.background, 0.2)};
            border-left: 4px solid var(--error-color);
        }}

        .alert.warning {{
            background-color: {self._alpha_blend(colors.warning, colors.background, 0.2)};
            border-left: 4px solid var(--warning-color);
        }}

        .alert.success {{
            background-color: {self._alpha_blend(colors.success, colors.background, 0.2)};
            border-left: 4px solid var(--success-color);
        }}

        /* Progress Bar */
        progress {{
            width: 100%;
            height: calc(var(--spacing) * 1.5);
            -webkit-appearance: none;
            appearance: none;
        }}

        progress::-webkit-progress-bar {{
            background-color: {self._lighten_or_darken(colors.background, 0.05)};
            border-radius: var(--border-radius);
        }}

        progress::-webkit-progress-value {{
            background-color: var(--primary-color);
            border-radius: var(--border-radius);
        }}

        /* Container */
        .container {{
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 var(--spacing);
        }}

        /* Grid */
        .grid {{
            display: grid;
            grid-gap: var(--spacing);
        }}

        /* Dashboard specific */
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            grid-gap: var(--spacing);
        }}

        .dashboard-card {{
            background-color: {self._lighten_or_darken(colors.background, 0.03)};
            border-radius: var(--border-radius);
            border: 1px solid var(--border-color);
            padding: var(--spacing);
        }}

        .dashboard-card-header {{
            font-weight: bold;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: calc(var(--spacing) / 2);
            margin-bottom: var(--spacing);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        """

    def _lighten_or_darken(self, hex_color: str, amount: float) -> str:
        """Holds Up a Color Or Darkens it. ARGS: Hex_color: Hex Color Code (e.G. "#FFFFFFFF") Amount: Amount of the Change (positive for Lightening, negative for Darkening) Return: Adapted Hex Color Code"""
        # Remove the #symbol and convert to RGB
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16) / 255.0, int(hex_color[2:4], 16) / 255.0, int(hex_color[4:6], 16) / 255.0

        # Lighten or darken based on the theme type
        if self.type == ThemeType.DARK:
            amount = -amount  # Reverse for dark themes

        # Adjust the values
        r = max(0, min(1, r + amount))
        g = max(0, min(1, g + amount))
        b = max(0, min(1, b + amount))

        # Convert back to Hex
        r, g, b = int(r * 255), int(g * 255), int(b * 255)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _alpha_blend(self, color1: str, color2: str, alpha: float) -> str:
        """Mix two colors with an alpha value. Args: Color1: First color (e.g. "#ffffffff") Color2: second color (e.g. "#000000") Alpha: Alpha value for the mixture (0.0 to 1.0) Return: Mixed hex color code"""
        # Remove the #symbol and convert to RGB
        color1 = color1.lstrip('#')
        r1, g1, b1 = int(color1[0:2], 16), int(color1[2:4], 16), int(color1[4:6], 16)

        color2 = color2.lstrip('#')
        r2, g2, b2 = int(color2[0:2], 16), int(color2[2:4], 16), int(color2[4:6], 16)

        # Mix the colors
        r = int(r1 * alpha + r2 * (1 - alpha))
        g = int(g1 * alpha + g2 * (1 - alpha))
        b = int(b1 * alpha + b2 * (1 - alpha))

        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"


class ThemeManager:
    """Manages themes for the application."""

    def __init__(self, config_dir: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialized the theme manager. Args: Config_Dir: List for theme configuration files"""
        config_dir = self._resolve_theme_config_dir(config=config, config_dir=config_dir)
        if config_dir is None:
            # Bestimme Standard-Konfigurationsverzeichnis
            user_home = os.path.expanduser("~")
            if platform.system() == "Windows":
                config_dir = os.path.join(user_home, "AppData", "Local", "ROMSorterPro", "themes")
            else:
                config_dir = os.path.join(user_home, ".config", "rom-sorter-pro", "themes")

        self.config_dir = str(config_dir) if config_dir is not None else ""
        self.themes: Dict[str, Theme] = {}
        self.current_theme_name = "default"

        # Make sure the configuration directory exists
        if not self.config_dir:
            self.config_dir = os.path.join(os.path.expanduser("~"), ".config", "rom-sorter-pro", "themes")
        os.makedirs(self.config_dir, exist_ok=True)

        # Lade Standardthemes
        self._initialize_default_themes()

        # Lade gespeicherte Themes
        self._load_saved_themes()

    @staticmethod
    def _resolve_theme_config_dir(
        config: Optional[Dict[str, Any]] = None,
        config_dir: Optional[str] = None,
    ) -> Optional[str]:
        if config_dir:
            return config_dir
        if not isinstance(config, dict):
            return None
        gui_cfg = config.get("gui_settings") or {}
        if isinstance(gui_cfg, dict):
            theme_cfg = gui_cfg.get("themes") or {}
            if isinstance(theme_cfg, dict):
                for key in ("config_dir", "themes_dir", "theme_dir"):
                    value = theme_cfg.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
            for key in ("theme_config_dir", "themes_dir", "theme_dir"):
                value = gui_cfg.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    def set_active_theme(self, theme_name: str) -> bool:
        """Set the active theme.

        Args:
            theme_name: Name of the theme to set

        Returns:
            True if successful, False otherwise
        """
        if theme_name in self.themes:
            self.current_theme_name = theme_name
            logger.info(f"Theme '{theme_name}' aktiviert")
            return True
        logger.error(f"Theme '{theme_name}' nicht gefunden")
        return False

    def _initialize_default_themes(self) -> None:
        """Initialisiert Standardthemes."""
        # Helles Standardtheme
        light_theme = Theme(
            name="Light",
            type=ThemeType.LIGHT,
            colors=ColorScheme.create_light_scheme()
        )

        # Dunkles Standardtheme
        dark_theme = Theme(
            name="Dark",
            type=ThemeType.DARK,
            colors=ColorScheme.create_dark_scheme()
        )

        # Blau-Thema
        blue_theme = Theme(
            name="Blue",
            type=ThemeType.CUSTOM,
            colors=ColorScheme(
                primary="#1e88e5",
                secondary="#00acc1",
                background="#e3f2fd",
                text="#37474f",
                accent="#5e35b1",
                error="#e53935",
                warning="#ffa000",
                success="#43a047",
                border="#bbdefb"
            )
        )

        # Dunkles Blau-Thema
        dark_blue_theme = Theme(
            name="Dark Blue",
            type=ThemeType.DARK,
            colors=ColorScheme(
                primary="#1e88e5",
                secondary="#00acc1",
                background="#102027",
                text="#eceff1",
                accent="#7e57c2",
                error="#ef5350",
                warning="#ffb300",
                success="#66bb6a",
                border="#263238"
            )
        )

        # Retro-Gaming-Thema
        retro_theme = Theme(
            name="Retro Gaming",
            type=ThemeType.DARK,
            colors=ColorScheme(
                primary="#ff5722",
                secondary="#4caf50",
                background="#212121",
                text="#f0f0f0",
                accent="#ffeb3b",
                error="#f44336",
                warning="#ff9800",
                success="#8bc34a",
                border="#424242"
            ),
            font_family="'Press Start 2P', monospace",
            border_radius=0
        )

        crt_green_theme = Theme(
            name="CRT Green",
            type=ThemeType.DARK,
            colors=ColorScheme(
                primary="#3bff76",
                secondary="#57ff8b",
                background="#06130a",
                text="#9cff7a",
                accent="#5bff93",
                error="#ff6b6b",
                warning="#f7c66a",
                success="#6bff95",
                border="#1d3b22"
            ),
            font_family="'Press Start 2P', monospace",
            border_radius=0
        )

        gameboy_theme = Theme(
            name="GameBoy DMG",
            type=ThemeType.LIGHT,
            colors=ColorScheme(
                primary="#306230",
                secondary="#4f8f4f",
                background="#9bbc0f",
                text="#0f380f",
                accent="#306230",
                error="#8b1d1d",
                warning="#826f1f",
                success="#2f6b2f",
                border="#0f380f"
            ),
            font_family="'Press Start 2P', monospace",
            border_radius=0
        )

        neo_dark_theme = Theme(
            name="Neo Dark",
            type=ThemeType.DARK,
            colors=ColorScheme(
                primary="#4c8bf5",
                secondary="#8ae9c1",
                background="#0f111a",
                text="#e6e6e6",
                accent="#c792ea",
                error="#ff5370",
                warning="#ffcb6b",
                success="#c3e88d",
                border="#1f2233"
            )
        )

        nord_frost_theme = Theme(
            name="Nord Frost",
            type=ThemeType.DARK,
            colors=ColorScheme(
                primary="#5e81ac",
                secondary="#88c0d0",
                background="#2e3440",
                text="#d8dee9",
                accent="#81a1c1",
                error="#bf616a",
                warning="#ebcb8b",
                success="#a3be8c",
                border="#3b4252"
            )
        )

        solar_light_theme = Theme(
            name="Solar Light",
            type=ThemeType.LIGHT,
            colors=ColorScheme(
                primary="#268bd2",
                secondary="#2aa198",
                background="#fdf6e3",
                text="#657b83",
                accent="#b58900",
                error="#dc322f",
                warning="#cb4b16",
                success="#859900",
                border="#eee8d5"
            )
        )

        clean_slate_theme = Theme(
            name="Clean Slate",
            type=ThemeType.LIGHT,
            colors=ColorScheme(
                primary="#4A6CF7",
                secondary="#4A6CF7",
                background="#FAFBFC",
                text="#1A1A2E",
                accent="#4A6CF7",
                error="#DC3545",
                warning="#FFC107",
                success="#28A745",
                border="#E1E4E8"
            )
        )

        midnight_pro_theme = Theme(
            name="Midnight Pro",
            type=ThemeType.DARK,
            colors=ColorScheme(
                primary="#58A6FF",
                secondary="#58A6FF",
                background="#0D1117",
                text="#C9D1D9",
                accent="#58A6FF",
                error="#F85149",
                warning="#D29922",
                success="#3FB950",
                border="#30363D"
            )
        )

        retro_console_theme = Theme(
            name="Retro Console",
            type=ThemeType.DARK,
            colors=ColorScheme(
                primary="#FF6B97",
                secondary="#FF6B97",
                background="#2C2137",
                text="#F0E7D5",
                accent="#FF6B97",
                error="#EF476F",
                warning="#FFD166",
                success="#95D17E",
                border="#5A4668"
            ),
            border_radius=12
        )

        # Add the Standarddthemes
        self.themes["Light"] = light_theme
        self.themes["Dark"] = dark_theme
        self.themes["Blue"] = blue_theme
        self.themes["Dark Blue"] = dark_blue_theme
        self.themes["Retro Gaming"] = retro_theme
        self.themes["CRT Green"] = crt_green_theme
        self.themes["GameBoy DMG"] = gameboy_theme
        self.themes["Neo Dark"] = neo_dark_theme
        self.themes["Nord Frost"] = nord_frost_theme
        self.themes["Solar Light"] = solar_light_theme
        self.themes["Clean Slate"] = clean_slate_theme
        self.themes["Midnight Pro"] = midnight_pro_theme
        self.themes["Retro Console"] = retro_console_theme

        # Set the standard.
        if self._detect_system_theme() == ThemeType.DARK:
            self.current_theme_name = "Dark"
        else:
            self.current_theme_name = "Light"

    def _load_saved_themes(self) -> None:
        """Lades stored themes from configuration files."""
        try:
            # Upload the theme list
            theme_index_file = os.path.join(self.config_dir, "theme_index.json")
            custom_themes = []

            if os.path.exists(theme_index_file):
                with open(theme_index_file, 'r', encoding='utf-8') as f:
                    theme_data = json.load(f)
                    custom_themes = theme_data.get('themes', [])
                    saved_current_theme = theme_data.get('current_theme')
                    if saved_current_theme and saved_current_theme in custom_themes:
                        self.current_theme_name = saved_current_theme

            # Lade individuelle Theme-Dateien
            for theme_name in custom_themes:
                theme_file = os.path.join(self.config_dir, f"{theme_name}.json")
                if os.path.exists(theme_file):
                    try:
                        with open(theme_file, 'r', encoding='utf-8') as f:
                            theme_dict = json.load(f)
                            theme = Theme.from_dict(theme_dict)
                            self.themes[theme_name] = theme
                    except Exception as e:
                        logger.warning(f"Fehler beim Laden des Themes '{theme_name}': {e}")

        except Exception as e:
            logger.error(f"Fehler beim Laden gespeicherter Themes: {e}")

    def _save_theme_index(self) -> None:
        """Speichert den Theme-Index."""
        try:
            theme_index_file = os.path.join(self.config_dir, "theme_index.json")

            # Sammle benutzerdefinierte Themes
            custom_themes = []
            for name, theme in self.themes.items():
                if theme.type == ThemeType.CUSTOM:
                    custom_themes.append(name)

            # Speichere den Index
            with open(theme_index_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'themes': custom_themes,
                    'current_theme': self.current_theme_name
                }, f, indent=2)

            logger.debug(f"Theme-Index gespeichert in '{theme_index_file}'")

        except Exception as e:
            logger.error(f"Fehler beim Speichern des Theme-Index: {e}")

    def add_theme(self, theme: Theme) -> bool:
        """Add a new theme. Args: Theme: The Theme to Be Added Return: True in the event of Success, False in the event of errors"""
        try:
            # Add the theme to the dictionary
            self.themes[theme.name] = theme

            # Wenn es ein benutzerdefiniertes Theme ist, speichere es
            if theme.type == ThemeType.CUSTOM:
                theme_file = os.path.join(self.config_dir, f"{theme.name}.json")
                with open(theme_file, 'w', encoding='utf-8') as f:
                    json.dump(theme.to_dict(), f, indent=2)

            # Aktualisiere den Theme-Index
            self._save_theme_index()

            logger.info(f"Theme '{theme.name}' hinzugefügt")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen des Themes '{theme.name}': {e}")
            return False

    def remove_theme(self, theme_name: str) -> bool:
        """Removes a theme. Args: Theme_Name: Name of the Theme to Be Removed Return: True in the event of Success, False in the event of errors"""
        # Standarddthemes cannot be removed
        if theme_name in [
            'Light',
            'Dark',
            'Blue',
            'Dark Blue',
            'Retro Gaming',
            'CRT Green',
            'GameBoy DMG',
            'Neo Dark',
            'Nord Frost',
            'Solar Light',
        ]:
            logger.warning(f"Standardtheme '{theme_name}' kann nicht entfernt werden")
            return False

        if theme_name not in self.themes:
            logger.warning(f"Theme '{theme_name}' nicht gefunden")
            return False

        try:
            # Delete the theme file
            theme_file = os.path.join(self.config_dir, f"{theme_name}.json")
            if os.path.exists(theme_file):
                os.remove(theme_file)

            # Remove the theme from the dictionary
            del self.themes[theme_name]

            # If it was the current theme, change to the standard
            if self.current_theme_name == theme_name:
                if self._detect_system_theme() == ThemeType.DARK:
                    self.current_theme_name = "Dark"
                else:
                    self.current_theme_name = "Light"

            # Aktualisiere den Theme-Index
            self._save_theme_index()

            logger.info(f"Theme '{theme_name}' entfernt")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Entfernen des Themes '{theme_name}': {e}")
            return False

    def get_theme(self, theme_name: Optional[str] = None) -> Theme:
        """Gives back a theme. ARGS: Theme_Name: Name of the Themes Or None for the Current Theme Return: Theme Instance"""
        resolved = theme_name or self.current_theme_name
        return self.themes.get(resolved, self.themes["Light"])

    def set_current_theme(self, theme_name: str) -> bool:
        """Set the current theme. Args: Theme_Name: Name of the theme to be set Return: True in the event of success, false in the event of errors"""
        if theme_name not in self.themes:
            logger.warning(f"Theme '{theme_name}' nicht gefunden")
            return False

        self.current_theme_name = theme_name
        self._save_theme_index()
        logger.info(f"Aktuelles Theme auf '{theme_name}' gesetzt")
        return True

    def _detect_system_theme(self) -> ThemeType:
        """Recognize the system theme (light or dark). Return: Themetype.light or themetype.dark"""
        # Plattformspezifische Erkennung
        system = platform.system()

        if system == "Windows":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                   r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                    # 0 = Dunkel, 1 = Hell
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    return ThemeType.LIGHT if value == 1 else ThemeType.DARK
            except Exception as exc:
                logger.debug("Windows theme detection failed: %s", exc)

        elif system == "Darwin":  # macOS
            try:
                import subprocess  # nosec B404
                result = subprocess.run(  # nosec B603
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True, text=True
                )
                return ThemeType.DARK if "Dark" in result.stdout else ThemeType.LIGHT
            except Exception as exc:
                logger.debug("macOS theme detection failed: %s", exc)

        elif system == "Linux":
            # Attempts to recognize the gnome theme
            try:
                import subprocess  # nosec B404
                result = subprocess.run(  # nosec B603
                    ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                    capture_output=True, text=True
                )
                return ThemeType.DARK if "dark" in result.stdout.lower() else ThemeType.LIGHT
            except Exception as exc:
                logger.debug("Linux theme detection failed: %s", exc)

        # Fallback: Helles Theme
        return ThemeType.LIGHT

    def get_system_theme_name(self) -> str:
        """Return the theme name matching the current system appearance."""
        return "Dark" if self._detect_system_theme() == ThemeType.DARK else "Light"

    def get_theme_names(self) -> List[str]:
        """Gives Back a List of All Available Theme Names. Return: List of Theme Names"""
        return list(self.themes.keys())

    def get_current_theme_name(self) -> str:
        """Gives back the name of the current theme. Return: Name of the current theme"""
        return self.current_theme_name

    def create_theme_from_colors(self, name: str, primary: str, secondary: str,
                               background: str, text: str) -> Theme:
        """Creates a new theme from Basic Colors. ARGS: Name: Name of the Theme Primary: Primary Color Secondary: Secondary Color Background: Background Color Text: Text Color Return: Created Theme"""
        # Determine Whether it is a light or dark theme
        is_dark = self._is_dark_color(background)
        theme_type = ThemeType.DARK if is_dark else ThemeType.LIGHT

        # Create the color scheme with derived accent colors
        colors = ColorScheme(
            primary=primary,
            secondary=secondary,
            background=background,
            text=text,
            accent=self._generate_accent_color(primary, secondary),
            error="#e74c3c" if not is_dark else "#ff5252",
            warning="#f39c12" if not is_dark else "#ffb142",
            success="#2ecc71" if not is_dark else "#5cb85c",
            border=self._generate_border_color(background, text)
        )

        # Create the theme
        theme = Theme(
            name=name,
            type=theme_type if theme_type != ThemeType.LIGHT else ThemeType.CUSTOM,
            colors=colors
        )

        return theme

    def _is_dark_color(self, hex_color: str) -> bool:
        """Check Whether a Color is Dark. ARGS: Hex_Color: Hex Color Code (e.G. "#ffffffff") Return: True When the Color is Dark, OtherWise False"""
        # Remove the #symbol and convert to RGB
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)

        # Calculate the brightness (0-255)
        brightness = (r * 299 + g * 587 + b * 114) / 1000

        # Dark when the brightness is below 128
        return brightness < 128

    def _generate_accent_color(self, primary: str, secondary: str) -> str:
        """Generates an accent color from primary and secondary color. Args: Primary: primary color Secondary: secondary color Return: Generated accent color"""
        # Remove the #symbol and convert to RGB
        primary = primary.lstrip('#')
        r1, g1, b1 = int(primary[0:2], 16) / 255.0, int(primary[2:4], 16) / 255.0, int(primary[4:6], 16) / 255.0

        secondary = secondary.lstrip('#')
        r2, g2, b2 = int(secondary[0:2], 16) / 255.0, int(secondary[2:4], 16) / 255.0, int(secondary[4:6], 16) / 255.0

        # Convert to HSV
        h1, s1, v1 = colorsys.rgb_to_hsv(r1, g1, b1)
        h2, s2, v2 = colorsys.rgb_to_hsv(r2, g2, b2)

        # Create A New Color with a Mixed Color and Adapted Saturn
        h = (h1 + h2 / 2) % 1.0
        s = min(1.0, (s1 + s2) / 1.5)
        v = min(1.0, (v1 + v2) / 1.5)

        # Convert back to RGB and then to Hex
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        r, g, b = int(r * 255), int(g * 255), int(b * 255)

        return f"#{r:02x}{g:02x}{b:02x}"

    def _generate_border_color(self, background: str, text: str) -> str:
        """Generates A Edge Color From Background and Text Color. Args: Background: Background Color Text: Text Color Return: Generated Edge Color"""
        # Remove the #symbol and convert to RGB
        background = background.lstrip('#')
        r1, g1, b1 = int(background[0:2], 16), int(background[2:4], 16), int(background[4:6], 16)

        text = text.lstrip('#')
        r2, g2, b2 = int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)

        # Mix the colors (80% background, 20% text)
        r = int(r1 * 0.8 + r2 * 0.2)
        g = int(g1 * 0.8 + g2 * 0.2)
        b = int(b1 * 0.8 + b2 * 0.2)

        return f"#{r:02x}{g:02x}{b:02x}"


# Example of using the module functions
if __name__ == "__main__":
    # Konfiguriere Logging
    logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    print("ROM Sorter Pro - Theme Manager")
    print("-----------------------------------------")

    # Erstelle einen ThemeManager
    theme_manager = ThemeManager()

    # Give out available themes
    print(f"Verfügbare Themes: {', '.join(theme_manager.get_theme_names())}")
    print(f"Aktuelles Theme: {theme_manager.get_current_theme_name()}")

    # Erstelle ein benutzerdefiniertes Theme
    custom_theme = theme_manager.create_theme_from_colors(
        name="Mein Theme",
        primary="#e91e63",
        secondary="#2196f3",
        background="#f5f5f5",
        text="#212121"
    )

    # Add the theme
    theme_manager.add_theme(custom_theme)
    print(f"Theme '{custom_theme.name}' hinzugefügt")

    # Set the Custom Theme as a Current Theme
    theme_manager.set_current_theme(custom_theme.name)
    print(f"Aktuelles Theme: {theme_manager.get_current_theme_name()}")

    # Generiere Stylesheets
    current_theme = theme_manager.get_theme()

    print("\nBeispiel für Qt-Stylesheet (gekürzt):")
    qt_style = current_theme.generate_qt_stylesheet()
    print(qt_style[:200] + "...\n")

    print("\nBeispiel für CSS (gekürzt):")
    css_style = current_theme.generate_css()
    print(css_style[:200] + "...")
