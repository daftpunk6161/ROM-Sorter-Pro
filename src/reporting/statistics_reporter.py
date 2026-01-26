#!/usr/bin/env python3
# -*-coding: utf-8-*-

"""ROM SARTER PRO - Extended statistics and reporting functions This module offers extensive analysis and report functions for Rome collections, including visualizations, export options and Detailed statistics. Features: - Detailed collection analysis (completeness, duplication) - Visualization of the collection statistics with diagrams - Export functions for reports (PDF, HTML, CSV) - custom reports and dashboards"""

import importlib
import os
import csv
import json
import logging
import datetime
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict

# Configure logger
logger = logging.getLogger(__name__)

# Attempts to import optional dependencies
try:
    pd = importlib.import_module("pandas")
    HAS_PANDAS = True
except Exception:
    pd = None
    HAS_PANDAS = False

try:
    matplotlib = importlib.import_module("matplotlib")
    plt = importlib.import_module("matplotlib.pyplot")
    matplotlib.use('Agg')  # Non-interactive backend for server environments
    HAS_MATPLOTLIB = True
except Exception:
    matplotlib = None
    plt = None
    HAS_MATPLOTLIB = False

try:
    jinja2 = importlib.import_module("jinja2")
    Environment = getattr(jinja2, "Environment", None)
    FileSystemLoader = getattr(jinja2, "FileSystemLoader", None)
    HAS_JINJA = Environment is not None and FileSystemLoader is not None
except Exception:
    Environment = None
    FileSystemLoader = None
    HAS_JINJA = False

try:
    weasyprint = importlib.import_module("weasyprint")
    HAS_WEASYPRINT = True
except Exception as e:
    logger.warning(f"WeasyPrint konnte nicht importiert werden: {e}")
    weasyprint = None
    HAS_WEASYPRINT = False

# Constant
REPORT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'reports')
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'reports')
CHART_DIR = os.path.join(REPORT_DIR, 'charts')

# Make sure the directories exist
os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)


class CollectionAnalyzer:
    """Analyzes Rome collections and generates detailed statistics."""

    def __init__(self, db_connection=None):
        """
        Initialisiert den CollectionAnalyzer.

        Args:
            db_connection: Verbindung zur ROM-Datenbank (optional)
        """
        self.db_connection = db_connection
        self.rom_data = None
        self.console_data = None
        self.statistics = {}
        self.duplicates = []
        self.missing_roms = []

    def load_data_from_db(self) -> bool:
        """Invites Rome data from the database. Return: True in the event of success, false in the event of errors"""
        if not self.db_connection:
            logger.error("Keine Datenbankverbindung verfügbar")
            return False

        try:
# Example: Acceptance of a SQLITE DATABASE WITH A Certain Structure
# In a real application, this would be adapted to the actual db Structure

# Rome's shop
            cursor = self.db_connection.cursor()
            cursor.execute("""
                SELECT r.id, r.name, r.file_path, r.size, r.hash, r.console_id, c.name as console_name
                FROM roms r
                JOIN consoles c ON r.console_id = c.id
            """)

            self.rom_data = [
                {
                    'id': row[0],
                    'name': row[1],
                    'file_path': row[2],
                    'size': row[3],
                    'hash': row[4],
                    'console_id': row[5],
                    'console_name': row[6]
                }
                for row in cursor.fetchall()
            ]

# Consoles shop
            cursor.execute("SELECT id, name, rom_count FROM consoles")
            self.console_data = [
                {'id': row[0], 'name': row[1], 'rom_count': row[2]}
                for row in cursor.fetchall()
            ]

            logger.info(f"Daten für {len(self.rom_data)} ROMs und {len(self.console_data)} Konsolen geladen")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Laden der Daten aus der Datenbank: {e}")
            return False

    def load_data_from_files(self, rom_file: str, console_file: Optional[str] = None) -> bool:
        """Invites Rome data from JSON or CSV files. Args: ROM_FILE: path to the Rome Date file Console_file: path to the console data file (optional) Return: True in the event of success, false in the event of errors"""
        try:
