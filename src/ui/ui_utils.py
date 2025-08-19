#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - UI-Komponenten

Dieses Modul stellt verbesserte UI-Komponenten für die Konsole bereit.
"""

import os
import sys
import time
import threading
import shutil
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta


class ProgressBar:
    """
    Verbesserte Fortschrittsanzeige mit mehreren Anzeigeformaten.

    Features:
    - Dynamische Größenanpassung an Terminalbreite
    - Mehrere Anzeigestile
    - ETA-Berechnung
    - Anpassbare Farben und Formatierung
    - Thread-sicheres Update
    """

    STYLES = {
        'default': {'char': '█', 'empty': '░', 'left': '[', 'right': ']'},
        'simple': {'char': '#', 'empty': '-', 'left': '|', 'right': '|'},
        'arrow': {'char': '>', 'empty': ' ', 'left': '[', 'right': ']'},
        'dots': {'char': '•', 'empty': '◦', 'left': '', 'right': ''}
    }

    def __init__(self,
                 total: int,
                 prefix: str = '',
                 suffix: str = '',
                 style: str = 'default',
                 length: Optional[int] = None,
                 fill_char: Optional[str] = None,
                 empty_char: Optional[str] = None,
                 show_percent: bool = True,
                 show_eta: bool = True,
                 update_interval: float = 0.1,
                 file=sys.stdout):
        """
        Initialisiert eine neue Fortschrittsanzeige.

        Args:
            total: Gesamtzahl der zu verarbeitenden Elemente
            prefix: Präfix vor dem Fortschrittsbalken
            suffix: Suffix nach dem Fortschrittsbalken
            style: Vordefinierter Stil ('default', 'simple', 'arrow', 'dots')
            length: Länge des Fortschrittsbalkens (None für automatisch)
            fill_char: Anpassbares Füllzeichen (überschreibt Stil)
            empty_char: Anpassbares Leerzeichen (überschreibt Stil)
            show_percent: Prozentangabe anzeigen
            show_eta: Geschätzte verbleibende Zeit anzeigen
            update_interval: Minimale Zeit zwischen Updates
            file: Ausgabedatei (Standard: sys.stdout)
        """
        self.total = max(total, 1)  # Vermeide Division durch Null
        self.prefix = prefix
        self.suffix = suffix
        self.style = self.STYLES.get(style, self.STYLES['default'])
        self.fill_char = fill_char if fill_char else self.style['char']
        self.empty_char = empty_char if empty_char else self.style['empty']
        self.show_percent = show_percent
        self.show_eta = show_eta
        self.update_interval = update_interval
        self.file = file

        self.progress = 0
        self.last_update_time = 0
        self.start_time = time.time()
        self._lock = threading.RLock()
        self._first_update = True

        # Dynamic size adjustment
        if length is None:
            try:
                terminal_width = shutil.get_terminal_size().columns
                # Reserve space for text around the bar
                reserved_space = len(prefix) + len(suffix) + 10  # +10 for percent etc
                self.bar_length = max(10, terminal_width - reserved_space)
            except (AttributeError, OSError):
                self.bar_length = 50  # Fallback
        else:
            self.bar_length = length

    def update(self, progress: int, suffix: Optional[str] = None) -> None:
        """
        Aktualisiert den Fortschrittsbalken.

        Args:
            progress: Aktuelle Fortschrittsposition
            suffix: Optionaler neuer Suffix-Text
        """
        current_time = time.time()

        # Update only when the interval is reached or at first/last update
        if (current_time - self.last_update_time < self.update_interval and
            not self._first_update and
            progress < self.total):
            return

        self._first_update = False
        self.last_update_time = current_time

        with self._lock:
            self.progress = min(progress, self.total)

            # Prozentsatz berechnen
            percent = self.progress / self.total

            # ETA berechnen
            if self.show_eta and self.progress > 0:
                elapsed = current_time - self.start_time
                remaining = (elapsed / self.progress) * (self.total - self.progress)
                eta_str = self._format_time(remaining)
                eta_display = f" ETA: {eta_str}"
            else:
                eta_display = ""

            # Prozentanzeige
            percent_display = f" {int(percent * 100):3d}%" if self.show_percent else ""

            # Fortschrittsbalken erstellen
            filled_length = int(self.bar_length * percent)
            bar = (self.style['left'] +
                   self.fill_char * filled_length +
                   self.empty_char * (self.bar_length - filled_length) +
                   self.style['right'])

            # Suffix aktualisieren, wenn angegeben
            if suffix is not None:
                self.suffix = suffix

            # Fortschritt anzeigen
            print(f"\r{self.prefix}{bar}{percent_display}{eta_display} {self.suffix}",
                  end='', file=self.file, flush=True)

            # Line line when you're done
            if self.progress >= self.total:
                elapsed = current_time - self.start_time
                total_time = self._format_time(elapsed)
                print(f"\r{self.prefix}{bar} Abgeschlossen in {total_time} {self.suffix}",
                      file=self.file)

    def _format_time(self, seconds: float) -> str:
        """
        Formatiert Sekunden in eine lesbare Zeitangabe.

        Args:
            seconds: Zeit in Sekunden

        Returns:
            Formatierte Zeit als String
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}min"
        else:
            return f"{seconds/3600:.1f}h"


