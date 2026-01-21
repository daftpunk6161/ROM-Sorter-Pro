@echo off
REM ROM Sorter Pro - Startskript für Windows
REM Version 2.1.8
REM Copyright (c) 2025

echo ROM Sorter Pro wird gestartet...
echo.

REM Überprüfen, ob Python installiert ist
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Fehler: Python wurde nicht gefunden!
    echo Bitte installieren Sie Python 3.8 oder höher.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Clean up project
echo Cleaning up project...
if exist "%~dp0dev\scripts\cleanup_project.py" (
    python "%~dp0dev\scripts\cleanup_project.py"
    if %ERRORLEVEL% NEQ 0 (
        echo Warning: Cleanup could not be completed fully.
        echo The program will continue anyway...
    )
) else (
    echo Warning: Cleanup script not found. Skipping cleanup.
)

REM Prüfen, ob virtuelle Umgebung existiert und aktivieren
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

REM Prüfen, ob Abhängigkeiten installiert sind
python -c "import PyQt5" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installiere Abhängigkeiten...
    python install_dependencies.py
)

REM Starte die Anwendung (GUI-first entry)
set "ARGS=%*"
if "%~1"=="" (
    set "ARGS=--gui"
)
python start_rom_sorter.py %ARGS%

REM Wenn eine virtuelle Umgebung aktiviert wurde, deaktivieren
if defined VIRTUAL_ENV (
    call deactivate
)

exit /b 0
