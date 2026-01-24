"""Database Management Dialog for Rome Database Integration. This module provides a gui interface for the management of the rome database."""

import os
import sys
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sqlite3
import subprocess
import platform
from typing import Any, Dict
from pathlib import Path

from .db_paths import get_rom_db_path

logger = logging.getLogger(__name__)

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class DatabaseManagerDialog:
    """Dialogue for managing the Rome database."""

    def __init__(self, parent):
        """Initialized the database manager dialog. Args: Parent: The overarching window"""
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("ROM-Datenbank verwalten")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

# Standard database path
        self.db_path = get_rom_db_path()

        self._create_interface()

    def _create_interface(self):
        """Creates the user interface."""
# Main container
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill='both', expand=True)

# Information area
        info_frame = ttk.LabelFrame(main_frame, text="Datenbank-Information", padding=10)
        info_frame.pack(fill='x', padx=5, pady=5)

# Show database status
        self.status_var = tk.StringVar(value="Lade Datenbankstatus...")
        ttk.Label(info_frame, textvariable=self.status_var, wraplength=550).pack(fill='x')

# Actions area
        actions_frame = ttk.LabelFrame(main_frame, text="Aktionen", padding=10)
        actions_frame.pack(fill='x', padx=5, pady=5)

# Scan button
        ttk.Button(actions_frame, text="ROMs scannen und zur Datenbank hinzufügen",
                  command=self._scan_roms).pack(fill='x', padx=5, pady=2)

# Import button
        ttk.Button(actions_frame, text="DAT-Datei importieren (No-Intro/Redump)",
                  command=self._import_dat).pack(fill='x', padx=5, pady=2)

        # Migrate button
        ttk.Button(actions_frame, text="Datenbank migrieren",
                  command=self._migrate_db).pack(fill='x', padx=5, pady=2)

        # Backup button
        ttk.Button(actions_frame, text="Datenbank sichern (Backup)",
                  command=self._backup_db).pack(fill='x', padx=5, pady=2)

        # Open folder button
        ttk.Button(actions_frame, text="Datenbank-Ordner öffnen",
                  command=self._open_db_folder).pack(fill='x', padx=5, pady=2)

# Statistics area
        stats_frame = ttk.LabelFrame(main_frame, text="Statistik", padding=10)
        stats_frame.pack(fill='both', expand=True, padx=5, pady=5)

# Statistics display
        self.stats_text = tk.Text(stats_frame, wrap='word', height=10)
        self.stats_text.pack(fill='both', expand=True)
        self.stats_text.config(state='disabled')

# Close button
        ttk.Button(main_frame, text="Schließen", command=self.dialog.destroy).pack(pady=10)

