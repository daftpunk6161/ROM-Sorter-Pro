"""Cloud Sync Support - F95 Implementation.

Provides cloud synchronization for ROM metadata and collections.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class SyncProvider(Enum):
    """Supported cloud providers."""

    LOCAL = auto()  # Local/NAS path
    ONEDRIVE = auto()
    DROPBOX = auto()
    GOOGLE_DRIVE = auto()
    SMB = auto()  # Network share


@dataclass
class SyncConfig:
    """Cloud sync configuration."""

    provider: SyncProvider = SyncProvider.LOCAL
    cloud_path: str = ""
    local_path: str = ""
    sync_metadata_only: bool = True  # Only sync metadata, not ROMs
    sync_interval_minutes: int = 60
    auto_sync: bool = False
    conflict_resolution: str = "newest"  # newest, local, remote, ask


@dataclass
class SyncResult:
    """Result of sync operation."""

    success: bool
    uploaded: int = 0
    downloaded: int = 0
    conflicts: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass
class SyncState:
    """File sync state."""

    path: str
    local_mtime: float = 0.0
    remote_mtime: float = 0.0
    local_hash: str = ""
    remote_hash: str = ""
    last_synced: float = 0.0
    synced: bool = False


class CloudSync:
    """Cloud synchronization for ROM collections.

    Implements F95: Cloud-Sync-Support

    Features:
    - Multiple cloud providers
    - Metadata-only or full sync
    - Conflict resolution
    - Incremental sync
    """

    STATE_FILENAME = ".sync_state.json"
    METADATA_FILES = [
        "*.json",
        "*.yaml",
        "*.yml",
        "*.xml",
        "gamelist.xml",
        "*.m3u",
    ]

    def __init__(self, config: SyncConfig):
        """Initialize cloud sync.

        Args:
            config: Sync configuration
        """
        self._config = config
        self._local = Path(config.local_path) if config.local_path else None
        self._remote = Path(config.cloud_path) if config.cloud_path else None
        self._state: Dict[str, SyncState] = {}

        self._load_state()

    def _load_state(self) -> None:
        """Load sync state from file."""
        if not self._local:
            return

        state_file = self._local / self.STATE_FILENAME
        if not state_file.exists():
            return

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for path, entry in data.get("files", {}).items():
                self._state[path] = SyncState(
                    path=entry.get("path", ""),
                    local_mtime=entry.get("local_mtime", 0),
                    remote_mtime=entry.get("remote_mtime", 0),
                    local_hash=entry.get("local_hash", ""),
                    remote_hash=entry.get("remote_hash", ""),
                    last_synced=entry.get("last_synced", 0),
                    synced=entry.get("synced", False),
                )
        except Exception:
            pass

    def _save_state(self) -> None:
        """Save sync state to file."""
        if not self._local:
            return

        state_file = self._local / self.STATE_FILENAME

        data = {
            "updated": time.time(),
            "provider": self._config.provider.name,
            "files": {
                path: {
                    "path": state.path,
                    "local_mtime": state.local_mtime,
                    "remote_mtime": state.remote_mtime,
                    "local_hash": state.local_hash,
                    "remote_hash": state.remote_hash,
                    "last_synced": state.last_synced,
                    "synced": state.synced,
                }
                for path, state in self._state.items()
            },
        }

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _hash_file(self, path: Path) -> str:
        """Calculate file hash."""
        hasher = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    def _is_metadata_file(self, path: Path) -> bool:
        """Check if file is metadata."""
        name = path.name.lower()
        suffix = path.suffix.lower()

        metadata_suffixes = {".json", ".yaml", ".yml", ".xml", ".m3u", ".txt"}
        if suffix in metadata_suffixes:
            return True

        metadata_names = {"gamelist.xml", "metadata.txt", "config.json"}
        if name in metadata_names:
            return True

        return False

    def _scan_local(self) -> Dict[str, SyncState]:
        """Scan local files."""
        files: Dict[str, SyncState] = {}

        if not self._local or not self._local.exists():
            return files

        for root, _, filenames in os.walk(self._local):
            for filename in filenames:
                if filename.startswith("."):
                    continue

                full_path = Path(root) / filename

                # Skip non-metadata in metadata-only mode
                if self._config.sync_metadata_only and not self._is_metadata_file(
                    full_path
                ):
                    continue

                rel_path = str(full_path.relative_to(self._local))

                try:
                    stat = full_path.stat()
                    files[rel_path] = SyncState(
                        path=rel_path,
                        local_mtime=stat.st_mtime,
                        local_hash=self._hash_file(full_path),
                    )
                except Exception:
                    pass

        return files

    def _scan_remote(self) -> Dict[str, SyncState]:
        """Scan remote files."""
        files: Dict[str, SyncState] = {}

        if not self._remote or not self._remote.exists():
            return files

        # For local/NAS providers, scan directly
        if self._config.provider in (SyncProvider.LOCAL, SyncProvider.SMB):
            for root, _, filenames in os.walk(self._remote):
                for filename in filenames:
                    if filename.startswith("."):
                        continue

                    full_path = Path(root) / filename

                    if self._config.sync_metadata_only and not self._is_metadata_file(
                        full_path
                    ):
                        continue

                    rel_path = str(full_path.relative_to(self._remote))

                    try:
                        stat = full_path.stat()
                        files[rel_path] = SyncState(
                            path=rel_path,
                            remote_mtime=stat.st_mtime,
                            remote_hash=self._hash_file(full_path),
                        )
                    except Exception:
                        pass

        # For cloud providers, would use their APIs
        # OneDrive: Microsoft Graph API
        # Dropbox: Dropbox API
        # Google Drive: Google Drive API

        return files

    def _resolve_conflict(
        self,
        local_state: SyncState,
        remote_state: SyncState,
    ) -> str:
        """Resolve sync conflict.

        Returns:
            "upload", "download", or "skip"
        """
        resolution = self._config.conflict_resolution

        if resolution == "local":
            return "upload"
        elif resolution == "remote":
            return "download"
        elif resolution == "newest":
            if local_state.local_mtime > remote_state.remote_mtime:
                return "upload"
            else:
                return "download"

        return "skip"

    def _upload_file(self, rel_path: str) -> bool:
        """Upload file to remote."""
        if not self._local or not self._remote:
            return False

        local_file = self._local / rel_path
        remote_file = self._remote / rel_path

        try:
            remote_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_file, remote_file)
            return True
        except Exception:
            return False

    def _download_file(self, rel_path: str) -> bool:
        """Download file from remote."""
        if not self._local or not self._remote:
            return False

        local_file = self._local / rel_path
        remote_file = self._remote / rel_path

        try:
            local_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(remote_file, local_file)
            return True
        except Exception:
            return False

    def sync(
        self,
        direction: str = "both",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> SyncResult:
        """Run synchronization.

        Args:
            direction: "upload", "download", or "both"
            progress_callback: Progress callback(current, total, filename)
            cancel_token: Cancellation token

        Returns:
            SyncResult
        """
        start_time = time.time()
        result = SyncResult(success=True)

        # Scan files
        local_files = self._scan_local()
        remote_files = self._scan_remote()

        # Determine actions
        actions: List[tuple[str, str]] = []  # (path, action)

        all_paths = set(local_files.keys()) | set(remote_files.keys())

        for path in all_paths:
            local = local_files.get(path)
            remote = remote_files.get(path)

            if local and not remote:
                # Only local - upload
                if direction in ("upload", "both"):
                    actions.append((path, "upload"))

            elif remote and not local:
                # Only remote - download
                if direction in ("download", "both"):
                    actions.append((path, "download"))

            else:
                # Both exist - check for changes
                previous = self._state.get(path)

                if local and remote:
                    # Check if either changed since last sync
                    local_changed = (
                        not previous
                        or local.local_mtime > previous.last_synced
                        or local.local_hash != previous.local_hash
                    )
                    remote_changed = (
                        not previous
                        or remote.remote_mtime > previous.last_synced
                        or remote.remote_hash != previous.remote_hash
                    )

                    if local_changed and remote_changed:
                        # Conflict
                        action = self._resolve_conflict(local, remote)
                        if action != "skip":
                            actions.append((path, action))
                        else:
                            result.conflicts += 1

                    elif local_changed and direction in ("upload", "both"):
                        actions.append((path, "upload"))

                    elif remote_changed and direction in ("download", "both"):
                        actions.append((path, "download"))

        # Execute actions
        total = len(actions)
        for i, (path, action) in enumerate(actions):
            # Check cancellation
            if cancel_token and hasattr(cancel_token, "is_set") and cancel_token.is_set():
                result.success = False
                result.errors.append("Sync cancelled")
                break

            if progress_callback:
                progress_callback(i + 1, total, path)

            if action == "upload":
                if self._upload_file(path):
                    result.uploaded += 1

                    # Update state
                    local = local_files.get(path)
                    if local:
                        local.last_synced = time.time()
                        local.synced = True
                        self._state[path] = local
                else:
                    result.errors.append(f"Failed to upload: {path}")

            elif action == "download":
                if self._download_file(path):
                    result.downloaded += 1

                    # Update state
                    remote = remote_files.get(path)
                    if remote:
                        remote.last_synced = time.time()
                        remote.synced = True
                        self._state[path] = remote
                else:
                    result.errors.append(f"Failed to download: {path}")

        # Save state
        self._save_state()

        result.duration_seconds = time.time() - start_time
        result.success = len(result.errors) == 0

        return result

    def upload(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> SyncResult:
        """Upload local changes to remote.

        Args:
            progress_callback: Progress callback

        Returns:
            SyncResult
        """
        return self.sync(direction="upload", progress_callback=progress_callback)

    def download(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> SyncResult:
        """Download remote changes to local.

        Args:
            progress_callback: Progress callback

        Returns:
            SyncResult
        """
        return self.sync(direction="download", progress_callback=progress_callback)

    def get_status(self) -> Dict[str, Any]:
        """Get sync status.

        Returns:
            Status dict
        """
        local_files = self._scan_local()
        remote_files = self._scan_remote()

        pending_uploads = 0
        pending_downloads = 0
        in_sync = 0

        all_paths = set(local_files.keys()) | set(remote_files.keys())

        for path in all_paths:
            local = local_files.get(path)
            remote = remote_files.get(path)
            previous = self._state.get(path)

            if local and not remote:
                pending_uploads += 1
            elif remote and not local:
                pending_downloads += 1
            elif local and remote and previous:
                if local.local_hash == remote.remote_hash:
                    in_sync += 1
                else:
                    # Conflict or change
                    if local.local_mtime > previous.last_synced:
                        pending_uploads += 1
                    if remote.remote_mtime > previous.last_synced:
                        pending_downloads += 1
            elif local and remote:
                # No previous state
                if local.local_hash == remote.remote_hash:
                    in_sync += 1
                else:
                    pending_uploads += 1

        return {
            "provider": self._config.provider.name,
            "local_path": str(self._local) if self._local else None,
            "remote_path": str(self._remote) if self._remote else None,
            "metadata_only": self._config.sync_metadata_only,
            "total_files": len(all_paths),
            "in_sync": in_sync,
            "pending_uploads": pending_uploads,
            "pending_downloads": pending_downloads,
            "last_sync": max(
                (s.last_synced for s in self._state.values()),
                default=0,
            ),
        }

    def get_conflicts(self) -> List[Dict[str, Any]]:
        """Get list of conflicting files.

        Returns:
            List of conflict info
        """
        conflicts = []

        local_files = self._scan_local()
        remote_files = self._scan_remote()

        for path in set(local_files.keys()) & set(remote_files.keys()):
            local = local_files[path]
            remote = remote_files[path]
            previous = self._state.get(path)

            if not previous:
                if local.local_hash != remote.remote_hash:
                    conflicts.append(
                        {
                            "path": path,
                            "local_mtime": datetime.fromtimestamp(
                                local.local_mtime
                            ).isoformat(),
                            "remote_mtime": datetime.fromtimestamp(
                                remote.remote_mtime
                            ).isoformat(),
                            "reason": "Both modified since last sync",
                        }
                    )
            else:
                local_changed = (
                    local.local_mtime > previous.last_synced
                    or local.local_hash != previous.local_hash
                )
                remote_changed = (
                    remote.remote_mtime > previous.last_synced
                    or remote.remote_hash != previous.remote_hash
                )

                if local_changed and remote_changed:
                    conflicts.append(
                        {
                            "path": path,
                            "local_mtime": datetime.fromtimestamp(
                                local.local_mtime
                            ).isoformat(),
                            "remote_mtime": datetime.fromtimestamp(
                                remote.remote_mtime
                            ).isoformat(),
                            "reason": "Both modified since last sync",
                        }
                    )

        return conflicts


def create_onedrive_sync(
    local_path: str,
    onedrive_folder: str = "ROM-Sorter",
) -> CloudSync:
    """Create OneDrive sync helper.

    Args:
        local_path: Local collection path
        onedrive_folder: OneDrive subfolder name

    Returns:
        CloudSync instance
    """
    # Find OneDrive path (Windows)
    onedrive_root = os.environ.get("OneDrive", "")
    if not onedrive_root:
        # Try default location
        home = os.path.expanduser("~")
        for folder in ["OneDrive", "OneDrive - Personal"]:
            candidate = os.path.join(home, folder)
            if os.path.exists(candidate):
                onedrive_root = candidate
                break

    if not onedrive_root:
        raise ValueError("OneDrive not found")

    config = SyncConfig(
        provider=SyncProvider.ONEDRIVE,
        local_path=local_path,
        cloud_path=os.path.join(onedrive_root, onedrive_folder),
        sync_metadata_only=True,
    )

    return CloudSync(config)


def create_dropbox_sync(
    local_path: str,
    dropbox_folder: str = "ROM-Sorter",
) -> CloudSync:
    """Create Dropbox sync helper.

    Args:
        local_path: Local collection path
        dropbox_folder: Dropbox subfolder name

    Returns:
        CloudSync instance
    """
    # Find Dropbox path
    home = os.path.expanduser("~")
    dropbox_root = os.path.join(home, "Dropbox")

    if not os.path.exists(dropbox_root):
        raise ValueError("Dropbox not found")

    config = SyncConfig(
        provider=SyncProvider.DROPBOX,
        local_path=local_path,
        cloud_path=os.path.join(dropbox_root, dropbox_folder),
        sync_metadata_only=True,
    )

    return CloudSync(config)


def create_nas_sync(
    local_path: str,
    nas_path: str,
) -> CloudSync:
    """Create NAS/SMB sync.

    Args:
        local_path: Local collection path
        nas_path: NAS/network path

    Returns:
        CloudSync instance
    """
    config = SyncConfig(
        provider=SyncProvider.SMB,
        local_path=local_path,
        cloud_path=nas_path,
        sync_metadata_only=False,  # Full sync for NAS
    )

    return CloudSync(config)