# Rome's shop
            if rom_file.endswith('.json'):
                with open(rom_file, 'r', encoding='utf-8') as f:
                    self.rom_data = json.load(f)
            elif rom_file.endswith('.csv'):
                if HAS_PANDAS and pd is not None:
                    self.rom_data = pd.read_csv(rom_file).to_dict('records')
                else:
                    with open(rom_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        self.rom_data = list(reader)
            else:
                logger.error(f"Nicht unterstütztes Dateiformat: {rom_file}")
                return False

# Load consoles, if specified
            if console_file:
                if console_file.endswith('.json'):
                    with open(console_file, 'r', encoding='utf-8') as f:
                        self.console_data = json.load(f)
                elif console_file.endswith('.csv'):
                    if HAS_PANDAS and pd is not None:
                        self.console_data = pd.read_csv(console_file).to_dict('records')
                    else:
                        with open(console_file, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            self.console_data = list(reader)
                else:
                    logger.warning(f"Nicht unterstütztes Dateiformat für Konsolen: {console_file}")

            logger.info(f"Daten für {len(self.rom_data)} ROMs geladen")
            if self.console_data:
                logger.info(f"Daten für {len(self.console_data)} Konsolen geladen")

            return True

        except Exception as e:
            logger.error(f"Fehler beim Laden der Daten aus Dateien: {e}")
            return False

    def analyze_collection(self) -> Dict[str, Any]:
        """Analyzes the Rome collection and generates detailed statistics. Return: Dictionary with statistics"""
        if not self.rom_data:
            logger.error("Keine ROM-Daten verfügbar")
            return {}

        try:
# Basic statistics
            self.statistics = {
                'total_roms': len(self.rom_data),
                'total_size': sum(float(rom.get('size') or 0) for rom in self.rom_data),
                'consoles': {},
                'file_formats': {},
                'size_distribution': {
                    'small': 0,    # < 1 MB
                    'medium': 0,   # 1-10 MB
                    'large': 0,    # 10-100 MB
                    'huge': 0      # > 100 MB
                },
                'analysis_date': datetime.datetime.now().isoformat()
            }

# Colot Rome Pro Console
            console_counter = Counter(rom.get('console_name', 'Unknown') for rom in self.rom_data)
            self.statistics['consoles'] = dict(console_counter)

# Tot file formats
            format_counter = Counter(
                os.path.splitext(rom.get('file_path', ''))[1].lower()
                for rom in self.rom_data if rom.get('file_path')
            )
            self.statistics['file_formats'] = dict(format_counter)

# Size distribution
            for rom in self.rom_data:
                size_mb = float(rom.get('size') or 0) / (1024 * 1024)
                if size_mb < 1:
                    self.statistics['size_distribution']['small'] += 1
                elif size_mb < 10:
                    self.statistics['size_distribution']['medium'] += 1
                elif size_mb < 100:
                    self.statistics['size_distribution']['large'] += 1
                else:
                    self.statistics['size_distribution']['huge'] += 1

# Find duplicates based on hash
            hash_map = defaultdict(list)
            for rom in self.rom_data:
                if rom.get('hash'):
                    hash_map[rom['hash']].append(rom)

            self.duplicates = [roms for roms in hash_map.values() if len(roms) > 1]
            self.statistics['duplicate_count'] = len(self.duplicates)
            self.statistics['duplicate_roms'] = sum(len(dups) for dups in self.duplicates)

# Analyze missing ROMs (if console_data is available with complete set lists)
            if self.console_data and any('complete_set' in console for console in self.console_data):
                self._analyze_missing_roms()
                self.statistics['missing_rom_count'] = len(self.missing_roms)

            logger.info(f"Sammlungsanalyse abgeschlossen: {len(self.rom_data)} ROMs, "
                      f"{self.statistics['duplicate_count']} Duplikate")

            return self.statistics

        except Exception as e:
            logger.error(f"Fehler bei der Sammlungsanalyse: {e}")
            return {}

    def _analyze_missing_roms(self) -> None:
        """Analyzes missing ROMs based on complete sets in console_data."""
        if not self.console_data or not self.rom_data:
            return

        self.missing_roms = []

# Collect existing Rome Hashes according to the console
        existing_roms = defaultdict(set)
        for rom in self.rom_data:
            console_id = rom.get('console_id')
            rom_hash = rom.get('hash')
            if console_id and rom_hash:
                existing_roms[console_id].add(rom_hash)

# Check for missing ROMs in complete sets
        for console in self.console_data:
            if 'complete_set' not in console:
                continue

            console_id = console['id']
            complete_set = console['complete_set']

# Compare the complete set with the existing ROMs
            for rom in complete_set:
                if not isinstance(rom, dict):
                    continue
                if rom.get('hash') not in existing_roms.get(console_id, set()):
                    missing_rom = rom.copy()
                    missing_rom['console_name'] = console.get('name', 'Unknown')
                    missing_rom['console_id'] = console_id
                    self.missing_roms.append(missing_rom)

    def get_duplicates(self) -> List[List[Dict[str, Any]]]:
        """Gives back found duplicates. Return: List of duplicate groups"""
        return self.duplicates

    def get_missing_roms(self) -> List[Dict[str, Any]]:
        """Gives back missing ROMs. Return: List of missing ROMs"""
        return self.missing_roms

    def get_statistics(self) -> Dict[str, Any]:
        """Gives back the generated statistics. Return: Statistics dictionary"""
        return self.statistics


class ReportGenerator:
    """Generates reports and visualizations from Rome collection statistics."""

    def __init__(self, analyzer: Optional[CollectionAnalyzer] = None):
        """
        Initialisiert den ReportGenerator.

        Args:
            analyzer: Optional vorhandener CollectionAnalyzer
        """
        self.analyzer = analyzer or CollectionAnalyzer()
        self.report_data = None
        self.charts = {}

    def set_analyzer(self, analyzer: CollectionAnalyzer) -> None:
        """
        Setzt den CollectionAnalyzer.

        Args:
            analyzer: CollectionAnalyzer-Instanz
        """
        self.analyzer = analyzer

    def prepare_report_data(self) -> Dict[str, Any]:
        """Prepare the data for a report. Return: Dictionary with Prepared Reporting Data"""
        if not self.analyzer.statistics:
            logger.warning("Keine Statistiken verfügbar, führe Analyse durch")
            self.analyzer.analyze_collection()

        stats = self.analyzer.statistics

# Create a Structured Amount of Data for the Report
        self.report_data = {
            'title': 'ROM-Sammlungsbericht',
            'generation_date': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            'summary': {
                'total_roms': stats.get('total_roms', 0),
                'total_size': self._format_size(stats.get('total_size', 0)),
                'total_consoles': len(stats.get('consoles', {})),
                'duplicate_count': stats.get('duplicate_count', 0)
            },
            'console_data': [
                {'name': console, 'count': count}
                for console, count in stats.get('consoles', {}).items()
            ],
            'format_data': [
                {'format': fmt or 'Unknown', 'count': count}
                for fmt, count in stats.get('file_formats', {}).items()
            ],
            'size_distribution': stats.get('size_distribution', {}),
            'duplicates': self._prepare_duplicates_data(),
            'missing_roms': self._prepare_missing_roms_data()
        }

        return self.report_data

    def _format_size(self, size_bytes: int) -> str:
        """Formats A size in bytes in a Readable form. Args: Size_bytes: Size in Bytes Return: Formatted Size"""
# Conversion into KB, MB, GB or TB
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.2f} {units[unit_index]}"

    def _prepare_duplicates_data(self) -> List[Dict[str, Any]]:
        """Prepare duplicate data for the report. Return: List with prepared duplicate information"""
        duplicates_data = []

        for i, dup_group in enumerate(self.analyzer.get_duplicates()[:20]):  # Begrenzen auf 20 Gruppen
            if len(dup_group) < 2:
                continue

            group_data = {
                'group_id': i + 1,
                'rom_name': dup_group[0].get('name', 'Unbekannt'),
                'console': dup_group[0].get('console_name', 'Unbekannt'),
                'count': len(dup_group),
                'total_size': self._format_size(int(sum(float(rom.get('size') or 0) for rom in dup_group))),
                'files': [
                    {
                        'path': rom.get('file_path', 'Unknown'),
                        'size': self._format_size(rom.get('size', 0))
                    }
                    for rom in dup_group
                ]
            }
            duplicates_data.append(group_data)

        return duplicates_data

    def _prepare_missing_roms_data(self) -> List[Dict[str, Any]]:
        """Prepares data on the lack of ROMs for the report. Return: List of information about missing ROMs"""
        missing_roms = self.analyzer.get_missing_roms()

# Group According to Console for A Better Reporting Structure
        consoles = defaultdict(list)
        for rom in missing_roms[:100]:  # Limit to 100 entries
            consoles[rom.get('console_name', 'Unbekannt')].append({
                'name': rom.get('name', 'Unbekannt'),
                'size': self._format_size(rom.get('size', 0)),
                'importance': rom.get('importance', 'Normal')
            })

        return [
            {'console': console, 'roms': roms}
            for console, roms in consoles.items()
        ]

    def generate_charts(self, output_dir: str = CHART_DIR) -> Dict[str, str]:
        """Generated diagrams for the report. Args: OutPut_dir: Output directory for diagrams Return: Dictionary with diagram paths"""
        if not HAS_MATPLOTLIB or plt is None:
            logger.warning("Matplotlib ist nicht installiert, keine Diagramme werden generiert")
            return {}

        if not self.report_data:
            self.prepare_report_data()
        if not isinstance(self.report_data, dict):
            return {}

        os.makedirs(output_dir, exist_ok=True)

# Create A Time Stamp for Clear File Names
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        try:
# 1. Console distribution (tortend diagram)
            console_file = self._generate_console_chart(output_dir, timestamp)

# 2. File format distribution (bar diagram)
            format_file = self._generate_format_chart(output_dir, timestamp)

# 3. Size distribution (bar diagram)
            size_file = self._generate_size_chart(output_dir, timestamp)

            self.charts = {
                'console_chart': console_file,
                'format_chart': format_file,
                'size_chart': size_file
            }

            return self.charts

        except Exception as e:
            logger.error(f"Fehler bei der Diagrammerstellung: {e}")
            return {}

    def _generate_console_chart(self, output_dir: str, timestamp: str) -> str:
        """Generates A Cake Diagram for the Console Distribution. Args: Output_dir: Edition Directory Timestamp: Time Stamp for the File Name Return: Path to Generated Diagram"""
        if not self.report_data or plt is None:
            return ""
# Prepare data
        consoles = []
        counts = []

# Sort by number and limit the top 10
        report = self.report_data or {}
        console_data = sorted(
            report.get('console_data', []),
            key=lambda x: x['count'],
            reverse=True
        )[:10]

        total_count = sum(item['count'] for item in report.get('console_data', []))
        other_count = total_count - sum(item['count'] for item in console_data)

        for item in console_data:
            consoles.append(item['name'])
            counts.append(item['count'])

# Add "others" when there are more than 10 consoles
        if other_count > 0:
            consoles.append('Andere')
            counts.append(other_count)

# Create the diagram
        plt.figure(figsize=(10, 8))
        plt.pie(counts, labels=consoles, autopct='%1.1f%%', startangle=90)
        plt.axis('equal')
        plt.title('ROM-Verteilung nach Konsole')

# Save the diagram
        output_file = os.path.join(output_dir, f'console_chart_{timestamp}.png')
        plt.savefig(output_file, dpi=100, bbox_inches='tight')
        plt.close()

        return output_file

    def _generate_format_chart(self, output_dir: str, timestamp: str) -> str:
        """Generates A Bar Diagram for the File Format Distribution. Args: Output_dir: Edition Directory Timestamp: Time Stamp for the File Name Return: Path to Generated Diagram"""
        if not self.report_data or plt is None:
            return ""
# Prepare data and sort by number
        report = self.report_data or {}
        format_data = sorted(
            report.get('format_data', []),
            key=lambda x: x['count'],
            reverse=True
        )[:8]  # Top 8 Formate

        formats = [item['format'] for item in format_data]
        counts = [item['count'] for item in format_data]

# Create the diagram
        plt.figure(figsize=(10, 6))
        plt.bar(formats, counts, color='skyblue')
        plt.xlabel('Dateiformat')
        plt.ylabel('Anzahl ROMs')
        plt.title('ROMs nach Dateiformat')
        plt.xticks(rotation=45)
        plt.tight_layout()

# Save the diagram
        output_file = os.path.join(output_dir, f'format_chart_{timestamp}.png')
        plt.savefig(output_file, dpi=100, bbox_inches='tight')
        plt.close()

        return output_file

    def _generate_size_chart(self, output_dir: str, timestamp: str) -> str:
        """Generates A Bar Diagram for the Size Distribution. Args: Output_dir: Edition Directory Timestamp: Time Stamp for the File Name Return: Path to Generated Diagram"""
        if not self.report_data or plt is None:
            return ""
# Data from the size distribution
        report = self.report_data or {}
        size_distribution = report.get('size_distribution', {})
        categories = ['Klein (<1MB)', 'Mittel (1-10MB)', 'Groß (10-100MB)', 'Sehr groß (>100MB)']
        values = [
            size_distribution.get('small', 0),
            size_distribution.get('medium', 0),
            size_distribution.get('large', 0),
            size_distribution.get('huge', 0)
        ]

# Create the diagram
        plt.figure(figsize=(10, 6))
        plt.bar(categories, values, color='lightgreen')
        plt.xlabel('Größenkategorie')
        plt.ylabel('Anzahl ROMs')
        plt.title('ROMs nach Größe')
        plt.tight_layout()

# Save the diagram
        output_file = os.path.join(output_dir, f'size_chart_{timestamp}.png')
        plt.savefig(output_file, dpi=100, bbox_inches='tight')
        plt.close()

        return output_file

    def export_csv(self, output_file: str) -> bool:
        """Export the Statistics Data as a CSV File. Args: Output_file: Path to the Issuing File Return: True in the event of Success, False in the event of errors"""
        if not self.report_data:
            self.prepare_report_data()
        if not isinstance(self.report_data, dict):
            return False

        try:
# Create a flat dictionary for csv export
            flat_data = []

# Console data
            report = self.report_data or {}
            for console in report.get('console_data', []):
                flat_data.append({
                    'Typ': 'Konsole',
                    'Name': console['name'],
                    'Anzahl': console['count']
                })

# Format data
            for format_item in report.get('format_data', []):
                flat_data.append({
                    'Typ': 'Format',
                    'Name': format_item['format'],
                    'Anzahl': format_item['count']
                })

# Size distribution
            size_mapping = {
                'small': 'Klein (<1MB)',
                'medium': 'Mittel (1-10MB)',
                'large': 'Groß (10-100MB)',
                'huge': 'Sehr groß (>100MB)'
            }

            for size_key, size_name in size_mapping.items():
                flat_data.append({
                    'Typ': 'Größe',
                    'Name': size_name,
                    'Anzahl': report.get('size_distribution', {}).get(size_key, 0)
                })

# Write the CSV file
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['Typ', 'Name', 'Anzahl']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(flat_data)

            logger.info(f"CSV-Bericht gespeichert unter {output_file}")
            return True

        except Exception as e:
            logger.error(f"Fehler beim CSV-Export: {e}")
            return False

    def export_html(self, output_file: str, include_charts: bool = True) -> bool:
        """Exports an HTML report. Args: output_file: path to the issuing file Include_charts: Whether diagrams should be included Return: True in the event of success, false in the event of errors"""
        if not HAS_JINJA or Environment is None or FileSystemLoader is None:
            logger.error("Jinja2 ist nicht installiert, HTML-Export ist nicht möglich")
            return False

        if not self.report_data:
            self.prepare_report_data()

        try:
# Generate diagrams, if desired
            if include_charts and HAS_MATPLOTLIB:
                chart_dir = os.path.join(os.path.dirname(os.path.abspath(output_file)), 'charts')
                os.makedirs(chart_dir, exist_ok=True)

                charts = self.generate_charts(chart_dir)

# Relative paths for HTML
                rel_charts = {}
                for chart_name, chart_path in charts.items():
                    rel_charts[chart_name] = os.path.join(
                        'charts',
                        os.path.basename(chart_path)
                    )
            else:
                rel_charts = {}

# Charge the template
            template_path = os.path.join(TEMPLATE_DIR, 'report_template.html')

# If the Template Does Not Exist, Create A Standard Template
            if not os.path.exists(template_path):
                os.makedirs(os.path.dirname(template_path), exist_ok=True)
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(self._get_default_html_template())

# Create a Jinja2 Environment
            env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
            template = env.get_template(os.path.basename(template_path))

# Renders the template
            html_content = template.render(
                report=self.report_data or {},
                charts=rel_charts
            )

# Write the HTML file
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"HTML-Bericht gespeichert unter {output_file}")
            return True

        except Exception as e:
            logger.error(f"Fehler beim HTML-Export: {e}")
            return False

    def _get_default_html_template(self) -> str:
        """Delivers A Standard HTML Template for Reports. Return: HTML Template as a String"""
        return """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ report.title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        .summary {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
        }
        .summary-item {
            background-color: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .summary-item h3 {
            margin-top: 0;
            font-size: 16px;
            color: #666;
        }
        .summary-item p {
            margin: 0;
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }
        .chart-container {
            margin: 30px 0;
            text-align: center;
        }
        .chart-container img {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .footer {
            margin-top: 50px;
            text-align: center;
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ report.title }}</h1>
        <p>Erstellt am {{ report.generation_date }}</p>

        <div class="summary">
            <h2>Zusammenfassung</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <h3>Anzahl ROMs</h3>
                    <p>{{ report.summary.total_roms }}</p>
                </div>
                <div class="summary-item">
                    <h3>Gesamtgroesse</h3>
                    <p>{{ report.summary.total_size }}</p>
                </div>
                <div class="summary-item">
                    <h3>Konsolen</h3>
                    <p>{{ report.summary.total_consoles }}</p>
                </div>
                <div class="summary-item">
                    <h3>Duplikate</h3>
                    <p>{{ report.summary.duplicate_count }}</p>
                </div>
            </div>
        </div>

        <!-- Diagramme, falls vorhanden -->
        {% if charts %}
        <h2>Visualisierungen</h2>

        {% if charts.console_chart %}
        <div class="chart-container">
            <h3>ROM-Verteilung nach Konsole</h3>
            <img src="{{ charts.console_chart }}" alt="Konsolenverteilung">
        </div>
        {% endif %}

        {% if charts.format_chart %}
        <div class="chart-container">
            <h3>ROMs nach Dateiformat</h3>
            <img src="{{ charts.format_chart }}" alt="Formatverteilung">
        </div>
        {% endif %}

        {% if charts.size_chart %}
        <div class="chart-container">
            <h3>ROMs nach Groesse</h3>
            <img src="{{ charts.size_chart }}" alt="Groessenverteilung">
        </div>
        {% endif %}
        {% endif %}

        <!-- Konsolenverteilung -->
        <h2>ROM-Verteilung nach Konsole</h2>
        <table>
            <thead>
                <tr>
                    <th>Konsole</th>
                    <th>Anzahl ROMs</th>
                </tr>
            </thead>
            <tbody>
                {% for console in report.console_data %}
                <tr>
                    <td>{{ console.name }}</td>
                    <td>{{ console.count }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <!-- Dateiformat-Verteilung -->
        <h2>ROM-Verteilung nach Dateiformat</h2>
        <table>
            <thead>
                <tr>
                    <th>Format</th>
                    <th>Anzahl ROMs</th>
                </tr>
            </thead>
            <tbody>
                {% for format in report.format_data %}
                <tr>
                    <td>{{ format.format }}</td>
                    <td>{{ format.count }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <!-- Duplikate -->
        {% if report.duplicates %}
        <h2>Duplikate</h2>
        {% for dup in report.duplicates %}
        <h3>Duplikat-Gruppe #{{ dup.group_id }}: {{ dup.rom_name }} ({{ dup.count }} Dateien)</h3>
        <table>
            <thead>
                <tr>
                    <th>Dateipfad</th>
                    <th>Groesse</th>
                </tr>
            </thead>
            <tbody>
                {% for file in dup.files %}
                <tr>
                    <td>{{ file.path }}</td>
                    <td>{{ file.size }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endfor %}
        {% endif %}

        <!-- Fehlende ROMs -->
        {% if report.missing_roms %}
        <h2>Fehlende ROMs</h2>
        {% for console in report.missing_roms %}
        <h3>{{ console.console }}</h3>
        <table>
            <thead>
                <tr>
                    <th>ROM-Name</th>
                    <th>Groesse</th>
                    <th>Wichtigkeit</th>
                </tr>
            </thead>
            <tbody>
                {% for rom in console.roms %}
                <tr>
                    <td>{{ rom.name }}</td>
                    <td>{{ rom.size }}</td>
                    <td>{{ rom.importance }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endfor %}
        {% endif %}

        <div class="footer">
            <p>ROM Sorter Pro - Sammlungsbericht</p>
            <p>Erstellt am {{ report.generation_date }}</p>
        </div>
    </div>
</body>
</html>"""

    def export_pdf(self, output_file: str) -> bool:
        """Export A PDF Report Based on the HTML Report. Args: Output_file: Path to the Issuing File Return: True in the event of Success, False in the event of errors"""
        if not HAS_WEASYPRINT or weasyprint is None:
            logger.error("WeasyPrint ist nicht installiert, PDF-Export ist nicht möglich")
            return False

        try:
