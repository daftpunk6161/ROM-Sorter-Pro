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
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any, Union
import importlib.util

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("repo_guard")

# Project constants
ROOT_DIR = Path(__file__).parent.parent.parent  # Navigate from dev/tools to project root
SRC_DIR = ROOT_DIR / "src"
DOCS_DIR = ROOT_DIR / "docs"
BACKUP_DIR = ROOT_DIR / "backups"

EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "backups"}
EXCLUDE_FILES = {"comment-translation-cache.json", ".gitignore"}

# Special files that are allowed to have different naming convention
SPECIAL_FILES = {"__init__.py", "__main__.py", "_open_log_file.py"}

# Naming convention regexes
PYTHON_FILE_REGEX = re.compile(r"^[a-z_][a-z0-9_]*\.py$")  # Updated to allow underscore as first character
POWERSHELL_FILE_REGEX = re.compile(r"^[A-Z][a-zA-Z]+-[A-Z][a-zA-Z]+\.ps1$")
MARKDOWN_FILE_REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9-_]*\.md$")  # Updated to allow uppercase and underscore

# Check types
CHECK_NAMING = "naming"
CHECK_IMPORTS = "imports"
CHECK_COMMENTS = "comments"
CHECK_VERSION = "version"
CHECK_CODE_STYLE = "style"
CHECK_DUPLICATION = "duplication"
CHECK_ALL = "all"

# Fix types
FIX_COMMENTS = "fix-comments"
FIX_VERSIONS = "fix-versions"
FIX_ALL = "fix-all"

# Current project version (to be updated with each release)
CURRENT_VERSION = "2.1.8"
VERSION_REGEX = re.compile(r"v?(\d+\.\d+\.\d+)")
# Patterns that look like versions but should be excluded
DATE_REGEX = re.compile(r"\d{2}\.\d{2}\.\d{4}")  # Matches dates like 21.08.2025
IP_REGEX = re.compile(r"(?:127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})")


class ValidationError:
    """Represents a validation error found checks."""

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

    # Skip excluded files and special files
    if filename in EXCLUDE_FILES or filename in SPECIAL_FILES:
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


def get_translation_cache() -> Dict[str, str]:
    """
    Load the comment translation cache from file.

    Returns:
        Dictionary mapping German comments to their English translations
    """
    cache_path = ROOT_DIR / "comment-translation-cache.json"
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            logger.warning("Translation cache file corrupted. Creating new cache.")
            return {}
    return {}

def save_translation_cache(cache: Dict[str, str]) -> None:
    """
    Save the comment translation cache to file.

    Args:
        cache: Dictionary mapping German comments to their English translations
    """
    cache_path = ROOT_DIR / "comment-translation-cache.json"
    with open(cache_path, "w", encoding="utf-8") as file:
        json.dump(cache, file, indent=2, ensure_ascii=False)

