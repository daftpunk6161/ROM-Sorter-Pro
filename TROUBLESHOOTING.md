# Troubleshooting

## GUI does not start
- Ensure Python 3.11+ is installed
- Install GUI deps: `pip install -r requirements-gui.txt`
- Use fallback: `python start_rom_sorter.py --gui --tk`

## Optional deps cause crash
- Optional packages must be guarded; verify imports are lazy
- Check `ROM_SORTER_GUI_BACKEND` env var for forced backend

## Conversions do nothing
- Confirm conversion rules in config and tools in `external_tools` are configured
- Dry-run never executes tools by design

## Scan shows Unknown
- UNKNOWN is preferred to wrong detection (policy)
- Add/verify platform catalog signals and DAT matches

## 7z/RAR archive scanning does not work
- 7z hashing uses the Python package `py7zr` (no external 7-Zip binary required).
- RAR hashing uses `rarfile` and requires an external tool on PATH:
	- Windows: `unrar.exe` (WinRAR) or `7z.exe`
	- Linux/macOS: `unrar` or `bsdtar`
- Place the tool anywhere, but it must be discoverable via PATH.
- If the tool is missing, the scanner falls back to name-only detection for .rar.

## Cancel does not stop
- Ensure you are on latest commit
- Check logs for long-running IO without cancel points

## Worker errors do not show details
- GUI should display an error dialog and log details in the live log panel
- If only a dialog appears, export the log buffer and attach it to bug reports
