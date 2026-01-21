"""ROM Sorter Pro - DB controller helpers (MVP)."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..database.db_paths import get_rom_db_path
from ..exceptions import ProcessingError


def _resolve_db_path(db_path: Optional[str] = None) -> Path:
    path = Path(db_path or get_rom_db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_update_module():
    repo_root = Path(__file__).resolve().parents[2]
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    from scripts import update_rom_database

    return update_rom_database


def init_db(db_path: Optional[str] = None) -> Path:
    """Initialize the unified DB schema and return the DB path."""
    path = _resolve_db_path(db_path)
    try:
        module = _load_update_module()
        conn = module.setup_database(str(path))
        conn.close()
        return path
    except Exception as exc:
        raise ProcessingError(f"DB init failed: {exc}") from exc


def migrate_db(db_path: Optional[str] = None) -> bool:
    """Run schema migration for the unified DB."""
    path = _resolve_db_path(db_path)
    try:
        module = _load_update_module()
        return bool(module.update_rom_database(str(path)))
    except Exception as exc:
        raise ProcessingError(f"DB migration failed: {exc}") from exc


def backup_db(db_path: Optional[str] = None) -> Path:
    """Create a timestamped backup of the DB and return the backup path."""
    path = _resolve_db_path(db_path)
    if not path.exists():
        raise ProcessingError("DB backup failed: database not found")

    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"roms_{stamp}.db"
    shutil.copy2(path, backup_path)
    return backup_path


def scan_roms(directory: str, *, db_path: Optional[str] = None, recursive: bool = True) -> int:
    """Scan a directory and add ROMs to the DB. Returns number of ROMs added."""
    path = _resolve_db_path(db_path)
    try:
        module = _load_update_module()
        conn = module.setup_database(str(path))
        count = module.scan_directory(conn, directory, recursive=recursive)
        conn.close()
        return int(count)
    except Exception as exc:
        raise ProcessingError(f"DB scan failed: {exc}") from exc


def import_dat(dat_file: str, *, db_path: Optional[str] = None) -> int:
    """Import DAT metadata into the DB. Returns number of ROMs updated."""
    path = _resolve_db_path(db_path)
    try:
        module = _load_update_module()
        conn = module.setup_database(str(path))
        count = module.import_dat_file(conn, dat_file)
        conn.close()
        return int(count)
    except Exception as exc:
        raise ProcessingError(f"DAT import failed: {exc}") from exc
