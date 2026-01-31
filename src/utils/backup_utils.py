"""Backup helpers for local + OneDrive destinations."""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..security.security_utils import validate_file_operation

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BackupTargets:
    local_dir: Path
    onedrive_dir: Optional[Path]


def _get_cfg(cfg: Optional[dict], *keys: str, default: Any = None) -> Any:
    if cfg is None:
        return default
    current: Any = cfg
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _resolve_onedrive_root() -> Optional[Path]:
    for env_key in ("OneDriveCommercial", "OneDriveConsumer", "OneDrive"):
        value = os.environ.get(env_key, "").strip()
        if value:
            candidate = Path(value).expanduser()
            if candidate.exists():
                return candidate
    fallback = Path.home() / "OneDrive"
    if fallback.exists():
        return fallback
    return None


def resolve_backup_targets(cfg: Optional[dict]) -> BackupTargets:
    local_dir_raw = _get_cfg(cfg, "features", "backup", "local_dir", default="cache/backups")
    local_dir = Path(str(local_dir_raw)).expanduser().resolve()

    onedrive_enabled = bool(_get_cfg(cfg, "features", "backup", "onedrive_enabled", default=True))
    onedrive_dir_raw = _get_cfg(cfg, "features", "backup", "onedrive_dir", default=None)
    onedrive_dir: Optional[Path] = None
    if onedrive_enabled:
        if onedrive_dir_raw:
            onedrive_dir = Path(str(onedrive_dir_raw)).expanduser().resolve()
        else:
            onedrive_root = _resolve_onedrive_root()
            if onedrive_root:
                onedrive_dir = onedrive_root / "ROM-Sorter-Pro" / "backups"

    return BackupTargets(local_dir=local_dir, onedrive_dir=onedrive_dir)


def _ensure_dir(path: Path) -> None:
    validate_file_operation(path, base_dir=None, allow_read=True, allow_write=True)
    path.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def backup_json(payload: Dict[str, Any], *, prefix: str, cfg: Optional[dict], log_cb=None) -> Optional[Path]:
    targets = resolve_backup_targets(cfg)
    _ensure_dir(targets.local_dir)
    filename = f"{prefix}_{_timestamp()}.json"
    local_path = targets.local_dir / filename

    try:
        with local_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        if log_cb is not None:
            log_cb(f"Backup saved: {local_path}")
    except Exception as exc:
        if log_cb is not None:
            log_cb(f"Backup failed: {exc}")
        logger.warning("Backup write failed: %s", exc)
        return None

    if targets.onedrive_dir is not None:
        try:
            _ensure_dir(targets.onedrive_dir)
            onedrive_path = targets.onedrive_dir / filename
            shutil.copy2(local_path, onedrive_path)
            if log_cb is not None:
                log_cb(f"OneDrive backup saved: {onedrive_path}")
        except Exception as exc:
            if log_cb is not None:
                log_cb(f"OneDrive backup failed: {exc}")
            logger.warning("OneDrive backup failed: %s", exc)

    return local_path


def backup_file(
    file_path: Union[str, Path],
    *,
    prefix: str,
    cfg: Optional[dict],
    log_cb=None,
) -> Optional[Path]:
    file_path_obj = Path(file_path)
    try:
        validate_file_operation(file_path_obj, base_dir=None, allow_read=True, allow_write=True)
    except Exception as exc:
        if log_cb is not None:
            log_cb(f"Backup failed: {exc}")
        logger.warning("Backup validation failed for %s: %s", file_path_obj, exc)
        return None

    if not file_path_obj.exists() or not file_path_obj.is_file():
        if log_cb is not None:
            log_cb(f"Backup skipped (missing file): {file_path_obj}")
        return None
    if file_path_obj.is_symlink():
        if log_cb is not None:
            log_cb(f"Backup skipped (symlink): {file_path_obj}")
        return None

    targets = resolve_backup_targets(cfg)
    _ensure_dir(targets.local_dir)

    filename = f"{prefix}_{_timestamp()}_{file_path_obj.name}"
    local_path = targets.local_dir / filename

    try:
        shutil.copy2(file_path_obj, local_path)
        if log_cb is not None:
            log_cb(f"Backup saved: {local_path}")
    except Exception as exc:
        if log_cb is not None:
            log_cb(f"Backup failed: {exc}")
        logger.warning("Backup copy failed: %s", exc)
        return None

    if targets.onedrive_dir is not None:
        try:
            _ensure_dir(targets.onedrive_dir)
            onedrive_path = targets.onedrive_dir / filename
            shutil.copy2(local_path, onedrive_path)
            if log_cb is not None:
                log_cb(f"OneDrive backup saved: {onedrive_path}")
        except Exception as exc:
            if log_cb is not None:
                log_cb(f"OneDrive backup failed: {exc}")
            logger.warning("OneDrive backup failed: %s", exc)

    return local_path