# First create an HTML report
            html_file = output_file.replace('.pdf', '.html')
            if not self.export_html(html_file, include_charts=True):
                return False

# Convert html to pdf
            html = weasyprint.HTML(filename=html_file)
            html.write_pdf(output_file)

            logger.info(f"PDF-Bericht gespeichert unter {output_file}")
            return True

        except Exception as e:
            logger.error(f"Fehler beim PDF-Export: {e}")
            return False

    def export_json(self, output_file: str) -> bool:
        """Export the Statistics Data as a Json File. Args: Output_file: Path to the Issuing File Return: True in the event of Success, False in the event of errors"""
        if not self.report_data:
            self.prepare_report_data()

        try:
# Write the JSON file
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.report_data, f, indent=2, ensure_ascii=False)

            logger.info(f"JSON-Bericht gespeichert unter {output_file}")
            return True

        except Exception as e:
            logger.error(f"Fehler beim JSON-Export: {e}")
            return False


def _format_size_bytes(size_bytes: Any) -> str:
    try:
        size = float(size_bytes or 0)
    except Exception:
        size = 0.0
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def _normalize_scan_items(scan_result: Any) -> List[Dict[str, Any]]:
    items: List[Any] = []
    if hasattr(scan_result, "items"):
        items = list(getattr(scan_result, "items") or [])
    elif isinstance(scan_result, dict):
        items = list(scan_result.get("items") or scan_result.get("roms") or [])

    normalized: List[Dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            raw = dict(item)
        else:
            raw = dict(getattr(item, "raw", {}) or {})
            raw.setdefault("detected_system", getattr(item, "detected_system", None))
            raw.setdefault("detection_confidence", getattr(item, "detection_confidence", None))
            raw.setdefault("detection_source", getattr(item, "detection_source", None))
            raw.setdefault("input_path", getattr(item, "input_path", None))

        normalized.append(raw)

    return normalized


def export_scan_results_csv(scan_result: Any, output_file: str) -> bool:
    """Export scan results with heuristic signals and candidates to CSV."""
    try:
        items = _normalize_scan_items(scan_result)
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Name",
                "System",
                "Confidence",
                "Signals",
                "Candidates",
                "Size",
                "CRC32",
                "Path",
                "DetectionSource",
            ])

            for rom in items:
                name = rom.get("name") or rom.get("title")
                path = rom.get("path") or rom.get("input_path") or rom.get("file")
                system = rom.get("system") or rom.get("detected_system") or "Unknown"
                confidence = rom.get("detection_confidence") or rom.get("confidence")
                source = rom.get("detection_source")
                size = _format_size_bytes(rom.get("size"))
                signals = rom.get("signals") or []
                if not isinstance(signals, list):
                    signals = [str(signals)]
                candidates = rom.get("candidates") or rom.get("candidate_systems") or []
                if not isinstance(candidates, list):
                    candidates = [str(candidates)]

                writer.writerow([
                    name or "",
                    system,
                    confidence if confidence is not None else "",
                    "; ".join(str(s) for s in signals if s),
                    "; ".join(str(c) for c in candidates if c),
                    size,
                    rom.get("crc32") or "",
                    path or "",
                    source or "",
                ])

        logger.info(f"Scan-CSV gespeichert unter {output_file}")
        return True

    except Exception as e:
        logger.error(f"Fehler beim Scan-CSV-Export: {e}")
        return False