# initialization
        self.update_database_status()

    def update_database_status(self):
        """Updates the database status information."""
        def worker() -> None:
            result = self._compute_database_status()
            self.dialog.after(0, lambda: self._apply_database_status(result))

        threading.Thread(target=worker, daemon=True).start()

    def _compute_database_status(self) -> Dict[str, Any]:
        try:
            if not os.path.exists(self.db_path):
                return {
                    "status": (
                        "Keine Datenbank gefunden. Erstellen Sie eine Datenbank, indem Sie ROMs scannen "
                        "oder eine DAT-Datei importieren."
                    ),
                    "stats": "Keine Datenbank vorhanden",
                }

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM roms")
            rom_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT console) FROM roms")
            console_count = cursor.fetchone()[0]

            cursor.execute("SELECT console, COUNT(*) FROM roms GROUP BY console ORDER BY COUNT(*) DESC")
            console_stats = cursor.fetchall()

            stats_text = f"Datenbankpfad: {self.db_path}\n"
            stats_text += f"Gesamtanzahl der ROMs: {rom_count:,}\n"
            stats_text += f"Anzahl der Konsolen: {console_count}\n\n"
            stats_text += "Top 10 Konsolen:\n"

            for i, (console, count) in enumerate(console_stats[:10], 1):
                stats_text += f"{i}. {console}: {count:,} ROMs\n"

            conn.close()

            return {
                "status": f"ROM-Datenbank gefunden: {rom_count:,} ROMs für {console_count} Konsolen.",
                "stats": stats_text,
            }

        except sqlite3.OperationalError as e:
            if "no such table: roms" in str(e):
                try:
                    self._ensure_repo_root()
                    from app import db_controller
                    os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                    db_controller.init_db(self.db_path)
                    return {
                        "status": "Datenbank wurde initialisiert. Bitte fügen Sie ROMs hinzu.",
                        "stats": (
                            "Leere Datenbank wurde erstellt.\n"
                            "Verwenden Sie 'ROMs scannen' oder 'DAT-Datei importieren', um Daten hinzuzufügen."
                        ),
                    }
                except Exception as init_err:
                    return {
                        "status": f"Fehler bei der Datenbankinitialisierung: {init_err}",
                        "stats": (
                            f"Initialisierungsfehler: {init_err}\n\n"
                            "Bitte stellen Sie sicher, dass Sie Schreibberechtigungen haben."
                        ),
                    }
            return {
                "status": f"Fehler beim Lesen der Datenbank: {e}",
                "stats": (
                    f"Datenbankfehler: {e}\n\n"
                    "Bitte überprüfen Sie die Berechtigungen und Datenbankstruktur."
                ),
            }

        except Exception as e:
            try:
                from .db_debug import debug_database_initialization
                debug_database_initialization(self.db_path)
            except Exception:
                pass
            return {
                "status": f"Unerwarteter Fehler beim Lesen der Datenbank: {e}",
                "stats": (
                    f"Fehler: {e}\n\nDiagnoseinformationen:\n"
                    f"DB-Pfad: {self.db_path}\nExistiert: {os.path.exists(self.db_path)}"
                ),
            }

    def _apply_database_status(self, payload: Dict[str, Any]) -> None:
        try:
            self.status_var.set(str(payload.get("status") or ""))
            self._update_stats(str(payload.get("stats") or ""))
        except Exception:
            return

    def _run_threaded(self, label: str, message: str, task, on_success) -> None:
        progress_dialog = tk.Toplevel(self.dialog)
        progress_dialog.title(label)
        progress_dialog.geometry("320x110")
        progress_dialog.transient(self.dialog)
        progress_dialog.grab_set()

        ttk.Label(progress_dialog, text=message).pack(pady=10)

        progress = ttk.Progressbar(progress_dialog, mode='indeterminate')
        progress.pack(fill='x', padx=20)
        progress.start()

        done_flag = threading.Event()
        result_holder: Dict[str, Any] = {}

        def worker() -> None:
            try:
                result_holder["result"] = task()
            except Exception as exc:
                result_holder["error"] = exc
            finally:
                done_flag.set()
                self.dialog.after(0, finish)

        def finish() -> None:
            try:
                progress.stop()
                progress_dialog.destroy()
            except Exception:
                pass

            err = result_holder.get("error")
            if err is not None:
                try:
                    logger.error("DB task failed (%s): %s", label, err)
                except Exception:
                    pass
                messagebox.showerror(label, f"{label} fehlgeschlagen:\n{err}")
                return

            on_success(result_holder.get("result"))

        threading.Thread(target=worker, daemon=True).start()

    def _update_stats(self, text):
        """Updates the statistics text field."""
        self.stats_text.config(state='normal')
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, text)
        self.stats_text.config(state='disabled')

    def _backup_db(self):
        """Create a timestamped backup of the database file."""
        if not os.path.exists(self.db_path):
            messagebox.showerror("Fehler", "Keine Datenbank gefunden, die gesichert werden kann.")
            return

        def task():
            self._ensure_repo_root()
            from app import db_controller

            return db_controller.backup_db(self.db_path)

        def on_success(backup_path):
            messagebox.showinfo("Backup erstellt", f"Backup gespeichert unter:\n{backup_path}")
            self.update_database_status()

        self._run_threaded("Backup", "Erstelle Backup der Datenbank...", task, on_success)

    def _open_db_folder(self):
        """Open the database folder in the system file explorer."""
        folder = os.path.dirname(self.db_path)
        if not os.path.isdir(folder):
            messagebox.showerror("Fehler", "Datenbank-Ordner nicht gefunden.")
            return

        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(folder)  # type: ignore[attr-defined]
            elif system == "Darwin":
                subprocess.run(["open", folder], check=False)
            else:
                subprocess.run(["xdg-open", folder], check=False)
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte Ordner nicht öffnen:\n{e}")

    def _ensure_repo_root(self):
        repo_root = Path(__file__).resolve().parents[2]
        root_str = str(repo_root)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)

    def _migrate_db(self):
        """Run DB migration to latest schema version."""
        def task():
            self._ensure_repo_root()
            from app import db_controller

            ok = db_controller.migrate_db(self.db_path)
            return bool(ok)

        def on_success(ok: bool):
            if ok:
                messagebox.showinfo("Migration", "Datenbank erfolgreich migriert.")
            else:
                messagebox.showerror("Migration", "Migration fehlgeschlagen.")
            self.update_database_status()

        self._run_threaded("Migration", "Migriere Datenbank...", task, on_success)

    def _scan_roms(self):
        """Open's A Dialogue for Scanning Roms for the Database."""
        rom_dir = filedialog.askdirectory(title="ROM-Verzeichnis zum Scannen auswählen")
        if not rom_dir:
            return

