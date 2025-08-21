# cleanup_project.py
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent  # Navigate from dev/scripts to project root
BACKUP_ROOT = ROOT / "backups" / "comments"
# Ensure that the backup directory exists
BACKUP_ROOT.mkdir(parents=True, exist_ok=True)

DELETE_SUFFIXES = {".pyc", ".pyo", ".tmp", ".log", ".DS_Store"}
DELETE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".idea", ".vscode"}

def cleanup():
    """
    Clean up the project directory by moving .bak files to backup folder
    and removing temporary files and directories.
    """
    print(f"[INFO] Cleaning project at {ROOT}...")

    for path in ROOT.rglob("*"):
        # Skip backups dir
        if BACKUP_ROOT in path.parents:
            continue

        # 1. Handle.bak files → Move to backup folder
        if path.suffix == ".bak" and path.is_file():
            try:
                rel = path.relative_to(ROOT)
                backup_path = BACKUP_ROOT / rel
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(backup_path))
                print(f"[MOVED] {path} -> {backup_path}")
            except Exception as e:
                print(f"[ERROR] Could not move {path}: {e}")
            continue

        # 2. Delete unwanted files
        if path.suffix in DELETE_SUFFIXES and path.is_file():
            try:
                path.unlink()
                print(f"[DELETED] {path}")
            except Exception as e:
                print(f"[ERROR] Could not delete {path}: {e}")
            continue

        # 3. Delete unwanted dirs
        if path.is_dir() and path.name in DELETE_DIRS:
            try:
                shutil.rmtree(path, ignore_errors=True)
                print(f"[DELETED DIR] {path}")
            except Exception as e:
                print(f"[ERROR] Could not delete directory {path}: {e}")
            continue

    # 4. Remove empty dirs
    for path in sorted(ROOT.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            try:
                path.rmdir()
                print(f"[EMPTY REMOVED] {path}")
            except Exception as e:
                print(f"[ERROR] Could not delete empty directory {path}: {e}")

    print("[DONE] Cleanup finished.")

if __name__ == "__main__":
    cleanup()
