@echo off
REM Skript zum Entfernen von Git-Spuren und Einrichten eines neuen Repositories

echo Entferne alle Git-Spuren aus dem Projekt...
python cleanup_git.py

echo.
echo Soll ein neues Git-Repository initialisiert werden? (j/n)
set /p init_git=

if /i "%init_git%"=="j" (
    echo.
    echo Initialisiere neues Git-Repository...
    git init

    echo.
    echo Füge alle Dateien zum Repository hinzu...
    git add .

    echo.
    echo Erstelle den ersten Commit...
    git commit -m "Initial commit"

    echo.
    echo Git-Repository wurde erfolgreich eingerichtet!
) else (
    echo.
    echo Git-Repository wurde nicht initialisiert.
)

echo.
echo Prozess abgeschlossen.
pause