# Directory exists
        if not os.path.exists(rom_dir):
            messagebox.showerror("Fehler", "Das ausgewählte Verzeichnis existiert nicht.")
            return

# Question about recursive scanning
        recursive = messagebox.askyesno("Rekursiv scannen?",
                                        "Sollen Unterverzeichnisse ebenfalls gescannt werden?")

# Start the scan process in a separate thread
        def scan_thread():
            try:
                from app import db_controller

                count = db_controller.scan_roms(rom_dir, db_path=self.db_path, recursive=recursive)

# Show the result
                self.dialog.after(0, lambda: messagebox.showinfo(
                    "Scan abgeschlossen",
                    f"{count:,} ROMs wurden zur Datenbank hinzugefügt."
                ))

# Update status
                self.dialog.after(0, self.update_database_status)

            except Exception as exc:
                self.dialog.after(0, lambda exc=exc: messagebox.showerror(
                    "Fehler",
                    f"Fehler beim Scannen des Verzeichnisses:\n{exc}"
                ))

# Start thread
        threading.Thread(target=scan_thread, daemon=True).start()

# Show to a Waiting Dialogue
        progress_dialog = tk.Toplevel(self.dialog)
        progress_dialog.title("Scanne ROMs...")
        progress_dialog.geometry("300x100")
        progress_dialog.transient(self.dialog)
        progress_dialog.grab_set()

        ttk.Label(progress_dialog, text="Scanne ROMs für die Datenbank...\n"
                                       "Dies kann einige Minuten dauern.").pack(pady=10)

        progress = ttk.Progressbar(progress_dialog, mode='indeterminate')
        progress.pack(fill='x', padx=20)
        progress.start()

# Function to close the progress dialogue
        def check_thread_status():
            if threading.active_count() > 1:  # Hauptthread + Scan-Thread
                progress_dialog.after(100, check_thread_status)
            else:
                progress_dialog.destroy()

        progress_dialog.after(100, check_thread_status)

    def _import_dat(self):
        """Open's A Dialog for Importing A Dat File."""
        dat_file = filedialog.askopenfilename(
            title="DAT-Datei importieren",
            filetypes=[("DAT-Dateien", "*.dat"), ("XML-Dateien", "*.xml"), ("Alle Dateien", "*.*")]
        )

        if not dat_file:
            return

# File exists
        if not os.path.exists(dat_file):
            messagebox.showerror("Fehler", "Die ausgewählte Datei existiert nicht.")
            return

# Start the Import Process in A separate thread
        def import_thread():
            try:
                from app import db_controller

                count = db_controller.import_dat(dat_file, db_path=self.db_path)

# Show the result
                self.dialog.after(0, lambda: messagebox.showinfo(
                    "Import abgeschlossen",
                    f"{count:,} Einträge wurden aus der DAT-Datei importiert."
                ))

# Update status
                self.dialog.after(0, self.update_database_status)

            except Exception as exc:
                self.dialog.after(0, lambda exc=exc: messagebox.showerror(
                    "Fehler",
                    f"Fehler beim Importieren der DAT-Datei:\n{exc}"
                ))

# Start thread
        threading.Thread(target=import_thread, daemon=True).start()

# Show to a Waiting Dialogue
        progress_dialog = tk.Toplevel(self.dialog)
        progress_dialog.title("Importiere DAT...")
        progress_dialog.geometry("300x100")
        progress_dialog.transient(self.dialog)
        progress_dialog.grab_set()

        ttk.Label(progress_dialog, text="Importiere DAT-Datei...\n"
                                       "Dies kann einige Minuten dauern.").pack(pady=10)

        progress = ttk.Progressbar(progress_dialog, mode='indeterminate')
        progress.pack(fill='x', padx=20)
        progress.start()

# Function to close the progress dialogue
        def check_thread_status():
            if threading.active_count() > 1:  # Hauptthread + Import-Thread
                progress_dialog.after(100, check_thread_status)
            else:
                progress_dialog.destroy()

        progress_dialog.after(100, check_thread_status)
