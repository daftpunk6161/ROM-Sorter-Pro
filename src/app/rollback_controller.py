"""Rollback support for move operations."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from ..security.security_utils import InvalidPathError, validate_file_operation
from .execute_helpers import atomic_copy_with_cancel
from .models import CancelToken
from .security_helpers import has_symlink_parent


@dataclass(frozen=True)
class RollbackEntry:
    source_path: str
    dest_path: str


@dataclass(frozen=True)
class RollbackManifest:
    created_at: float
    entries: List[RollbackEntry]


@dataclass(frozen=True)
class RollbackReport:
    processed: int
    restored: int
    skipped: int
    errors: List[str]
    cancelled: bool


def write_rollback_manifest(entries: List[RollbackEntry], path: str) -> None:
    payload = {
        "created_at": time.time(),
        "entries": [{"source_path": e.source_path, "dest_path": e.dest_path} for e in entries],
    }
    target = Path(path)
    validate_file_operation(target, base_dir=None, allow_read=True, allow_write=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def load_rollback_manifest(path: str) -> RollbackManifest:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    entries = [RollbackEntry(**item) for item in payload.get("entries", [])]
    return RollbackManifest(created_at=float(payload.get("created_at", 0.0)), entries=entries)


def apply_rollback(
    path: str,
    *,
    cancel_token: Optional[CancelToken] = None,
    log_cb=None,
) -> RollbackReport:
    manifest = load_rollback_manifest(path)
    processed = 0
    restored = 0
    skipped = 0
    errors: List[str] = []
    cancelled = False

    for entry in manifest.entries:
        if cancel_token is not None and cancel_token.is_cancelled():
            cancelled = True
            break

        processed += 1
        src_raw = Path(entry.source_path)
        dst_raw = Path(entry.dest_path)

        try:
            if src_raw.exists():
                skipped += 1
                if log_cb is not None:
                    log_cb(f"Rollback skipped (source exists): {src_raw}")
                continue
            if not dst_raw.exists():
                skipped += 1
                if log_cb is not None:
                    log_cb(f"Rollback skipped (dest missing): {dst_raw}")
                continue

            if dst_raw.is_symlink():
                raise InvalidPathError(f"Symlink destination not allowed: {dst_raw}")
            if has_symlink_parent(dst_raw):
                raise InvalidPathError(f"Symlink parent not allowed: {dst_raw}")

            validate_file_operation(dst_raw, base_dir=None, allow_read=True, allow_write=True)
            validate_file_operation(src_raw, base_dir=None, allow_read=True, allow_write=True)

            src_raw.parent.mkdir(parents=True, exist_ok=True)

            try:
                os.replace(str(dst_raw), str(src_raw))
            except OSError as exc:
                ok = atomic_copy_with_cancel(dst_raw, src_raw, allow_replace=True, cancel_token=cancel_token)
                if not ok:
                    cancelled = True
                    break
                try:
                    dst_raw.unlink()
                except Exception:
                    os.remove(str(dst_raw))
            restored += 1
            if log_cb is not None:
                log_cb(f"Rollback moved: {dst_raw} -> {src_raw}")
        except Exception as exc:
            msg = f"Rollback failed for {dst_raw}: {exc}"
            errors.append(msg)
            if log_cb is not None:
                log_cb(msg)

    return RollbackReport(
        processed=processed,
        restored=restored,
        skipped=skipped,
        errors=errors,
        cancelled=cancelled,
    )
