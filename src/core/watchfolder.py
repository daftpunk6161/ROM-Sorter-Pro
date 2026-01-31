"""Watchfolder Auto-Sort - F65 Implementation.

Provides automatic sorting when new files appear.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class WatchEvent:
    """A file watch event."""

    path: str
    event_type: str  # created, modified, deleted, moved
    timestamp: float = field(default_factory=time.time)
    processed: bool = False
    error: str = ""


@dataclass
class WatchConfig:
    """Watchfolder configuration."""

    watch_path: str
    enabled: bool = True
    recursive: bool = True
    extensions: List[str] = field(default_factory=list)  # Empty = all
    debounce_seconds: float = 5.0  # Wait before processing
    batch_mode: bool = True  # Process multiple files at once
    auto_scan: bool = True
    auto_sort: bool = False  # Only sort after confirmation


class WatchfolderMonitor:
    """Watchfolder monitor.

    Implements F65: Watchfolder-Auto-Sort

    Features:
    - Automatic file detection
    - Debounce for batch operations
    - Configurable extensions
    - Event callbacks
    """

    CONFIG_FILENAME = "watchfolder_config.json"

    def __init__(
        self,
        config_dir: Optional[str] = None,
        on_files_detected: Optional[Callable[[List[str]], None]] = None,
    ):
        """Initialize watchfolder monitor.

        Args:
            config_dir: Configuration directory
            on_files_detected: Callback when files detected
        """
        self._config_dir = Path(config_dir) if config_dir else Path("config")
        self._on_files_detected = on_files_detected

        self._configs: Dict[str, WatchConfig] = {}
        self._watchers: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._pending_files: Dict[str, Set[str]] = {}
        self._debounce_timers: Dict[str, Optional[threading.Timer]] = {}
        self._file_states: Dict[str, Dict[str, float]] = {}
        self._event_history: List[WatchEvent] = []

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        config_file = self._config_dir / self.CONFIG_FILENAME

        if not config_file.exists():
            return

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for folder_data in data.get("folders", []):
                config = WatchConfig(
                    watch_path=folder_data["watch_path"],
                    enabled=folder_data.get("enabled", True),
                    recursive=folder_data.get("recursive", True),
                    extensions=folder_data.get("extensions", []),
                    debounce_seconds=folder_data.get("debounce_seconds", 5.0),
                    batch_mode=folder_data.get("batch_mode", True),
                    auto_scan=folder_data.get("auto_scan", True),
                    auto_sort=folder_data.get("auto_sort", False),
                )
                self._configs[config.watch_path] = config

        except Exception:
            pass

    def _save_config(self) -> None:
        """Save configuration to file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        config_file = self._config_dir / self.CONFIG_FILENAME

        data = {
            "folders": [
                {
                    "watch_path": config.watch_path,
                    "enabled": config.enabled,
                    "recursive": config.recursive,
                    "extensions": config.extensions,
                    "debounce_seconds": config.debounce_seconds,
                    "batch_mode": config.batch_mode,
                    "auto_scan": config.auto_scan,
                    "auto_sort": config.auto_sort,
                }
                for config in self._configs.values()
            ]
        }

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _scan_folder(self, path: str, config: WatchConfig) -> Dict[str, float]:
        """Scan folder for files and their modification times.

        Args:
            path: Folder path
            config: Watch configuration

        Returns:
            Dict of file path to modification time
        """
        files: Dict[str, float] = {}
        folder = Path(path)

        if not folder.exists():
            return files

        if config.recursive:
            iterator = folder.rglob("*")
        else:
            iterator = folder.glob("*")

        for file_path in iterator:
            if not file_path.is_file():
                continue

            # Check extension filter
            if config.extensions:
                ext = file_path.suffix.lower()
                if ext not in config.extensions and ext.lstrip(".") not in config.extensions:
                    continue

            try:
                files[str(file_path)] = file_path.stat().st_mtime
            except Exception:
                pass

        return files

    def _check_for_changes(self, watch_path: str) -> None:
        """Check for file changes in watched folder.

        Args:
            watch_path: Watched folder path
        """
        config = self._configs.get(watch_path)
        if not config or not config.enabled:
            return

        current_files = self._scan_folder(watch_path, config)
        previous_files = self._file_states.get(watch_path, {})

        new_files: Set[str] = set()
        modified_files: Set[str] = set()

        # Check for new/modified files
        for file_path, mtime in current_files.items():
            if file_path not in previous_files:
                new_files.add(file_path)
                self._add_event(file_path, "created")
            elif mtime > previous_files[file_path]:
                modified_files.add(file_path)
                self._add_event(file_path, "modified")

        # Check for deleted files
        for file_path in previous_files:
            if file_path not in current_files:
                self._add_event(file_path, "deleted")

        # Update state
        self._file_states[watch_path] = current_files

        # Queue changed files for processing
        changed = new_files | modified_files
        if changed:
            self._queue_files(watch_path, changed)

    def _add_event(self, path: str, event_type: str) -> None:
        """Add event to history.

        Args:
            path: File path
            event_type: Event type
        """
        event = WatchEvent(path=path, event_type=event_type)
        self._event_history.append(event)

        # Keep last 1000 events
        if len(self._event_history) > 1000:
            self._event_history = self._event_history[-1000:]

    def _queue_files(self, watch_path: str, files: Set[str]) -> None:
        """Queue files for processing with debounce.

        Args:
            watch_path: Watch path
            files: Files to queue
        """
        if watch_path not in self._pending_files:
            self._pending_files[watch_path] = set()

        self._pending_files[watch_path].update(files)

        config = self._configs.get(watch_path)
        if not config:
            return

        # Cancel existing debounce timer
        existing_timer = self._debounce_timers.get(watch_path)
        if existing_timer:
            existing_timer.cancel()

        # Set new debounce timer
        timer = threading.Timer(
            config.debounce_seconds,
            self._process_pending_files,
            args=[watch_path],
        )
        timer.daemon = True
        timer.start()
        self._debounce_timers[watch_path] = timer

    def _process_pending_files(self, watch_path: str) -> None:
        """Process pending files after debounce.

        Args:
            watch_path: Watch path
        """
        files = self._pending_files.pop(watch_path, set())
        if not files:
            return

        # Filter to only existing files
        existing = [f for f in files if Path(f).exists()]

        if existing and self._on_files_detected:
            try:
                self._on_files_detected(existing)
            except Exception:
                pass

    def _watch_loop(self, watch_path: str, stop_event: threading.Event) -> None:
        """Watch loop for a folder.

        Args:
            watch_path: Path to watch
            stop_event: Stop event
        """
        # Initial scan
        config = self._configs.get(watch_path)
        if config:
            self._file_states[watch_path] = self._scan_folder(watch_path, config)

        while not stop_event.is_set():
            try:
                self._check_for_changes(watch_path)
            except Exception:
                pass

            # Poll interval
            stop_event.wait(2.0)

    def add_watchfolder(self, config: WatchConfig) -> bool:
        """Add a watchfolder.

        Args:
            config: Watch configuration

        Returns:
            True if added
        """
        if not Path(config.watch_path).exists():
            return False

        self._configs[config.watch_path] = config
        self._save_config()

        if config.enabled:
            self.start_watching(config.watch_path)

        return True

    def remove_watchfolder(self, watch_path: str) -> bool:
        """Remove a watchfolder.

        Args:
            watch_path: Path to remove

        Returns:
            True if removed
        """
        if watch_path not in self._configs:
            return False

        self.stop_watching(watch_path)

        del self._configs[watch_path]
        self._file_states.pop(watch_path, None)
        self._pending_files.pop(watch_path, None)

        self._save_config()

        return True

    def start_watching(self, watch_path: str) -> bool:
        """Start watching a folder.

        Args:
            watch_path: Path to watch

        Returns:
            True if started
        """
        if watch_path in self._watchers:
            return True  # Already watching

        config = self._configs.get(watch_path)
        if not config:
            return False

        stop_event = threading.Event()
        self._stop_events[watch_path] = stop_event

        thread = threading.Thread(
            target=self._watch_loop,
            args=(watch_path, stop_event),
            daemon=True,
        )
        thread.start()
        self._watchers[watch_path] = thread

        return True

    def stop_watching(self, watch_path: str) -> bool:
        """Stop watching a folder.

        Args:
            watch_path: Path to stop

        Returns:
            True if stopped
        """
        if watch_path not in self._watchers:
            return True

        # Signal stop
        stop_event = self._stop_events.get(watch_path)
        if stop_event:
            stop_event.set()

        # Cancel debounce timer
        timer = self._debounce_timers.get(watch_path)
        if timer:
            timer.cancel()

        # Wait for thread
        thread = self._watchers.get(watch_path)
        if thread:
            thread.join(timeout=5.0)

        # Cleanup
        self._watchers.pop(watch_path, None)
        self._stop_events.pop(watch_path, None)
        self._debounce_timers.pop(watch_path, None)

        return True

    def start_all(self) -> int:
        """Start all enabled watchfolders.

        Returns:
            Number started
        """
        started = 0

        for path, config in self._configs.items():
            if config.enabled and self.start_watching(path):
                started += 1

        return started

    def stop_all(self) -> int:
        """Stop all watchfolders.

        Returns:
            Number stopped
        """
        stopped = 0

        for path in list(self._watchers.keys()):
            if self.stop_watching(path):
                stopped += 1

        return stopped

    def get_watchfolders(self) -> List[Dict[str, Any]]:
        """Get all watchfolder configurations.

        Returns:
            List of config dicts
        """
        result = []

        for path, config in self._configs.items():
            result.append(
                {
                    "watch_path": config.watch_path,
                    "enabled": config.enabled,
                    "recursive": config.recursive,
                    "extensions": config.extensions,
                    "debounce_seconds": config.debounce_seconds,
                    "auto_scan": config.auto_scan,
                    "auto_sort": config.auto_sort,
                    "is_watching": path in self._watchers,
                    "pending_count": len(self._pending_files.get(path, set())),
                }
            )

        return result

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent watch events.

        Args:
            limit: Maximum events

        Returns:
            List of event dicts
        """
        events = self._event_history[-limit:]

        return [
            {
                "path": e.path,
                "event_type": e.event_type,
                "timestamp": e.timestamp,
                "processed": e.processed,
            }
            for e in reversed(events)
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get overall status.

        Returns:
            Status dict
        """
        return {
            "total_watchfolders": len(self._configs),
            "active_watchers": len(self._watchers),
            "pending_files": sum(
                len(files) for files in self._pending_files.values()
            ),
            "total_events": len(self._event_history),
        }

    def set_callback(
        self, callback: Callable[[List[str]], None]
    ) -> None:
        """Set files detected callback.

        Args:
            callback: Callback function
        """
        self._on_files_detected = callback