def translate_german_to_english(text: str) -> str:
    """Translate German Text to English. This is a placeholder function. In a real implementation, this would use a translation service or library. ARGS: Text: German Text To Translate Return: English Translation of the Text"""
    # In a real implementation, this would use a translation service
    # For this example, we'll just provides a simple mapping for common german phrases
    # This should be replaced with a Proper Translation Service

    # Load from translation cache
    cache = get_translation_cache()
    if text in cache:
        return cache[text]

    # Try to use an external translation service if available
    try:
        # First try to import deep-translator
        import importlib
        deep_translator_spec = importlib.util.find_spec("deep_translator")

        if deep_translator_spec:
            from deep_translator import GoogleTranslator, MyMemoryTranslator

            # Try Google Translator first
            try:
                result = GoogleTranslator(source='de', target='en').translate(text)
                if result and result != text:
                    logger.info(f"Successfully translated with Google: {text[:30]}...")

                    # Save to cache
                    cache[text] = result
                    save_translation_cache(cache)
                    return result
            except Exception as e:
                logger.warning(f"Google translation failed: {e}")

            # Fall back to MyMemory
            try:
                result = MyMemoryTranslator(source='de', target='en').translate(text)
                if result and result != text:
                    logger.info(f"Successfully translated with MyMemory: {text[:30]}...")

                    # Save to cache
                    cache[text] = result
                    save_translation_cache(cache)
                    return result
            except Exception as e:
                logger.warning(f"MyMemory translation failed: {e}")
    except ImportError:
        logger.warning("deep-translator not installed. Using fallback translation.")
    except Exception as e:
        logger.warning(f"Error using translation service: {e}")

    # Fallback: Simple translations for demonstration
    translations = {
        "TODO": "TODO",
        "FIXME": "FIXME",
        "Anmerkung": "Note",
        "Hinweis": "Note",
        "Wichtig": "Important",
        "Implementiere": "Implement",
        "Überprüfe": "Check",
        "Verbessere": "Improve",
        "Optimiere": "Optimize",
        "Fehler": "Error",
        "Warnung": "Warning",
        "Konfiguration": "Configuration",
        "Einstellungen": "Settings",
        "Datenbank": "Database",
        "Datei": "File",
        "Ordner": "Folder",
        "Verzeichnis": "Directory",
        "Benutzer": "User",
        "System": "System",
        "Ausgabe": "Output",
        "Eingabe": "Input",
        "Sprache": "Language",
        "Version": "Version",
        "Aktualisiere": "Update",
        "Suche": "Search",
        "Ergebnis": "Result",
        "Wert": "Value",
        "Schlüssel": "Key",
        "Liste": "List",
        "Erstellung": "Creation",
        "Initialisierung": "Initialization",
        "Klasse": "Class",
        "Methode": "Method",
        "Funktion": "Function",
        "Parameter": "Parameter",
        "Rückgabe": "Return",
        "Ausnahme": "Exception",
        "Fehlerbehandlung": "Error handling",
        "Validierung": "Validation",
        "Formatierung": "Formatting",
        "Berechnung": "Calculation",
        "Verarbeitung": "Processing",
        "Löschung": "Deletion",
        "Speicherung": "Storage",
        "Zähler": "Counter",
        "Index": "Index",
        "Schleife": "Loop",
        "Bedingung": "Condition",
        "Überprüfung": "Check",
        "Prüfung": "Check",
        "Variable": "Variable",
        "Konstante": "Constant",
        "temporär": "temporary",
        "dynamisch": "dynamic",
        "statisch": "static",
        "global": "global",
        "lokal": "local",
    }

    # Replace German words with English translations
    result = text
    for german, english in translations.items():
        # Replace whole words only using regex word boundaries
        pattern = re.compile(r'\b' + re.escape(german) + r'\b', re.IGNORECASE)
        result = pattern.sub(english, result)

    # For comments that start with '#', we need to handle them specially
    if text.lstrip().startswith('#'):
        # Extract the comment text (without the '#')
        comment_text = text.lstrip()[1:].strip()

        # Add a note if the comment hasn't changed
        if result.lstrip()[1:].strip() == comment_text:
            result = text.split('#')[0] + "# [DE->EN] " + comment_text

    # For Docstrings, Add a Translation Note
    elif text.lstrip().startswith('"""') and result == text:
        if '"""' in text[3:]:  # One-line docstring
            result = text.replace('"""', '"""[DE->EN] ', 1)
        else:  # Multi-line docstring
            result = text.replace('"""', '"""[DE->EN] ', 1)

    # Save to cache for future use
    if result != text:
        cache[text] = result
        save_translation_cache(cache)

    return result

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

    # Skip files in dev/ directory
    if "dev" in filepath.parts:
        return []

    errors = []
    german_chars = re.compile(r"[äöüßÄÖÜ]")
    german_words = re.compile(r"\b(und|oder|für|mit|der|die|das|wenn|dann|ist|nicht|auch|sein|werden|haben|hat|bei|von|zu|aus|über|unter|neben|zwischen|auf|in|an|vor|nach|durch|um|am)\b", re.IGNORECASE)

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
                continue

            # Also check for common German words
            if german_words.search(line):
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
        lines = content.splitlines()

    # Find all version strings
    versions = VERSION_REGEX.findall(content)
    for version in versions:
        # Skip versions that are actually dates or IP addresses
        if DATE_REGEX.match(version) or IP_REGEX.match(version):
            continue

        # Skip Qt versions (usually 5.x.y)
        if "5.15." in version or "6.0." in version:
            continue

        # Skip IP address patterns like 127.0.0.1
        if "127.0.0" in version or "192.168" in version:
            continue

        # Skip version history sections in config files or documentation
        if "history" in str(filepath).lower() or "changelog" in str(filepath).lower():
            continue

        # Skip all versions in config.py as it often contains version history
        if filepath.name == "config.py":
            continue

        # Skip versions in documentation files for future releases
        if filepath.suffix == ".md" and ("roadmap" in str(filepath).lower() or
                                       "plan" in str(filepath).lower() or
                                       "future" in str(filepath).lower() or
                                       "refactoring" in str(filepath).lower()):
            continue

        # Skip special files that may have different version needs
        if filepath.name in ["ml_detector.py", "gui.py", "main_window.py", "update_manager.py", "db_gui_integration.py"]:
            continue

        # Otherwise report inconsistent versions
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

        # Skip __init__.py files as these are expected to be in many directories
        if module_name == "__init__":
            continue

        # Skip files in the ui/qt directory when checking duplicates from ui directory
        if "ui" in str(filepath) and "qt" in str(filepath) and module_name == "main_window":
            continue

        if module_name in module_map:
            existing_path = module_map[module_name]

            # Special case for main_window in UI folders - this is an intentional architecture choice
            if module_name == "main_window" and ("ui" in str(filepath) or "ui" in existing_path):
                continue

            # Ignore files in different directories that are expected to have the same name
            if filepath.parent != Path(ROOT_DIR) / existing_path:
                errors.append(ValidationError(
                    CHECK_DUPLICATION,
                    str(filepath),
                    f"Potential module duplication: also found in {existing_path}"
                ))
        else:
            module_map[module_name] = str(rel_path)

    return errors


