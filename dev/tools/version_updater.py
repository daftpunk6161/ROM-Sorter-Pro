#!/usr/bin/env python3
"""
ROM Sorter Pro - Version Updater Tool

This script finds and updates all occurrences of a specific version number
to a new version across all project files.
"""

import os
import re
import sys
from pathlib import Path

# Configuration
OLD_VERSION = "2.1.8"
NEW_VERSION = "2.1.8"
# Directories to skip
SKIP_DIRS = [
    "backups",
    "__pycache__",
    ".git",
    "temp",
    "venv",
    "env"
]
# File extensions to check
FILE_EXTENSIONS = [
    ".py", ".md", ".json", ".txt", ".bat", ".sh", ".html", ".js", ".css"
]

def update_version(file_path, old_version, new_version):
    """Update version in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Check if the file contains the old version
        if old_version in content:
            # Replace all occurrences
            updated_content = content.replace(old_version, new_version)

            # Write updated content back to the file
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)

            print(f"Updated: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def scan_directory(directory, old_version, new_version):
    """Scan directory recursively and update version in files"""
    updated_files = 0

    for root, dirs, files in os.walk(directory):
        # Skip directories in the SKIP_DIRS list
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            # Check if file has one of the allowed extensions
            if any(file.endswith(ext) for ext in FILE_EXTENSIONS):
                file_path = os.path.join(root, file)
                if update_version(file_path, old_version, new_version):
                    updated_files += 1

    return updated_files

if __name__ == "__main__":
    # Get the repository root directory (assuming the script is in dev/tools)
    repo_root = Path(__file__).parent.parent.parent

    print(f"ROM Sorter Pro - Version Updater")
    print(f"Updating version from {OLD_VERSION} to {NEW_VERSION}")
    print(f"Repository root: {repo_root}")

    # Confirm with the user before proceeding
    confirm = input("Continue with version update? (y/n): ")
    if confirm.lower() != 'y':
        print("Version update cancelled.")
        sys.exit(0)

    # Start the update process
    updated = scan_directory(repo_root, OLD_VERSION, NEW_VERSION)

    print(f"\nVersion update completed.")
    print(f"Updated {updated} files from version {OLD_VERSION} to {NEW_VERSION}.")