class MultiProgressDisplay:
    """
    Verwaltet mehrere Fortschrittsbalken für parallele Aufgaben.
    """

    def __init__(self, clear_on_exit: bool = True):
        """
        Initialisiert einen Multi-Fortschritts-Manager.

        Args:
            clear_on_exit: Bereinigt den Bildschirm beim Beenden
        """
        self.bars: Dict[str, ProgressBar] = {}
        self.clear_on_exit = clear_on_exit
        self._lock = threading.RLock()

    def add_bar(self,
                name: str,
                total: int,
                prefix: str = '',
                **kwargs) -> None:
        """
        Fügt einen neuen Fortschrittsbalken hinzu.

        Args:
            name: Eindeutiger Name für den Balken
            total: Gesamtzahl der zu verarbeitenden Elemente
            prefix: Präfix vor dem Balken
            **kwargs: Weitere Parameter für ProgressBar
        """
        with self._lock:
            self.bars[name] = ProgressBar(total=total, prefix=prefix, **kwargs)

    def update(self, name: str, progress: int, suffix: Optional[str] = None) -> None:
        """
        Aktualisiert einen bestimmten Fortschrittsbalken.

        Args:
            name: Name des zu aktualisierenden Balkens
            progress: Aktuelle Fortschrittsposition
            suffix: Optionaler Suffix-Text
        """
        with self._lock:
            if name in self.bars:
                self.bars[name].update(progress, suffix)

    def remove(self, name: str) -> None:
        """
        Entfernt einen Fortschrittsbalken.

        Args:
            name: Name des zu entfernenden Balkens
        """
        with self._lock:
            if name in self.bars:
                del self.bars[name]

    def __enter__(self):
        """Context Manager Eintritt."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context Manager Austritt.
        Bereinigt die Fortschrittsbalken.
        """
        if self.clear_on_exit:
            print("\033[2J\033[H", end="")  # Clear screen


class StatusDisplay:
    """
    Statusanzeige für laufende Prozesse ohne definierte Fortschrittslänge.
    """

    def __init__(self,
                 prefix: str = '',
                 spinner_type: str = 'dots',
                 update_interval: float = 0.1,
                 file=sys.stdout):
        """
        Initialisiert eine neue Statusanzeige.

        Args:
            prefix: Anzuzeigender Präfixtext
            spinner_type: Art des Spinners ('dots', 'braille', 'bar', 'arrows')
            update_interval: Aktualisierungsintervall in Sekunden
            file: Ausgabedatei
        """
        self.prefix = prefix
        self.update_interval = update_interval
        self.file = file
        self._running = False
        self._thread = None
        self._lock = threading.RLock()
        self._current_status = ""

        # Spinner-Typen
        self._spinners = {
            'dots': ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
            'braille': ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'],
            'bar': ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█', '▇', '▆', '▅', '▄', '▃', '▂'],
            'arrows': ['←', '↖', '↑', '↗', '→', '↘', '↓', '↙']
        }

        self._spinner_frames = self._spinners.get(spinner_type, self._spinners['dots'])

    def start(self, status_text: str = "") -> None:
        """
        Startet die Statusanzeige in einem separaten Thread.

        Args:
            status_text: Anfänglicher Statustext
        """
        with self._lock:
            if self._running:
                return

            self._current_status = status_text
            self._running = True
            self._thread = threading.Thread(target=self._update_status, daemon=True)
            self._thread.start()

    def update_status(self, status_text: str) -> None:
        """
        Aktualisiert den angezeigten Statustext.

        Args:
            status_text: Neuer Statustext
        """
        with self._lock:
            self._current_status = status_text

    def stop(self, final_message: Optional[str] = None) -> None:
        """
        Stoppt die Statusanzeige.

        Args:
            final_message: Optionale Abschlussnachricht
        """
        with self._lock:
            if not self._running:
                return

            self._running = False

            if self._thread:
                self._thread.join(timeout=1.0)

            # Letzte Nachricht anzeigen
            if final_message:
                print(f"\r{final_message}", file=self.file)
            else:
                # Delete line
                terminal_width = shutil.get_terminal_size().columns
                print(f"\r{' ' * terminal_width}\r", end="", file=self.file)

    def _update_status(self) -> None:
        """Thread-Methode für die Statusaktualisierung."""
        idx = 0

        while self._running:
            with self._lock:
                spinner_char = self._spinner_frames[idx % len(self._spinner_frames)]
                status = self._current_status

            print(f"\r{self.prefix} {spinner_char} {status}", end="", file=self.file, flush=True)

            idx += 1
            time.sleep(self.update_interval)

    def __enter__(self):
        """Context Manager Eintritt."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Austritt."""
        if exc_type:
            self.stop(f"Fehler: {exc_val}")
        else:
            self.stop("Fertig")


