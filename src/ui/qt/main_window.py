#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro v2.1.8 - Qt Main Window
Phase 1 Implementation: Desktop Optimization

This module contains the implementation of the main window with Qt 6.5+
for improved performance, modern design and cross-platform support.
"""

from typing import Dict, List, Optional, Any, Callable, Union, Tuple
import os
import sys
import logging
import threading
from pathlib import Path

try:
    from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                                QTabWidget, QLabel, QPushButton, QMessageBox, QFileDialog,
                                QProgressBar, QTableWidget, QTableWidgetItem, QComboBox, QMenu,
                                QMenuBar, QStatusBar, QSplitter, QLineEdit, QGroupBox, QCheckBox)
    from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, pyqtSlot, QTimer, QSettings, QUrl
    from PyQt6.QtGui import QIcon, QPixmap, QAction, QFont, QDesktopServices
except ImportError:
    # Fallback for older versions or if PYQT6 is not available
    from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                                QTabWidget, QLabel, QPushButton, QMessageBox, QFileDialog,
                                QProgressBar, QTableWidget, QTableWidgetItem, QComboBox, QMenu,
                                QMenuBar, QStatusBar, QSplitter, QLineEdit, QGroupBox, QCheckBox)
    from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, pyqtSlot, QTimer, QSettings, QUrl
    from PyQt5.QtGui import QIcon, QPixmap, QAction, QFont, QDesktopServices
    logging.warning("PyQt6 nicht gefunden, verwende PyQt5 als Fallback.")

# Lokale Importe
from ...config import Config
from ...exceptions import ROMSorterError, ConfigError
from ..theme_manager import ThemeManager
from ..custom_widgets import ClickableLabel, CollapsibleFrame

# Constants for uniform styling
WINDOW_TITLE = "ROM Sorter Pro 🎮 - Optimiert v3.0.0"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 600
PADDING = 10
DEFAULT_FONT = QFont("Segoe UI", 10)  # Cross -platform modern font

# Stylish colors (can be replaced later by themes)
COLORS = {
    "primary": "#3498db",
    "secondary": "#2ecc71",
    "error": "#e74c3c",
    "warning": "#f39c12",
    "info": "#2980b9",
    "background": "#f5f5f5",
    "text": "#333333",
    "border": "#dddddd"
}

class ScanWorkerThread(QThread):
    """Thread for scanning directories without UI blocking."""

    # Signals for communication with the main thread
    progress_updated = pyqtSignal(int, int)  # Aktuell/Gesamt
    rom_found = pyqtSignal(dict)  # ROM-Informationen
    scan_completed = pyqtSignal(dict)  # Zusammenfassungsdaten
    error_occurred = pyqtSignal(str)  # Fehlermeldung

    def __init__(self, scan_dir: str, config: dict):
        super().__init__()
        self.scan_dir = scan_dir
        self.config = config
        self.is_paused = False
        self.is_cancelled = False

    def run(self):
        """Performs the scanning process in the background."""
        try:
            # Here the actual scan logic would be implemented
            # Beispielimplementierung:
            import time
            import random

            files_to_scan = 100  # Simuliert
            self.progress_updated.emit(0, files_to_scan)

            for i in range(files_to_scan):
                # Check on a break or demolition
                while self.is_paused:
                    time.sleep(0.1)
                    if self.is_cancelled:
                        break

                if self.is_cancelled:
                    break

                # Simuliere Verarbeitung
                time.sleep(0.05)

                # Simuliere ROM-Fund
                if random.random() > 0.7:
                    rom_info = {
                        "name": f"ROM_{i}",
                        "path": f"{self.scan_dir}/rom_{i}.bin",
                        "size": random.randint(100000, 10000000),
                        "system": random.choice(["NES", "SNES", "Genesis", "PlayStation"]),
                        "crc32": f"{random.randint(0, 0xFFFFFFFF):08x}"
                    }
                    self.rom_found.emit(rom_info)

                self.progress_updated.emit(i+1, files_to_scan)

            # Scan abgeschlossen
            summary = {
                "total_files": files_to_scan,
                "roms_found": random.randint(20, 70),
                "duration_seconds": random.randint(10, 120)
            }
            self.scan_completed.emit(summary)

        except Exception as e:
            self.error_occurred.emit(str(e))

    def pause(self):
        """Pausiert den Scan-Thread."""
        self.is_paused = True

    def resume(self):
        """Setzt den pausierten Scan-Thread fort."""
        self.is_paused = False

    def cancel(self):
        """Bricht den Scan-Thread ab."""
        self.is_cancelled = True
        self.is_paused = False


class ROMSorterMainWindow(QMainWindow):
    """Main window of the Rome Sorter Pro application with QT."""

    def __init__(self, config=None):
        super().__init__()

        self.config = config or Config()
        self.theme_manager = ThemeManager()
        self.scan_thread = None
        self.roms_table_data = []

        self._init_ui()
        self._connect_signals()
        self._load_settings()

    def _init_ui(self):
        """Initialized the user interface."""
        # Grundlegende Fenstereinstellungen
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # Zentrale Widget-Erstellung
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Haupt-Layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(PADDING, PADDING, PADDING, PADDING)

        # Create the menu
        self._create_menus()

        # Main splinters for adaptable UI
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.main_splitter)

        # Left side - navigation and configuration area
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self._create_left_panel()
        self.main_splitter.addWidget(self.left_panel)

        # Right side - main area of work with tabs
        self.right_panel = QTabWidget()
        self._create_right_panel()
        self.main_splitter.addWidget(self.right_panel)

        # Set splitter sizes (30% left, 70% right)
        self.main_splitter.setSizes([int(WINDOW_WIDTH * 0.3), int(WINDOW_WIDTH * 0.7)])

        # Statusleiste erstellen
        self._create_statusbar()

    def _create_menus(self):
        """Creates the menu bar with all menus and actions."""
        # Create menu bar
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&Datei")

        # File menu campaigns
        open_action = QAction(QIcon(), "Verzeichnis öffnen...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_directory)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        export_action = QAction(QIcon(), "Ergebnisse exportieren...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._on_export_results)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction(QIcon(), "Beenden", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Bearbeiten")

        settings_action = QAction(QIcon(), "Einstellungen...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._on_open_settings)
        edit_menu.addAction(settings_action)

        # View menu
        view_menu = menubar.addMenu("&Ansicht")

        refresh_action = QAction(QIcon(), "Aktualisieren", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._on_refresh)
        view_menu.addAction(refresh_action)

        # Tool
        tools_menu = menubar.addMenu("&Tools")

        scan_action = QAction(QIcon(), "Scan starten", self)
        scan_action.setShortcut("F9")
        scan_action.triggered.connect(self._on_start_scan)
        tools_menu.addAction(scan_action)

        # Help menu
        help_menu = menubar.addMenu("&Hilfe")

        about_action = QAction(QIcon(), "Über ROM Sorter Pro...", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

        docs_action = QAction(QIcon(), "Dokumentation", self)
        docs_action.setShortcut("F1")
        docs_action.triggered.connect(self._on_open_docs)
        help_menu.addAction(docs_action)

    def _create_left_panel(self):
        """Creates the left panel with navigation and configuration."""
        # Scan-Bereich
        scan_group = QGroupBox("Scannen")
        scan_layout = QVBoxLayout(scan_group)

        # Verzeichnisauswahl
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Verzeichnis:")
        self.dir_input = QLineEdit()
        self.dir_input.setReadOnly(True)
        dir_button = QPushButton("...")
        dir_button.setMaximumWidth(30)
        dir_button.clicked.connect(self._on_open_directory)
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(dir_button)
        scan_layout.addLayout(dir_layout)

        # Scan-Optionen
        options_layout = QVBoxLayout()
        self.recursive_check = QCheckBox("Unterordner einbeziehen")
        self.recursive_check.setChecked(True)
        options_layout.addWidget(self.recursive_check)

        self.verify_check = QCheckBox("ROMs verifizieren")
        self.verify_check.setChecked(True)
        options_layout.addWidget(self.verify_check)

        scan_layout.addLayout(options_layout)

        # Scan-Aktionen
        actions_layout = QHBoxLayout()
        self.scan_button = QPushButton("Scan starten")
        self.scan_button.clicked.connect(self._on_start_scan)
        actions_layout.addWidget(self.scan_button)

        self.stop_button = QPushButton("Stoppen")
        self.stop_button.clicked.connect(self._on_stop_scan)
        self.stop_button.setEnabled(False)
        actions_layout.addWidget(self.stop_button)

        scan_layout.addLayout(actions_layout)

        # Fortschrittsanzeige
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Bereit")
        progress_layout.addWidget(self.progress_label)

        scan_layout.addLayout(progress_layout)

        # Filter-Bereich
        filter_group = QGroupBox("Filter")
        filter_layout = QVBoxLayout(filter_group)

        # Systemfilter
        system_layout = QHBoxLayout()
        system_label = QLabel("System:")
        self.system_combo = QComboBox()
        self.system_combo.addItem("Alle Systeme")
        self.system_combo.addItems(["NES", "SNES", "Genesis", "PlayStation", "N64", "Dreamcast"])
        system_layout.addWidget(system_label)
        system_layout.addWidget(self.system_combo)
        filter_layout.addLayout(system_layout)

        # Suche
        search_layout = QHBoxLayout()
        search_label = QLabel("Suche:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("ROM-Name suchen...")
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        filter_layout.addLayout(search_layout)

        # Linkes Panel zusammenbauen
        self.left_layout.addWidget(scan_group)
        self.left_layout.addWidget(filter_group)
        self.left_layout.addStretch(1)  # Add space at the bottom

    def _create_right_panel(self):
        """Creates the right panel with tabs for different views."""
        # Tab for Rome list
        self.roms_tab = QWidget()
        roms_layout = QVBoxLayout(self.roms_tab)

        # ROM-Tabelle
        self.roms_table = QTableWidget()
        self.roms_table.setColumnCount(5)
        self.roms_table.setHorizontalHeaderLabels(["Name", "System", "Größe", "CRC32", "Pfad"])
        self.roms_table.horizontalHeader().setStretchLastSection(True)
        self.roms_table.verticalHeader().setVisible(False)
        self.roms_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.roms_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        roms_layout.addWidget(self.roms_table)

        # Tab for statistics
        self.stats_tab = QWidget()
        stats_layout = QVBoxLayout(self.stats_tab)

        self.stats_label = QLabel("Noch keine Daten verfügbar.")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch(1)

        # Tab for log
        self.log_tab = QWidget()
        log_layout = QVBoxLayout(self.log_tab)

        self.log_text = QLineEdit()  # In a real application, a Qtextedit would be used here
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        # Add tabs
        self.right_panel.addTab(self.roms_tab, "ROMs")
        self.right_panel.addTab(self.stats_tab, "Statistik")
        self.right_panel.addTab(self.log_tab, "Log")

    def _create_statusbar(self):
        """Creates the status bar at the bottom of the window."""
        statusbar = self.statusBar()

        self.status_label = QLabel("Bereit")
        statusbar.addWidget(self.status_label, 1)

        self.rom_count_label = QLabel("0 ROMs gefunden")
        statusbar.addPermanentWidget(self.rom_count_label)

    def _connect_signals(self):
        """Verbindet alle Signal-Slot-Verbindungen."""
        # Connection to configuration changes
        # Here the signals from the configuration class would be connected in a complete implementation

    def _load_settings(self):
        """Loads the stored settings."""
        settings = QSettings("ROM Sorter Pro", "v3")

        # Window position and size
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        # Splitter sizes
        splitter_sizes = settings.value("splitter_sizes")
        if splitter_sizes:
            self.main_splitter.setSizes(splitter_sizes)

        # Letztes Scan-Verzeichnis
        last_dir = settings.value("last_directory", "")
        self.dir_input.setText(last_dir)

    def _save_settings(self):
        """Saves the current settings."""
        settings = QSettings("ROM Sorter Pro", "v3")

        # Window position and size
        settings.setValue("geometry", self.saveGeometry())

        # Splitter sizes
        settings.setValue("splitter_sizes", self.main_splitter.sizes())

        # Letztes Scan-Verzeichnis
        settings.setValue("last_directory", self.dir_input.text())

    def _update_rom_table(self, rom_info=None):
        """Updates the ROM table with new data."""
        if rom_info:
            # Add a new rome
            self.roms_table_data.append(rom_info)

            # Update the table
            row = self.roms_table.rowCount()
            self.roms_table.insertRow(row)

            # Fill the cell data
            self.roms_table.setItem(row, 0, QTableWidgetItem(rom_info["name"]))
            self.roms_table.setItem(row, 1, QTableWidgetItem(rom_info["system"]))

            # Format the size of user -friendly
            size_str = self._format_size(rom_info["size"])
            self.roms_table.setItem(row, 2, QTableWidgetItem(size_str))

            self.roms_table.setItem(row, 3, QTableWidgetItem(rom_info["crc32"]))
            self.roms_table.setItem(row, 4, QTableWidgetItem(rom_info["path"]))

            # Update the display jacket
            self.rom_count_label.setText(f"{len(self.roms_table_data)} ROMs gefunden")
        else:
            # Reset the table
            self.roms_table.setRowCount(0)
            self.roms_table_data = []
            self.rom_count_label.setText("0 ROMs gefunden")

    def _format_size(self, size_bytes):
        """Formatted bytes in A Readable Size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def _update_progress(self, current, total):
        """Updates the progress display."""
        if total <= 0:
            self.progress_bar.setValue(0)
            self.progress_label.setText("Bereit")
            return

        percentage = min(int(100 * current / total), 100)
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(f"Verarbeite: {current} / {total} Dateien ({percentage}%)")
        self.status_label.setText(f"Scan läuft... ({percentage}%)")

    def _update_status(self, message):
        """Updates the status bar with a message."""
        self.status_label.setText(message)

    def _handle_scan_error(self, error_message):
        """Treats error during the scanning process."""
        QMessageBox.critical(self, "Scan-Fehler", f"Fehler beim Scannen: {error_message}")
        self._update_status("Scan fehlgeschlagen")
        self._reset_scan_ui()

    def _handle_scan_completed(self, summary):
        """Behandelt den erfolgreichen Abschluss eines Scans."""
        # Update the status bar
        duration = summary.get("duration_seconds", 0)
        roms_found = summary.get("roms_found", 0)
        total_files = summary.get("total_files", 0)

        success_message = f"Scan abgeschlossen: {roms_found} ROMs in {duration} Sekunden gefunden (aus {total_files} Dateien)"
        self._update_status(success_message)

        # Update the statistics
        self._update_statistics(summary)

        # Set the UI back
        self._reset_scan_ui()

        # Zeige eine Erfolgsmeldung
        QMessageBox.information(self, "Scan abgeschlossen", success_message)

    def _update_statistics(self, summary):
        """Updates the statistics view with the scan results."""
        stats_text = f"""
        <h2>Scan-Zusammenfassung</h2>
        <ul>
            <li><b>ROMs gefunden:</b> {summary.get('roms_found', 0)}</li>
            <li><b>Gescannte Dateien:</b> {summary.get('total_files', 0)}</li>
            <li><b>Dauer:</b> {summary.get('duration_seconds', 0)} Sekunden</li>
            <li><b>Durchschnittliche Zeit pro Datei:</b> {summary.get('duration_seconds', 0) / max(summary.get('total_files', 1), 1):.4f} Sekunden</li>
        </ul>
        """

        self.stats_label.setText(stats_text)

    def _reset_scan_ui(self):
        """Put the ui back after a scan."""
        self.scan_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Bereit")

    def _on_open_directory(self):
        """Open's A Dialogue for the Directory Selection."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Verzeichnis zum Scannen auswählen",
            self.dir_input.text() or str(Path.home())
        )

        if directory:  # Not Empty if the user has made a selection
            self.dir_input.setText(directory)

    def _on_export_results(self):
        """Export the scan results into a file."""
        if not self.roms_table_data:
            QMessageBox.warning(self, "Export nicht möglich", "Keine ROMs zum Exportieren gefunden.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Ergebnisse exportieren",
            str(Path.home() / "rom_scan_results.csv"),
            "CSV-Dateien (*.csv);;Alle Dateien (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # CSV-Header
                    f.write("Name,System,Größe,CRC32,Pfad\n")

                    # Daten
                    for rom in self.roms_table_data:
                        size_str = self._format_size(rom["size"])
                        line = f"{rom['name']},{rom['system']},{size_str},{rom['crc32']},{rom['path']}\n"
                        f.write(line)

                QMessageBox.information(self, "Export erfolgreich", f"Daten wurden erfolgreich nach {file_path} exportiert.")

            except Exception as e:
                QMessageBox.critical(self, "Export fehlgeschlagen", f"Fehler beim Exportieren: {str(e)}")

    def _on_open_settings(self):
        """Opens the setting dialog."""
        # A separate setting dialog would be opened here
        QMessageBox.information(self, "Einstellungen", "Diese Funktion ist noch nicht implementiert.")

    def _on_refresh(self):
        """Updates the views."""
        # In a real application, the data would be ared here
        self._update_status("Ansicht aktualisiert")

    def _on_start_scan(self):
        """Startet den Scan-Vorgang."""
        scan_dir = self.dir_input.text()

        if not scan_dir or not os.path.isdir(scan_dir):
            QMessageBox.warning(self, "Ungültiges Verzeichnis",
                                "Bitte wählen Sie ein gültiges Verzeichnis zum Scannen aus.")
            return

        # Prepare Ui for the scan
        self._update_rom_table()  # Reset the table
        self.scan_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self._update_status("Scan wird gestartet...")

        # Scan-Konfiguration zusammenstellen
        scan_config = {
            "recursive": self.recursive_check.isChecked(),
            "verify": self.verify_check.isChecked()
        }

        # Create and start scan thread
        self.scan_thread = ScanWorkerThread(scan_dir, scan_config)
        self.scan_thread.progress_updated.connect(self._update_progress)
        self.scan_thread.rom_found.connect(self._update_rom_table)
        self.scan_thread.scan_completed.connect(self._handle_scan_completed)
        self.scan_thread.error_occurred.connect(self._handle_scan_error)

        self.scan_thread.start()

    def _on_stop_scan(self):
        """Stoppt den laufenden Scan-Vorgang."""
        if self.scan_thread and self.scan_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Scan stoppen",
                "Möchten Sie den laufenden Scan wirklich abbrechen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.scan_thread.cancel()
                self._update_status("Scan abgebrochen")
                self._reset_scan_ui()

    def _on_search_changed(self, text):
        """Filters the Rome table based on the search text."""
        for row in range(self.roms_table.rowCount()):
            show_row = False

            # Suche in allen Spalten
            for col in range(self.roms_table.columnCount()):
                item = self.roms_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    show_row = True
                    break

            self.roms_table.setRowHidden(row, not show_row)

    def _on_about(self):
        """Displays the over-dialog."""
        about_text = (
            f"<h2>ROM Sorter Pro v3.0.0</h2>"
            f"<p>Eine leistungsstarke Anwendung zur Organisation von ROM-Sammlungen</p>"
            f"<p>Copyright © 2025 ROM Sorter Pro Team</p>"
            f"<p>Diese Anwendung ist Teil der Desktop-Optimierungsphase (Phase 1) "
            f"der ROM Sorter Pro Roadmap 2025-2027.</p>"
        )

        QMessageBox.about(self, "Über ROM Sorter Pro", about_text)

    def _on_open_docs(self):
        """Opens the documentation."""
        # In a real application, The Local Documentation would be opened here
        # Or the online documentation in the browser
        QMessageBox.information(self, "Dokumentation", "Diese Funktion ist noch nicht implementiert.")

    def closeEvent(self, event):
        """Treats the closure of the window."""
        if self.scan_thread and self.scan_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Scan läuft",
                "Ein Scan läuft noch. Möchten Sie wirklich beenden?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.scan_thread.cancel()
            else:
                event.ignore()
                return

        # Save settings before ending
        self._save_settings()

        # Standardverhalten beibehalten
        event.accept()
