@echo off
REM Automatische Ausführung von cleanup_project.py
echo Starte Bereinigung des Projekts...
python "%~dp0\cleanup_project.py"
if %ERRORLEVEL% neq 0 (
    echo Fehler bei der Bereinigung!
    pause
    exit /b %ERRORLEVEL%
) else (
    echo Bereinigung erfolgreich abgeschlossen.
)
pause
