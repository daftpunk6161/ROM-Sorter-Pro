#!/usr/bin/env python3
"""
Skript zum vollständigen Entfernen aller Git-Spuren aus dem Projekt
und Vorbereitung für einen Neustart mit Versionskontrolle.
"""

import os
import shutil
import sys
from pathlib import Path

def main():
    # Aktuelles Verzeichnis (Root des Projekts)
    project_root = Path(__file__).resolve().parent

    print(f"Entferne Git-Spuren aus: {project_root}")

    # Git-Hook Verzeichnis entfernen
    git_dir = project_root / "git"
    if git_dir.exists() and git_dir.is_dir():
        print(f"Entferne Git-Hook-Verzeichnis: {git_dir}")
        shutil.rmtree(git_dir)

    # Git-bezogene Dateien entfernen
    git_related_files = [
        "repo_guard.py",
        "repo_guard.config.json",
        "repo-guard-config.json"  # Alternative Schreibweise basierend auf dem Code
    ]

    for file_name in git_related_files:
        file_path = project_root / file_name
        if file_path.exists():
            print(f"Entferne Git-bezogene Datei: {file_path}")
            os.remove(file_path)

    # Temporäre und generierte Dateien finden und entfernen
    temp_files = [
        "dup-index.json"  # In repo_guard.py erwähnt
    ]

    for file_name in temp_files:
        file_path = project_root / file_name
        if file_path.exists():
            print(f"Entferne temporäre Datei: {file_path}")
            os.remove(file_path)

    # Prüfen, ob .git-Verzeichnis existiert (für den Fall, dass es versteckt ist)
    git_repo = project_root / ".git"
    if git_repo.exists() and git_repo.is_dir():
        print(f"Entferne Git-Repository-Verzeichnis: {git_repo}")
        shutil.rmtree(git_repo)

    # Versteckte Git-Dateien entfernen
    git_config_files = [".gitignore", ".gitattributes", ".gitmodules"]
    for file_name in git_config_files:
        file_path = project_root / file_name
        if file_path.exists():
            print(f"Entferne Git-Konfigurationsdatei: {file_path}")
            os.remove(file_path)

    print("Bereinigung abgeschlossen! Das Projekt ist bereit für einen neuen Git-Start.")

    # Neue .gitignore-Datei erstellen
    create_new_gitignore = input("Soll eine neue .gitignore-Datei erstellt werden? (j/n): ").lower().strip()
    if create_new_gitignore == 'j':
        create_gitignore(project_root)

def create_gitignore(project_root):
    """Erstellt eine neue .gitignore-Datei mit den üblichen Ausschlüssen für Python-Projekte"""

    gitignore_content = """# Python-Dateien
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtuelle Umgebungen
venv/
env/
ENV/
.venv/

# IDE-Dateien
.idea/
.vscode/
*.swp
*.swo

# SQLite-Datenbanken
*.sqlite
*.db

# Logs
*.log

# Sicherungsdateien
*.bak
*~

# Cache-Dateien
*.cache
.pytest_cache/
.coverage
htmlcov/

# Betriebssystem-Dateien
.DS_Store
Thumbs.db
"""

    gitignore_path = project_root / ".gitignore"
    with open(gitignore_path, "w", encoding="utf-8") as f:
        f.write(gitignore_content)

    print(f"Neue .gitignore-Datei erstellt: {gitignore_path}")

if __name__ == "__main__":
    main()
