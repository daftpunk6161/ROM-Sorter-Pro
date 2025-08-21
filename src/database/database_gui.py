"""Database Management Dialog for Rome Database Integration. This module provides a gui interface for the management of the rome database."""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sqlite3
from pathlib import Path

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
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                     'rom_databases', 'rom_database.sqlite')

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
        try:
            if not os.path.exists(self.db_path):
                self.status_var.set(
                    "Keine Datenbank gefunden. Erstellen Sie eine Datenbank, indem Sie ROMs scannen "
                    "oder eine DAT-Datei importieren."
                )
                self._update_stats("Keine Datenbank vorhanden")
                return

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

# Number of ROMs
            cursor.execute("SELECT COUNT(*) FROM roms")
            rom_count = cursor.fetchone()[0]

# Number of consoles
            cursor.execute("SELECT COUNT(DISTINCT console) FROM roms")
            console_count = cursor.fetchone()[0]

# List of consoles and their number
            cursor.execute("SELECT console, COUNT(*) FROM roms GROUP BY console ORDER BY COUNT(*) DESC")
            console_stats = cursor.fetchall()

# Update status
            self.status_var.set(
                f"ROM-Datenbank gefunden: {rom_count:,} ROMs für {console_count} Konsolen."
            )

# Update statistics
            stats_text = f"Datenbankpfad: {self.db_path}\n"
            stats_text += f"Gesamtanzahl der ROMs: {rom_count:,}\n"
            stats_text += f"Anzahl der Konsolen: {console_count}\n\n"
            stats_text += "Top 10 Konsolen:\n"

            for i, (console, count) in enumerate(console_stats[:10], 1):
                stats_text += f"{i}. {console}: {count:,} ROMs\n"

            self._update_stats(stats_text)

            conn.close()

        except sqlite3.OperationalError as e:
# If the table does not exist, we initiate the database
            if "no such table: roms" in str(e):
                try:
                    from scripts.update_rom_database import setup_database
# Create database directory if necessary
                    os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
# Initialize database
                    conn = setup_database(self.db_path)
                    conn.close()
# Update status
                    self.status_var.set("Datenbank wurde initialisiert. Bitte fügen Sie ROMs hinzu.")
                    self._update_stats("Leere Datenbank wurde erstellt.\nVerwenden Sie 'ROMs scannen' oder 'DAT-Datei importieren', um Daten hinzuzufügen.")
                except Exception as init_err:
                    self.status_var.set(f"Fehler bei der Datenbankinitialisierung: {init_err}")
                    self._update_stats(f"Initialisierungsfehler: {init_err}\n\nBitte stellen Sie sicher, dass Sie Schreibberechtigungen haben.")
            else:
                self.status_var.set(f"Fehler beim Lesen der Datenbank: {e}")
                self._update_stats(f"Datenbankfehler: {e}\n\nBitte überprüfen Sie die Berechtigungen und Datenbankstruktur.")

        except Exception as e:
# General mistake
            self.status_var.set(f"Unerwarteter Fehler beim Lesen der Datenbank: {e}")
            self._update_stats(f"Fehler: {e}\n\nDiagnoseinformationen:\nDB-Pfad: {self.db_path}\nExistiert: {os.path.exists(self.db_path)}")
# For additional diagnosis
            from src.database.db_debug import debug_database_initialization
            debug_database_initialization(self.db_path)

    def _update_stats(self, text):
        """Updates the statistics text field."""
        self.stats_text.config(state='normal')
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, text)
        self.stats_text.config(state='disabled')

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
                from scripts.update_rom_database import scan_directory, setup_database

# Make sure the database directory exists
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

# Connect to the database
                conn = setup_database(self.db_path)

# Scanne the directory
                count = scan_directory(conn, rom_dir, recursive)

# Close the connection
                conn.close()

# Show the result
                self.dialog.after(0, lambda: messagebox.showinfo(
                    "Scan abgeschlossen",
                    f"{count:,} ROMs wurden zur Datenbank hinzugefügt."
                ))

# Update status
                self.dialog.after(0, self.update_database_status)

            except Exception as e:
                self.dialog.after(0, lambda: messagebox.showerror(
                    "Fehler",
                    f"Fehler beim Scannen des Verzeichnisses:\n{e}"
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
                from scripts.update_rom_database import import_dat_file, setup_database

# Make sure the database directory exists
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

# Connect to the database
                conn = setup_database(self.db_path)

# Import dat file
                count = import_dat_file(conn, dat_file)

# Close the connection
                conn.close()

# Show the result
                self.dialog.after(0, lambda: messagebox.showinfo(
                    "Import abgeschlossen",
                    f"{count:,} Einträge wurden aus der DAT-Datei importiert."
                ))

# Update status
                self.dialog.after(0, self.update_database_status)

            except Exception as e:
                self.dialog.after(0, lambda: messagebox.showerror(
                    "Fehler",
                    f"Fehler beim Importieren der DAT-Datei:\n{e}"
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