def export_scan_results_json(scan_result: Any, output_file: str) -> bool:
    """Export scan results with heuristic signals and candidates to JSON."""
    try:
        items = _normalize_scan_items(scan_result)
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

        payload = {
            "source_path": getattr(scan_result, "source_path", None),
            "stats": getattr(scan_result, "stats", None),
            "cancelled": getattr(scan_result, "cancelled", None),
            "items": items,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        logger.info(f"Scan-JSON gespeichert unter {output_file}")
        return True

    except Exception as e:
        logger.error(f"Fehler beim Scan-JSON-Export: {e}")
        return False


def generate_collection_report(db_connection=None, output_dir: str = REPORT_DIR,
                             formats: Optional[List[str]] = None) -> Dict[str, str]:
    """Generates A Collection Report in different formats. ARGS: DB_CONNECTION: DATABASE Connection (optional) Output_Dir: Output Directory for Reports Format: List of the Desired Formats ('HTML', 'PDF', 'CSV', 'JSON') Return: Dictionary with paths to the generated Reports"""
    if formats is None:
        formats = ['html']

# Make sure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

# Create timing stamp for clear file names
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

# Initialistically analyzer and generator
    analyzer = CollectionAnalyzer(db_connection)

# Charging data and analyze the collection
    if db_connection:
        analyzer.load_data_from_db()
    else:
# Example data for tests
        logger.warning("Keine DB-Verbindung, verwende Beispieldaten")
        analyzer.rom_data = [
            {'name': f'ROM {i}', 'console_name': f'Console {i%5}',
             'file_path': f'/path/to/rom{i}.rom', 'size': i*1024*1024,
             'hash': f'hash{i}'}
            for i in range(1, 101)
        ]

    analyzer.analyze_collection()

# Generate reports
    generator = ReportGenerator(analyzer)
    generator.prepare_report_data()

    reports = {}

# Generate the desired report formats
    if 'html' in formats:
        html_file = os.path.join(output_dir, f'collection_report_{timestamp}.html')
        if generator.export_html(html_file):
            reports['html'] = html_file

    if 'pdf' in formats and HAS_WEASYPRINT:
        pdf_file = os.path.join(output_dir, f'collection_report_{timestamp}.pdf')
        if generator.export_pdf(pdf_file):
            reports['pdf'] = pdf_file

    if 'csv' in formats:
        csv_file = os.path.join(output_dir, f'collection_report_{timestamp}.csv')
        if generator.export_csv(csv_file):
            reports['csv'] = csv_file

    if 'json' in formats:
        json_file = os.path.join(output_dir, f'collection_report_{timestamp}.json')
        if generator.export_json(json_file):
            reports['json'] = json_file

    return reports


# Example of using the module functions
if __name__ == "__main__":
# Configure logging
    logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    print("ROM Sorter Pro - Statistik- und Berichtsmodul")
    print("-----------------------------------------")

# Generates A Sample Report
    reports = generate_collection_report(formats=['html', 'csv', 'json'])

    if reports:
        print("Berichte generiert:")
        for format_name, report_path in reports.items():
            print(f"- {format_name.upper()}: {report_path}")
    else:
        print("Keine Berichte generiert.")
