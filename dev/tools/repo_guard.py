#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - Repository Quality Guard

This tool checks the repository for code quality, consistency, and adherence to project standards.
It ensures that all files follow naming conventions, code style guidelines, and other project rules.
"""

import os
import sys
import re
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import importlib.util

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("repo_guard")

# Project constants
ROOT_DIR = Path(__file__).parent
SRC_DIR = ROOT_DIR / "src"
DOCS_DIR = ROOT_DIR / "docs"
BACKUP_DIR = ROOT_DIR / "backups"

EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "backups"}
EXCLUDE_FILES = {"comment-translation-cache.json", ".gitignore"}

# Naming convention regexes
PYTHON_FILE_REGEX = re.compile(r"^[a-z][a-z0-9_]*\.py$")
POWERSHELL_FILE_REGEX = re.compile(r"^[A-Z][a-zA-Z]+-[A-Z][a-zA-Z]+\.ps1$")
MARKDOWN_FILE_REGEX = re.compile(r"^[a-z][a-z0-9-]*\.md$")

# Check types
CHECK_NAMING = "naming"
CHECK_IMPORTS = "imports"
CHECK_COMMENTS = "comments"
CHECK_VERSION = "version"
CHECK_CODE_STYLE = "style"
CHECK_DUPLICATION = "duplication"
CHECK_ALL = "all"

# Current project version (to be updated with each release)
CURRENT_VERSION = "2.1.7"
VERSION_REGEX = re.compile(r"v?(\d+\.\d+\.\d+)")


class ValidationError:
    """Represents a validation error found during checks."""

    def __init__(self, check_type: str, filepath: str, message: str, line: Optional[int] = None):
        self.check_type = check_type
        self.filepath = filepath
        self.message = message
        self.line = line

    def __str__(self) -> str:
        location = f"{self.filepath}"
        if self.line is not None:
            location += f":{self.line}"
        return f"[{self.check_type.upper()}] {location} - {self.message}"


def check_file_naming(filepath: Path) -> List[ValidationError]:
    """
    Check if the file follows the project's naming conventions.

    Args:
        filepath: The path to the file to check

    Returns:
        List of validation errors, empty if no errors found
    """
    errors = []
    filename = filepath.name

    # Skip excluded files
    if filename in EXCLUDE_FILES:
        return errors

    # Check Python files
    if filepath.suffix == ".py":
        if not PYTHON_FILE_REGEX.match(filename):
            errors.append(ValidationError(
                CHECK_NAMING,
                str(filepath),
                f"Python file should use snake_case.py: {filename}"
            ))

    # Check PowerShell files
    elif filepath.suffix == ".ps1":
        if not POWERSHELL_FILE_REGEX.match(filename):
            errors.append(ValidationError(
                CHECK_NAMING,
                str(filepath),
                f"PowerShell file should use Verb-Noun.ps1: {filename}"
            ))

    # Check Markdown files
    elif filepath.suffix == ".md":
        if filepath.parent == DOCS_DIR and not MARKDOWN_FILE_REGEX.match(filename):
            errors.append(ValidationError(
                CHECK_NAMING,
                str(filepath),
                f"Markdown file should use kebab-case.md: {filename}"
            ))

    return errors


def check_python_imports(filepath: Path) -> List[ValidationError]:
    """
    Check Python imports for issues like circular imports and inconsistent patterns.

    Args:
        filepath: The path to the Python file to check

    Returns:
        List of validation errors, empty if no errors found
    """
    if filepath.suffix != ".py":
        return []

    errors = []
    with open(filepath, "r", encoding="utf-8") as file:
        content = file.read()
        lines = content.splitlines()

    # Check for absolute imports from src
    src_imports = re.findall(r"from\s+src\.[\w\.]+\s+import", content)
    if src_imports and filepath.parent.name == "src":
        errors.append(ValidationError(
            CHECK_IMPORTS,
            str(filepath),
            f"Found {len(src_imports)} absolute imports from 'src' within src directory. "
            "Use relative imports instead."
        ))

    return errors


def check_python_comments(filepath: Path) -> List[ValidationError]:
    """
    Check Python files for non-English comments.

    Args:
        filepath: The path to the Python file to check

    Returns:
        List of validation errors, empty if no errors found
    """
    if filepath.suffix != ".py":
        return []

    errors = []
    german_chars = re.compile(r"[äöüßÄÖÜ]")

    with open(filepath, "r", encoding="utf-8") as file:
        for i, line in enumerate(file, 1):
            # Skip lines that are not comments
            stripped = line.strip()
            if not (stripped.startswith("#") or stripped.startswith('"""')):
                continue

            # Check for German characters in comments
            if german_chars.search(line):
                errors.append(ValidationError(
                    CHECK_COMMENTS,
                    str(filepath),
                    "Found non-English (likely German) comment",
                    i
                ))

    return errors