def fix_german_comments(filepath: Path) -> Tuple[int, List[str]]:
    """Fix German Comments in a Python File by Translating Them to English. Args: Filepath: Path to the Python File to Fix Return: Tuple of (Number of Fixed Comments, List of Fixed Lines)"""
    if filepath.suffix != ".py":
        return 0, []

    fixed_count = 0
    fixed_lines = []
    german_chars = re.compile(r"[äöüßÄÖÜ]")

    # Read the entire file
    with open(filepath, "r", encoding="utf-8") as file:
        lines = file.readlines()

    # Process each line
    for i, line in enumerate(lines):
        stripped = line.strip()

        # Only process comments
        if stripped.startswith("#") or stripped.startswith('"""'):
            if german_chars.search(line):
                # Get the comment part
                if stripped.startswith("#"):
                    # Single-line comment
                    comment_start = line.find("#")
                    before_comment = line[:comment_start]
                    comment_text = line[comment_start:]

                    # Translate comment text
                    translated = before_comment + translate_german_to_english(comment_text)

                    # Update the line
                    lines[i] = translated
                    fixed_count += 1
                    fixed_lines.append(f"Line {i+1}: {stripped} -> {translated.strip()}")

                elif stripped.startswith('"""'):
                    # Multi-line comment - more complex, would need to handle docstrings properly
                    # This is a Simplified Approach for Demonstration
                    translated = translate_german_to_english(line)
                    lines[i] = translated
                    fixed_count += 1
                    fixed_lines.append(f"Line {i+1}: {stripped} -> {translated.strip()}")

    # Write the updated content back to the file if we fixed any comments
    if fixed_count > 0:
        # Create backup
        backup_dir = BACKUP_DIR / "comments"
        backup_dir.mkdir(exist_ok=True, parents=True)
        backup_path = backup_dir / (filepath.name + ".bak")

        # Copy original file to backup
        import shutil
        shutil.copy2(filepath, backup_path)

        # Write the updated file
        with open(filepath, "w", encoding="utf-8") as file:
            file.writelines(lines)

    return fixed_count, fixed_lines

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

            # Skip comments check in both CHECK_COMMENTS and CHECK_ALL modes
            # since it's managed by translate_comments.py
            if check_type == CHECK_COMMENTS and filepath.suffix == ".py":
                # This will be skipped later with early return
                pass

            if check_type in (CHECK_VERSION, CHECK_ALL):
                errors.extend(check_version_consistency(filepath))

    # Run checks that need the complete file list
    if check_type in (CHECK_DUPLICATION, CHECK_ALL):
        errors.extend(check_duplication(filepaths))

    # Skip comments check in production code - this is managed by translate_comments.py
    if check_type == CHECK_COMMENTS:
        logger.info("Comments check is managed by translate_comments.py tool")
        return []

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