def print_box(title: str, content: str, width: int = 80, style: str = 'single') -> None:
    """
    Gibt eine Box mit Titel und Inhalt aus.

    Args:
        title: Titel der Box
        content: Inhalt der Box
        width: Breite der Box
        style: Boxstil ('single', 'double', 'rounded', 'bold')
    """
    box_styles = {
        'single': {'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘', 'h': '─', 'v': '│', 'lt': '├', 'rt': '┤'},
        'double': {'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝', 'h': '═', 'v': '║', 'lt': '╠', 'rt': '╣'},
        'rounded': {'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯', 'h': '─', 'v': '│', 'lt': '├', 'rt': '┤'},
        'bold': {'tl': '┏', 'tr': '┓', 'bl': '┗', 'br': '┛', 'h': '━', 'v': '┃', 'lt': '┣', 'rt': '┫'}
    }

    box = box_styles.get(style, box_styles['single'])

    # Echte Terminalbreite berechnen, falls width = 0
    if width == 0:
        try:
            width = shutil.get_terminal_size().columns
        except (AttributeError, OSError):
            width = 80

    # Upper boxing line with title
    title_display = f" {title} " if title else ""
    title_len = len(title_display)
    left_pad = (width - title_len) // 2
    right_pad = width - left_pad - title_len

    print(f"{box['tl']}{box['h'] * left_pad}{title_display}{box['h'] * right_pad}{box['tr']}")

    # Inhalt zeilenweise
    lines = content.split('\n')
    for line in lines:
        # Call lines for too long
        while len(line) > width - 2:
            print(f"{box['v']} {line[:width-4]} {box['v']}")
            line = line[width-4:]

        # Zeile ausgeben
        padding = ' ' * (width - len(line) - 2)
        print(f"{box['v']} {line}{padding}{box['v']}")

    # Untere Boxzeile
    print(f"{box['bl']}{box['h'] * width}{box['br']}")


def print_table(data: List[List[Any]], headers: List[str], title: Optional[str] = None) -> None:
    """
    Gibt eine formatierte Tabelle aus.

    Args:
        data: Liste von Zeilen mit Daten
        headers: Spaltentitel
        title: Optionaler Tabellentitel
    """
    if not data and not headers:
        return

    # Spaltenbreiten berechnen
    num_cols = max(len(headers), max(len(row) for row in data) if data else 0)
    headers = headers + [''] * (num_cols - len(headers))

    # Bring each line to the same length
    normalized_data = []
    for row in data:
        normalized_data.append(row + [''] * (num_cols - len(row)))

    # Spaltenbreiten bestimmen
    col_widths = [max(len(str(row[i])) for row in normalized_data + [headers]) for i in range(num_cols)]

    # Gesamtbreite berechnen
    separator_width = 1  # Width of the separator between columns
    total_width = sum(col_widths) + separator_width * (num_cols + 1)

    # Tabellenkopf
    if title:
        print(f" {title} ".center(total_width, '='))

    # Kopfzeile
    header_str = '│'
    for i, header in enumerate(headers):
        header_str += f" {header.ljust(col_widths[i])} │"
    print(header_str)

    # Trenner
    separator = '├' + '┼'.join('─' * (width + 2) for width in col_widths) + '┤'
    print(separator)

    # Datenzeilen
    for row in normalized_data:
        row_str = '│'
        for i, cell in enumerate(row):
            row_str += f" {str(cell).ljust(col_widths[i])} │"
        print(row_str)

    # Untere Grenze
    bottom_border = '└' + '┴'.join('─' * (width + 2) for width in col_widths) + '┘'
    print(bottom_border)


def confirm_action(prompt: str, default: bool = False) -> bool:
    """
    Fordert den Benutzer zur Bestätigung einer Aktion auf.

    Args:
        prompt: Anzuzeigender Text
        default: Standardaktion (True = Ja, False = Nein)

    Returns:
        Benutzerentscheidung als Boolean
    """
    yes_choices = ['j', 'ja', 'y', 'yes', '1']
    no_choices = ['n', 'nein', 'no', '0']

    default_text = " [J/n]" if default else " [j/N]"

    while True:
        user_input = input(f"{prompt}{default_text}: ").strip().lower()

        if not user_input:
            return default

        if user_input in yes_choices:
            return True
        if user_input in no_choices:
            return False

        print("Ungültige Eingabe. Bitte 'j' oder 'n' eingeben.")


def print_color(text: str, color: str = 'white', bold: bool = False) -> None:
    """
    Gibt farbigen Text aus.

    Args:
        text: Auszugebender Text
        color: Farbe ('red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white')
        bold: Text fett darstellen
    """
    colors = {
        'black': 30, 'red': 31, 'green': 32, 'yellow': 33,
        'blue': 34, 'magenta': 35, 'cyan': 36, 'white': 37
    }

    color_code = colors.get(color.lower(), 37)  # Standard: white
    bold_code = 1 if bold else 0

    print(f"\033[{bold_code};{color_code}m{text}\033[0m")
