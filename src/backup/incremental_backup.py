"""Incremental Backup - F94 Implementation.

Provides incremental backup functionality for ROM collections.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class FileEntry:
    """A file entry in the manifest."""

    path: str
    size: int
    mtime: float
    hash: str = ""
    backed_up: bool = False
    backup_path: str = ""


@dataclass
class BackupManifest:
    """Backup manifest tracking file states."""

    version: int = 1
    created: float = 0.0
    updated: float = 0.0
    source_path: str = ""
    backup_path: str = ""
    total_files: int = 0
    total_size_bytes: int = 0
    files: Dict[str, FileEntry] = field(default_factory=dict)

    @property
    def created_date(self) -> datetime:
        """Get created datetime."""
        return datetime.fromtimestamp(self.created)

    @property
    def updated_date(self) -> datetime:
        """Get updated datetime."""
        return datetime.fromtimestamp(self.updated)


@dataclass
class BackupResult:
    """Result of backup operation."""

    success: bool
    new_files: int = 0
    modified_files: int = 0
    unchanged_files: int = 0
    deleted_files: int = 0
    bytes_backed_up: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    manifest_path: str = ""


class IncrementalBackup:
    """Incremental backup system.

    Implements F94: Inkrementelles Backup

    Features:
    - Only backup changed files
    - Hash-based change detection
    - Manifest tracking
    - Restore capability
    """

    MANIFEST_FILENAME = "backup_manifest.json"
    HASH_ALGORITHM = "sha256"

    def __init__(
        self,
        source_path: str,
        backup_path: str,
        use_hash: bool = True,
    ):
        """Initialize incremental backup.

        Args:
            source_path: Source directory to backup
            backup_path: Backup destination
            use_hash: Use file hashes for comparison
        """
        self._source = Path(source_path)
        self._backup = Path(backup_path)
        self._use_hash = use_hash
        self._manifest: Optional[BackupManifest] = None

        self._backup.mkdir(parents=True, exist_ok=True)

    def _load_manifest(self) -> BackupManifest:
        """Load or create manifest."""
        manifest_path = self._backup / self.MANIFEST_FILENAME

        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                manifest = BackupManifest(
                    version=data.get("version", 1),
                    created=data.get("created", 0),
                    updated=data.get("updated", 0),
                    source_path=data.get("source_path", ""),
                    backup_path=data.get("backup_path", ""),
                    total_files=data.get("total_files", 0),
                    total_size_bytes=data.get("total_size_bytes", 0),
                )

                for path, entry_data in data.get("files", {}).items():
                    manifest.files[path] = FileEntry(
                        path=entry_data.get("path", ""),
                        size=entry_data.get("size", 0),
                        mtime=entry_data.get("mtime", 0),
                        hash=entry_data.get("hash", ""),
                        backed_up=entry_data.get("backed_up", False),
                        backup_path=entry_data.get("backup_path", ""),
                    )

                return manifest

            except Exception:
                pass

        # Create new manifest
        return BackupManifest(
            created=time.time(),
            source_path=str(self._source),
            backup_path=str(self._backup),
        )

    def _save_manifest(self, manifest: BackupManifest) -> None:
        """Save manifest to file."""
        manifest.updated = time.time()
        manifest_path = self._backup / self.MANIFEST_FILENAME

        data = {
            "version": manifest.version,
            "created": manifest.created,
            "updated": manifest.updated,
            "source_path": manifest.source_path,
            "backup_path": manifest.backup_path,
            "total_files": manifest.total_files,
            "total_size_bytes": manifest.total_size_bytes,
            "files": {
                path: {
                    "path": entry.path,
                    "size": entry.size,
                    "mtime": entry.mtime,
                    "hash": entry.hash,
                    "backed_up": entry.backed_up,
                    "backup_path": entry.backup_path,
                }
                for path, entry in manifest.files.items()
            },
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _hash_file(self, path: Path) -> str:
        """Calculate file hash."""
        hasher = hashlib.new(self.HASH_ALGORITHM)

        with open(path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)

        return hasher.hexdigest()

    def _scan_source(self) -> Dict[str, FileEntry]:
        """Scan source directory for files."""
        files: Dict[str, FileEntry] = {}

        for root, _, filenames in os.walk(self._source):
            for filename in filenames:
                full_path = Path(root) / filename
                rel_path = str(full_path.relative_to(self._source))

                try:
                    stat = full_path.stat()
                    files[rel_path] = FileEntry(
                        path=rel_path,
                        size=stat.st_size,
                        mtime=stat.st_mtime,
                    )
                except Exception:
                    pass

        return files

    def _file_changed(
        self,
        current: FileEntry,
        previous: Optional[FileEntry],
    ) -> bool:
        """Check if file has changed."""
        if not previous:
            return True

        # Size changed
        if current.size != previous.size:
            return True

        # Modification time changed
        if current.mtime > previous.mtime:
            return True

        return False

    def backup(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> BackupResult:
        """Run incremental backup.

        Args:
            progress_callback: Progress callback(current, total, filename)
            cancel_token: Cancellation token with .is_set()

        Returns:
            BackupResult
        """
        start_time = time.time()
        result = BackupResult(success=True)

        # Load existing manifest
        manifest = self._load_manifest()

        # Scan source
        current_files = self._scan_source()

        # Detect deleted files
        deleted_paths = set(manifest.files.keys()) - set(current_files.keys())
        for path in deleted_paths:
            result.deleted_files += 1
            del manifest.files[path]

        # Process files
        total = len(current_files)
        processed = 0

        for rel_path, current_entry in current_files.items():
            # Check cancellation
            if cancel_token and hasattr(cancel_token, "is_set") and cancel_token.is_set():
                result.success = False
                result.errors.append("Backup cancelled")
                break

            processed += 1
            if progress_callback:
                progress_callback(processed, total, rel_path)

            previous_entry = manifest.files.get(rel_path)

            # Check if file changed
            if not self._file_changed(current_entry, previous_entry):
                result.unchanged_files += 1
                continue

            # Calculate hash if needed
            source_file = self._source / rel_path
            if self._use_hash:
                try:
                    current_entry.hash = self._hash_file(source_file)

                    # Double-check with hash
                    if previous_entry and current_entry.hash == previous_entry.hash:
                        result.unchanged_files += 1
                        continue
                except Exception:
                    pass

            # Determine backup path
            backup_file = self._backup / "files" / rel_path
            backup_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            try:
                shutil.copy2(source_file, backup_file)
                current_entry.backed_up = True
                current_entry.backup_path = str(backup_file.relative_to(self._backup))

                if previous_entry:
                    result.modified_files += 1
                else:
                    result.new_files += 1

                result.bytes_backed_up += current_entry.size

            except Exception as e:
                result.errors.append(f"Failed to backup {rel_path}: {e}")

            # Update manifest
            manifest.files[rel_path] = current_entry

        # Update manifest totals
        manifest.total_files = len(manifest.files)
        manifest.total_size_bytes = sum(e.size for e in manifest.files.values())

        # Save manifest
        self._save_manifest(manifest)
        result.manifest_path = str(self._backup / self.MANIFEST_FILENAME)

        result.duration_seconds = time.time() - start_time
        result.success = len(result.errors) == 0

        self._manifest = manifest
        return result

    def restore(
        self,
        target_path: Optional[str] = None,
        files: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> BackupResult:
        """Restore from backup.

        Args:
            target_path: Restore target (default: original source)
            files: Specific files to restore (default: all)
            progress_callback: Progress callback

        Returns:
            BackupResult
        """
        start_time = time.time()
        result = BackupResult(success=True)

        manifest = self._load_manifest()
        target = Path(target_path) if target_path else self._source

        files_to_restore = files or list(manifest.files.keys())
        total = len(files_to_restore)

        for i, rel_path in enumerate(files_to_restore):
            if progress_callback:
                progress_callback(i + 1, total, rel_path)

            if rel_path not in manifest.files:
                result.errors.append(f"File not in backup: {rel_path}")
                continue

            entry = manifest.files[rel_path]
            if not entry.backed_up or not entry.backup_path:
                result.errors.append(f"File not backed up: {rel_path}")
                continue

            backup_file = self._backup / entry.backup_path
            target_file = target / rel_path

            if not backup_file.exists():
                result.errors.append(f"Backup file missing: {rel_path}")
                continue

            try:
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, target_file)
                result.new_files += 1
                result.bytes_backed_up += entry.size

            except Exception as e:
                result.errors.append(f"Failed to restore {rel_path}: {e}")

        result.duration_seconds = time.time() - start_time
        result.success = len(result.errors) == 0

        return result

    def get_status(self) -> Dict[str, Any]:
        """Get backup status.

        Returns:
            Status dict
        """
        manifest = self._load_manifest()

        return {
            "source_path": manifest.source_path,
            "backup_path": manifest.backup_path,
            "total_files": manifest.total_files,
            "total_size_mb": manifest.total_size_bytes / (1024 * 1024),
            "last_backup": manifest.updated_date.isoformat() if manifest.updated else None,
            "first_backup": manifest.created_date.isoformat() if manifest.created else None,
        }

    def get_changed_files(self) -> List[str]:
        """Get list of files that have changed since last backup.

        Returns:
            List of changed file paths
        """
        manifest = self._load_manifest()
        current_files = self._scan_source()

        changed = []
        for rel_path, current_entry in current_files.items():
            previous = manifest.files.get(rel_path)
            if self._file_changed(current_entry, previous):
                changed.append(rel_path)

        return changed

    def verify_backup(self) -> Dict[str, Any]:
        """Verify backup integrity.

        Returns:
            Verification result
        """
        manifest = self._load_manifest()

        result = {
            "valid": True,
            "total_files": len(manifest.files),
            "missing_files": [],
            "hash_mismatches": [],
            "verified": 0,
        }

        for rel_path, entry in manifest.files.items():
            if not entry.backed_up:
                continue

            backup_file = self._backup / entry.backup_path
            if not backup_file.exists():
                result["missing_files"].append(rel_path)
                result["valid"] = False
                continue

            if self._use_hash and entry.hash:
                try:
                    current_hash = self._hash_file(backup_file)
                    if current_hash != entry.hash:
                        result["hash_mismatches"].append(rel_path)
                        result["valid"] = False
                        continue
                except Exception:
                    pass

            result["verified"] += 1

        return result

    def cleanup_old_versions(self, keep_count: int = 5) -> int:
        """Clean up old backup versions.

        Args:
            keep_count: Number of versions to keep

        Returns:
            Number of files removed
        """
        # This is a simplified implementation
        # Full implementation would track versions
        return 0