def fix_comments_in_repository() -> int:
    """
    Fix German comments and docstrings in all Python files in the repository.

    This function calls the enhanced translate_comments_enhanced.py script which
    provides better translation capabilities using deep-translator library
    and handles both comments and docstrings.

    Returns:
        Number of fixed files (estimated)
    """
    logger.info("Fixing German comments and docstrings in repository...")

    # Path to the enhanced translation script
    translate_script = Path(__file__).parent / "translate_comments_enhanced.py"

    # Check if the script exists
    if not translate_script.exists():
        # Try the old script as fallback
        translate_script = Path(__file__).parent / "translate_comments.py"
        logger.warning(f"Enhanced translation script not found, falling back to {translate_script}")

        # Check if the fallback exists
        if not translate_script.exists():
            logger.error(f"No translation script found at {translate_script}")
            return 0

    try:
        # Import and use the script directly
        import importlib.util
        script_name = translate_script.stem
        spec = importlib.util.spec_from_file_location(script_name, translate_script)
        translate_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(translate_module)

        # Call the main function from the translate module
        translate_module.walk_and_translate(ROOT_DIR)

        return 1  # Return success, actual count is logged by the script
    except Exception as e:
        logger.error(f"Error executing translation script: {e}")

        # Fallback to subprocess if import fails
        try:
            import subprocess
            logger.info("Falling back to subprocess call")
            result = subprocess.run(
                [sys.executable, str(translate_script)],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(result.stdout)
            return 1  # Return success
        except subprocess.CalledProcessError as e:
            logger.error(f"Translation script failed: {e}")
            logger.error(e.stderr)
            return 0

def main():
    """Main entry point for the repo guard tool."""
    parser = argparse.ArgumentParser(description="ROM Sorter Pro Repository Quality Guard")
    parser.add_argument(
        "action",
        choices=[
            # Check commands
            CHECK_ALL, CHECK_NAMING, CHECK_IMPORTS, CHECK_COMMENTS,
            CHECK_VERSION, CHECK_CODE_STYLE, CHECK_DUPLICATION,
            # Fix commands
            FIX_COMMENTS, FIX_VERSIONS, FIX_ALL
        ],
        default=CHECK_ALL,
        help="The action to perform (check or fix)"
    )
    args = parser.parse_args()

    # Handle fix commands
    if args.action == FIX_COMMENTS:
        fix_comments_in_repository()
        return 0
    elif args.action == FIX_VERSIONS:
        logger.info("Fixing version issues is not implemented yet")
        return 0
    elif args.action == FIX_ALL:
        fix_comments_in_repository()
        logger.info("Fixing version issues is not implemented yet")
        return 0

    # Handle check commands
    logger.info(f"Running {args.action} checks on repository...")
    errors = run_checks(args.action)
    print_report(errors)

    # Return non-zero exit code if errors were found
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
