"""Implementation of the _open_log_file Method for the Optimizedromesortergui Class. This module provides a simple function to open the log files."""

import os
import platform
from tkinter import messagebox

def open_log_file(self):
    """Opens the current log file. This method is intended to be integrated into the Optimized Rome Sortergui class."""
    try:
        # Go up to the logs from the Ui Directory a Directory for the Logs
        ui_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(ui_dir)
        log_path = os.path.join(app_dir, 'logs')

        # Find the latest log file
        if os.path.exists(log_path):
            log_files = [f for f in os.listdir(log_path) if f.startswith('rom_sorter_')]
            if log_files:
                log_files.sort(reverse=True)  # Neueste zuerst
                latest_log = os.path.join(log_path, log_files[0])

                # Open the log file
                if platform.system() == 'Windows':
                    os.startfile(latest_log)
                elif platform.system() == 'Darwin':  # macOS
                    os.system(f'open "{latest_log}"')
                else:  # Linux and others
                    os.system(f'xdg-open "{latest_log}"')
                return

        messagebox.showinfo("Info", "Keine Log-Datei gefunden.")
    except Exception as e:
        messagebox.showerror("Fehler", f"Fehler beim Öffnen der Log-Datei: {e}")
