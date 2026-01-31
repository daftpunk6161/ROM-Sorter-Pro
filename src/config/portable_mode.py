"""Portable Mode - F70 Implementation.

Provides portable configuration for USB-stick deployment.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class PortablePaths:
    """Portable paths configuration."""

    base_dir: Path
    config_dir: Path
    cache_dir: Path
    data_dir: Path
    logs_dir: Path
    temp_dir: Path
    backup_dir: Path


class PortableMode:
    """Portable mode configuration.

    Implements F70: Portable-Mode

    Features:
    - All paths relative to program
    - USB-stick deployment
    - No system-wide config
    - Self-contained operation
    """

    PORTABLE_MARKER = ".portable"
    PORTABLE_CONFIG = "portable_config.json"

    def __init__(self):
        """Initialize portable mode."""
        self._is_portable = False
        self._base_dir: Optional[Path] = None
        self._paths: Optional[PortablePaths] = None
        self._config: Dict[str, Any] = {}

        self._detect_mode()

    def _get_program_dir(self) -> Path:
        """Get program directory."""
        # Try to find the main script location
        if getattr(sys, "frozen", False):
            # Running as compiled executable
            return Path(sys.executable).parent
        else:
            # Running as script
            main_module = sys.modules.get("__main__")
            if main_module and hasattr(main_module, "__file__") and main_module.__file__:
                return Path(main_module.__file__).parent.resolve()

            # Fallback to current working directory
            return Path.cwd()

    def _detect_mode(self) -> None:
        """Detect if running in portable mode."""
        program_dir = self._get_program_dir()

        # Check for portable marker file
        marker_file = program_dir / self.PORTABLE_MARKER

        if marker_file.exists():
            self._is_portable = True
            self._base_dir = program_dir
            self._load_config()
            self._setup_paths()
        else:
            # Check environment variable
            if os.environ.get("ROM_SORTER_PORTABLE", "").lower() in ("1", "true", "yes"):
                self._is_portable = True
                self._base_dir = program_dir
                self._setup_paths()

    def _load_config(self) -> None:
        """Load portable configuration."""
        if not self._base_dir:
            return

        config_file = self._base_dir / self.PORTABLE_CONFIG

        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except Exception:
                self._config = {}

    def _save_config(self) -> None:
        """Save portable configuration."""
        if not self._base_dir:
            return

        config_file = self._base_dir / self.PORTABLE_CONFIG

        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2)
        except Exception:
            pass

    def _setup_paths(self) -> None:
        """Setup portable paths."""
        if not self._base_dir:
            return

        self._paths = PortablePaths(
            base_dir=self._base_dir,
            config_dir=self._base_dir / "config",
            cache_dir=self._base_dir / "cache",
            data_dir=self._base_dir / "data",
            logs_dir=self._base_dir / "logs",
            temp_dir=self._base_dir / "temp",
            backup_dir=self._base_dir / "backups",
        )

        # Create directories if needed
        for path in [
            self._paths.config_dir,
            self._paths.cache_dir,
            self._paths.data_dir,
            self._paths.logs_dir,
            self._paths.temp_dir,
            self._paths.backup_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    @property
    def is_portable(self) -> bool:
        """Check if running in portable mode."""
        return self._is_portable

    @property
    def base_dir(self) -> Optional[Path]:
        """Get base directory."""
        return self._base_dir

    @property
    def paths(self) -> Optional[PortablePaths]:
        """Get portable paths."""
        return self._paths

    def get_config_path(self, filename: str) -> Path:
        """Get config file path.

        Args:
            filename: Config filename

        Returns:
            Full path
        """
        if self._is_portable and self._paths:
            return self._paths.config_dir / filename
        else:
            return Path("config") / filename

    def get_cache_path(self, filename: str) -> Path:
        """Get cache file path.

        Args:
            filename: Cache filename

        Returns:
            Full path
        """
        if self._is_portable and self._paths:
            return self._paths.cache_dir / filename
        else:
            return Path("cache") / filename

    def get_data_path(self, filename: str) -> Path:
        """Get data file path.

        Args:
            filename: Data filename

        Returns:
            Full path
        """
        if self._is_portable and self._paths:
            return self._paths.data_dir / filename
        else:
            return Path("data") / filename

    def get_log_path(self, filename: str) -> Path:
        """Get log file path.

        Args:
            filename: Log filename

        Returns:
            Full path
        """
        if self._is_portable and self._paths:
            return self._paths.logs_dir / filename
        else:
            return Path("logs") / filename

    def get_temp_path(self, filename: str) -> Path:
        """Get temp file path.

        Args:
            filename: Temp filename

        Returns:
            Full path
        """
        if self._is_portable and self._paths:
            return self._paths.temp_dir / filename
        else:
            return Path("temp") / filename

    def get_backup_path(self, filename: str) -> Path:
        """Get backup file path.

        Args:
            filename: Backup filename

        Returns:
            Full path
        """
        if self._is_portable and self._paths:
            return self._paths.backup_dir / filename
        else:
            return Path("backups") / filename

    def enable_portable_mode(self) -> bool:
        """Enable portable mode by creating marker file.

        Returns:
            True if successful
        """
        program_dir = self._get_program_dir()
        marker_file = program_dir / self.PORTABLE_MARKER

        try:
            marker_file.write_text(
                "ROM-Sorter-Pro Portable Mode\n"
                "Delete this file to use standard paths.\n"
            )

            self._is_portable = True
            self._base_dir = program_dir
            self._setup_paths()

            return True

        except Exception:
            return False

    def disable_portable_mode(self) -> bool:
        """Disable portable mode by removing marker file.

        Returns:
            True if successful
        """
        if not self._base_dir:
            return False

        marker_file = self._base_dir / self.PORTABLE_MARKER

        try:
            if marker_file.exists():
                marker_file.unlink()

            self._is_portable = False
            self._paths = None

            return True

        except Exception:
            return False

    def get_relative_path(self, absolute_path: Path) -> Path:
        """Convert absolute path to relative (for portable storage).

        Args:
            absolute_path: Absolute path

        Returns:
            Relative path if possible, otherwise absolute
        """
        if not self._is_portable or not self._base_dir:
            return absolute_path

        try:
            return absolute_path.relative_to(self._base_dir)
        except ValueError:
            return absolute_path

    def get_absolute_path(self, relative_path: Path) -> Path:
        """Convert relative path to absolute.

        Args:
            relative_path: Relative path

        Returns:
            Absolute path
        """
        if not self._is_portable or not self._base_dir:
            return relative_path

        if relative_path.is_absolute():
            return relative_path

        return self._base_dir / relative_path

    def store_recent_path(self, key: str, path: str) -> None:
        """Store a recent path in portable config.

        Args:
            key: Path key
            path: Path value
        """
        if not self._is_portable:
            return

        recent = self._config.setdefault("recent_paths", {})

        # Store relative path if possible
        try:
            if self._base_dir:
                rel_path = Path(path).relative_to(self._base_dir)
                recent[key] = str(rel_path)
            else:
                recent[key] = path
        except ValueError:
            recent[key] = path

        self._save_config()

    def get_recent_path(self, key: str) -> Optional[str]:
        """Get a recent path from portable config.

        Args:
            key: Path key

        Returns:
            Path value or None
        """
        recent = self._config.get("recent_paths", {})
        rel_path = recent.get(key)

        if not rel_path:
            return None

        # Convert to absolute if portable
        if self._is_portable and self._base_dir:
            abs_path = self._base_dir / rel_path
            if abs_path.exists():
                return str(abs_path)

        return rel_path

    def get_status(self) -> Dict[str, Any]:
        """Get portable mode status.

        Returns:
            Status dict
        """
        if not self._is_portable:
            return {
                "portable": False,
                "message": "Running in standard mode",
            }

        return {
            "portable": True,
            "base_dir": str(self._base_dir) if self._base_dir else None,
            "config_dir": str(self._paths.config_dir) if self._paths else None,
            "cache_dir": str(self._paths.cache_dir) if self._paths else None,
            "data_dir": str(self._paths.data_dir) if self._paths else None,
            "logs_dir": str(self._paths.logs_dir) if self._paths else None,
        }


# Singleton instance
_portable_mode: Optional[PortableMode] = None


def get_portable_mode() -> PortableMode:
    """Get portable mode singleton.

    Returns:
        PortableMode instance
    """
    global _portable_mode

    if _portable_mode is None:
        _portable_mode = PortableMode()

    return _portable_mode


def is_portable() -> bool:
    """Check if running in portable mode.

    Returns:
        True if portable
    """
    return get_portable_mode().is_portable


def get_config_path(filename: str) -> Path:
    """Get config file path.

    Args:
        filename: Config filename

    Returns:
        Full path
    """
    return get_portable_mode().get_config_path(filename)


def get_cache_path(filename: str) -> Path:
    """Get cache file path.

    Args:
        filename: Cache filename

    Returns:
        Full path
    """
    return get_portable_mode().get_cache_path(filename)


def get_data_path(filename: str) -> Path:
    """Get data file path.

    Args:
        filename: Data filename

    Returns:
        Full path
    """
    return get_portable_mode().get_data_path(filename)