def check_version_consistency(filepath: Path) -> List[ValidationError]:
    """
    Check for inconsistent version numbers in files.

    Args:
        filepath: The path to the file to check

    Returns:
        List of validation errors, empty if no errors found
    """
    errors = []

    # Only check certain file types
    if filepath.suffix not in [".py", ".md", ".bat", ".sh"]:
        return errors

    with open(filepath, "r", encoding="utf-8") as file:
        content = file.read()

    # Find all version strings
    versions = VERSION_REGEX.findall(content)
    for version in versions:
        if version != CURRENT_VERSION:
            errors.append(ValidationError(
                CHECK_VERSION,
                str(filepath),
                f"Inconsistent version number found: {version}, expected {CURRENT_VERSION}"
            ))

    return errors


def check_duplication(filepaths: List[Path]) -> List[ValidationError]:
    """
    Check for duplicated files or modules.

    Args:
        filepaths: List of all filepaths to check against each other

    Returns:
        List of validation errors, empty if no errors found
    """
    errors = []

    # Map module names to their filepaths
    module_map = {}
    for filepath in filepaths:
        if filepath.suffix != ".py":
            continue

        # Check for potential module duplication
        module_name = filepath.stem
        rel_path = filepath.relative_to(ROOT_DIR)

        if module_name in module_map:
            existing_path = module_map[module_name]
            # Ignore __init__.py and files in different directories
            if module_name != "__init__" and filepath.parent != Path(existing_path).parent:
                errors.append(ValidationError(
                    CHECK_DUPLICATION,
                    str(filepath),
                    f"Potential module duplication: also found in {existing_path}"
                ))
        else:
            module_map[module_name] = str(rel_path)

    return errors


def run_checks(check_type: str = CHECK_ALL) -> List[ValidationError]:
    """
    Run the requested checks on the repository.

    Args:
        check_type: The type of check to run

    Returns:
        List of validation errors
    """
    errors = []
    filepaths = []

    # Collect all relevant files
    for root, dirs, files in os.walk(ROOT_DIR):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        root_path = Path(root)
        for file in files:
            filepath = root_path / file
            filepaths.append(filepath)

            # Run individual file checks
            if check_type in (CHECK_NAMING, CHECK_ALL):
                errors.extend(check_file_naming(filepath))

            if check_type in (CHECK_IMPORTS, CHECK_ALL) and filepath.suffix == ".py":
                errors.extend(check_python_imports(filepath))

            if check_type in (CHECK_COMMENTS, CHECK_ALL) and filepath.suffix == ".py":
                errors.extend(check_python_comments(filepath))

            if check_type in (CHECK_VERSION, CHECK_ALL):
                errors.extend(check_version_consistency(filepath))

    # Run checks that need the complete file list
    if check_type in (CHECK_DUPLICATION, CHECK_ALL):
        errors.extend(check_duplication(filepaths))

    return errors


def print_report(errors: List[ValidationError]) -> None:
    """Print a formatted report of all validation errors."""
    if not errors:
        logger.info("✅ No issues found! Repository is in good shape.")
        return

    # Group errors by check type
    errors_by_type = {}
    for error in errors:
        if error.check_type not in errors_by_type:
            errors_by_type[error.check_type] = []
        errors_by_type[error.check_type].append(error)

    logger.info(f"Found {len(errors)} issues in {len(errors_by_type)} categories:")

    # Print errors by category
    for check_type, type_errors in errors_by_type.items():
        print(f"\n=== {check_type.upper()} ISSUES ({len(type_errors)}) ===")
        for error in type_errors:
            print(f"- {error}")


def main():
    """Main entry point for the repo guard tool."""
    parser = argparse.ArgumentParser(description="ROM Sorter Pro Repository Quality Guard")
    parser.add_argument(
        "check",
        choices=[CHECK_ALL, CHECK_NAMING, CHECK_IMPORTS, CHECK_COMMENTS, CHECK_VERSION, CHECK_CODE_STYLE, CHECK_DUPLICATION],
        default=CHECK_ALL,
        help="The type of check to perform"
    )
    args = parser.parse_args()

    logger.info(f"Running {args.check} checks on repository...")
    errors = run_checks(args.check)
    print_report(errors)

    # Return non-zero exit code if errors were found
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
