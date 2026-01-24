#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ROM Sorter Pro - Automatic Update Manager

This module implements an automatic update manager that searches for updates,
downloads and installs them. It supports updating program files, databases,
and other resources.

Features:
- Automatic update checking
- Secure downloading and verification of updates
- Recovery mechanisms for failed updates
- Incremental updates for bandwidth optimization
"""

import os
import sys
import json
import time
import hashlib
import logging
import requests
import tempfile
import shutil
import threading
import subprocess
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta

# Configure logger
logger = logging.getLogger(__name__)

# Update server URL
UPDATE_SERVER = "https://romsorter.example.com/updates"

# Update configuration file
UPDATE_CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'update.json')

# Version of the program
VERSION_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'version.txt')

# Current version
__version__ = '2.1.8'

# Path for temporary update files
TEMP_UPDATE_DIR = os.path.join(tempfile.gettempdir(), "romsorter_updates")


class UpdateError(Exception):
    """Base class for update errors."""
    pass


class UpdateManager:
    """
    Manages the update process for ROM Sorter Pro.
    """

    def __init__(self, auto_check: bool = True, check_interval: int = 24):
        """
        Initializes the update manager.

        Args:
            auto_check: Enable automatic update checking
            check_interval: Check interval in hours
        """
        self.auto_check = auto_check
        self.check_interval = check_interval
        self.current_version = self._get_current_version()
        self.update_config = self._load_update_config()
        self.update_thread = None
        self.is_checking = False
        self.last_check_time = None
        self.update_available = False
        self.available_version = None
        self.update_info = None
        self.update_progress_callback = None

        # Make sure the temporary update directory exists
        os.makedirs(TEMP_UPDATE_DIR, exist_ok=True)

        # Start automatic testing if activated
        if self.auto_check:
            self._start_auto_check()

    def _get_current_version(self) -> str:
        """
        Determines the current version of the program.

        Returns:
            Aktuelle Version als String
        """
        try:
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, 'r') as f:
                    version = f.read().strip()
                return version
            else:
                # Standardversion, falls keine Versionsdatei gefunden wurde
                return "0.0.1"
        except Exception as e:
            logger.error(f"Fehler beim Lesen der Versionsdatei: {e}")
            return "0.0.1"

    def _load_update_config(self) -> Dict[str, Any]:
        """Loads the Update Configuration from the File. Return: Update Configuration as a dictionary"""
        default_config = {
            "auto_check": self.auto_check,
            "check_interval": self.check_interval,
            "last_check": None,
            "update_channel": "stable",
            "proxy": None,
            "custom_update_server": None
        }

        try:
            if os.path.exists(UPDATE_CONFIG_FILE):
                with open(UPDATE_CONFIG_FILE, 'r') as f:
                    config = json.load(f)

                # Complete missing entries with standard values
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value

                return config
            else:
                # Create the configuration file with standard values
                os.makedirs(os.path.dirname(UPDATE_CONFIG_FILE), exist_ok=True)
                with open(UPDATE_CONFIG_FILE, 'w') as f:
                    json.dump(default_config, f, indent=2)

                return default_config
        except Exception as e:
            logger.error(f"Fehler beim Laden der Update-Konfiguration: {e}")
            return default_config

    def _save_update_config(self) -> bool:
        """Save the update configuration in the file. Return: True in the event of success, false in the event of errors"""
        try:
            os.makedirs(os.path.dirname(UPDATE_CONFIG_FILE), exist_ok=True)
            with open(UPDATE_CONFIG_FILE, 'w') as f:
                json.dump(self.update_config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Update-Konfiguration: {e}")
            return False

    def _start_auto_check(self) -> None:
        """Starts the automatic update check."""
        def check_thread():
            while self.auto_check:
                # Check whether an update test is required
                if self.update_config["last_check"] is None:
                    perform_check = True
                else:
                    last_check = datetime.fromisoformat(self.update_config["last_check"])
                    time_since_last_check = datetime.now() - last_check
                    perform_check = time_since_last_check > timedelta(hours=self.check_interval)

                if perform_check and not self.is_checking:
                    self.check_for_updates()

                # Wait for an hour before checking again
                time.sleep(3600)

        self.update_thread = threading.Thread(target=check_thread)
        self.update_thread.daemon = True
        self.update_thread.start()

    def set_progress_callback(self, callback: Callable[[int, str], None]) -> None:
        """Set A Callback for Update Progress. ARGS: Callback: Function that is called When Progress Signature: Callback (Progress, Message)"""
        self.update_progress_callback = callback

    def _report_progress(self, progress: int, message: str) -> None:
        """
        Meldet den Update-Fortschritt.

        Args:
            progress: Fortschritt in Prozent (0-100)
            message: Fortschrittsmeldung
        """
        logger.debug(f"Update-Fortschritt {progress}%: {message}")

        if self.update_progress_callback:
            self.update_progress_callback(progress, message)

    def check_for_updates(self) -> bool:
        """Check whether updates are available. Return: True when updates are available, otherwise false"""
        if self.is_checking:
            logger.warning("Update-Prüfung läuft bereits")
            return False

        self.is_checking = True
        self._report_progress(0, "Prüfe auf Updates...")

        try:
            # Determine the update server url to be used
            server_url = self.update_config.get("custom_update_server") or UPDATE_SERVER
            update_channel = self.update_config.get("update_channel", "stable")

            # Create the URL for the update examination
            url = f"{server_url}/check?version={self.current_version}&channel={update_channel}"

            # Konfiguriere den Proxy, falls vorhanden
            proxies = None
            if self.update_config.get("proxy"):
                proxies = {"http": self.update_config["proxy"], "https": self.update_config["proxy"]}

            # Perform the request
            self._report_progress(20, "Verbindung zum Update-Server wird hergestellt...")
            response = requests.get(url, proxies=proxies, timeout=30)

            if response.status_code == 200:
                data = response.json()
                self.update_available = data.get("update_available", False)

                if self.update_available:
                    self.available_version = data.get("version")
                    self.update_info = data
                    logger.info(f"Update verfügbar: Version {self.available_version}")
                    self._report_progress(100, f"Update auf Version {self.available_version} verfügbar!")
                else:
                    logger.info("Keine Updates verfügbar")
                    self._report_progress(100, "Die Software ist auf dem neuesten Stand")

                # Update the time of the last examination
                self.last_check_time = datetime.now()
                self.update_config["last_check"] = self.last_check_time.isoformat()
                self._save_update_config()

                self.is_checking = False
                return self.update_available
            else:
                logger.error(f"Fehler bei der Update-Prüfung: HTTP {response.status_code}")
                self._report_progress(100, f"Fehler bei der Update-Prüfung: HTTP {response.status_code}")
                self.is_checking = False
                return False

        except Exception as e:
            logger.error(f"Fehler bei der Update-Prüfung: {e}")
            self._report_progress(100, f"Fehler bei der Update-Prüfung: {e}")
            self.is_checking = False
            return False

    def download_update(self) -> Optional[str]:
        """
        Downloads the update.

        Returns:
            Path to the downloaded update file or None if error
        """
        if not self.update_available or not self.update_info:
            logger.warning("Kein Update verfügbar")
            return None

        self._report_progress(0, "Update wird vorbereitet...")

        try:
            # Determine the update server url to be used
            server_url = self.update_config.get("custom_update_server") or UPDATE_SERVER

            # URL for the download
            download_url = self.update_info.get("download_url")
            if not download_url:
                download_url = f"{server_url}/download?version={self.available_version}"

            # Check Whether there is a direct download link
            if not download_url.startswith("http"):
                download_url = f"{server_url}/{download_url}"

            # Konfiguriere den Proxy, falls vorhanden
            proxies = None
            if self.update_config.get("proxy"):
                proxies = {"http": self.update_config["proxy"], "https": self.update_config["proxy"]}

            # File path for the downloaded update
            update_filename = f"romsorter_update_{self.available_version}.zip"
            update_filepath = os.path.join(TEMP_UPDATE_DIR, update_filename)

            # Delete previous update files
            if os.path.exists(update_filepath):
                os.remove(update_filepath)

            # Download the update
            self._report_progress(10, "Update wird heruntergeladen...")

            with requests.get(download_url, proxies=proxies, stream=True, timeout=300) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0

                with open(update_filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Calculate and report the progress
                            if total_size > 0:
                                progress = int(10 + (downloaded / total_size) * 70)
                                self._report_progress(
                                    progress,
                                    f"Update wird heruntergeladen... {downloaded / 1024 / 1024:.1f} MB / {total_size / 1024 / 1024:.1f} MB"
                                )

            # Check the integrity of the downloaded update
            if "checksum" in self.update_info:
                self._report_progress(80, "Überprüfe Update-Integrität...")

                checksum_type = self.update_info.get("checksum_type", "sha256")
                expected_checksum = self.update_info["checksum"]

                if not self._verify_checksum(update_filepath, expected_checksum, checksum_type):
                    logger.error("Checksum-Prüfung fehlgeschlagen")
                    self._report_progress(100, "Fehler: Update-Datei ist beschädigt")
                    return None

            self._report_progress(90, "Update erfolgreich heruntergeladen")
            return update_filepath

        except Exception as e:
            logger.error(f"Fehler beim Herunterladen des Updates: {e}")
            self._report_progress(100, f"Fehler beim Herunterladen des Updates: {e}")
            return None

    def _verify_checksum(self, file_path: str, expected_checksum: str,
                        checksum_type: str = "sha256") -> bool:
        """Verifies the Integrity of A File Using Checksum. ARGS: File_Path: Path to the File to Verify Expected_Checksum: Expected Checksum Checksum_Type: Type of Checksum (MD5, SHA1, SHA256, SHA512) Return: True, if the Checks Matches, OtherWise False"""
        try:
            if checksum_type == "md5":
                hasher = hashlib.md5()
            elif checksum_type == "sha1":
                hasher = hashlib.sha1()
            elif checksum_type == "sha256":
                hasher = hashlib.sha256()
            elif checksum_type == "sha512":
                hasher = hashlib.sha512()
            else:
                logger.warning(f"Unbekannter Checksum-Typ: {checksum_type}, verwende sha256")
                hasher = hashlib.sha256()

            with open(file_path, 'rb') as f:
                # Read the file in chunks to limit memory consumption
                chunk_size = 4096
                for chunk in iter(lambda: f.read(chunk_size), b''):
                    hasher.update(chunk)

            calculated_checksum = hasher.hexdigest()

            logger.debug(f"Erwartete Checksum: {expected_checksum}")
            logger.debug(f"Berechnete Checksum: {calculated_checksum}")

            return calculated_checksum.lower() == expected_checksum.lower()

        except Exception as e:
            logger.error(f"Fehler bei der Checksum-Prüfung: {e}")
            return False

    def install_update(self, update_file_path: str) -> bool:
        """Install a downloaded update. ARGS: Update_file_Path: Path to the Update File Return: True in the event of Success, False in the event of errors"""
        if not os.path.exists(update_file_path):
            logger.error(f"Update-Datei nicht gefunden: {update_file_path}")
            return False

        try:
            from ..security.security_utils import validate_file_operation
            validate_file_operation(update_file_path, base_dir=None, allow_read=True, allow_write=False)
        except Exception as e:
            logger.error(f"Unsicherer Update-Pfad: {e}")
            return False

        self._report_progress(0, "Update wird installiert...")

        # Create A Temporary Directory for the Unpacked Update Files
        extract_dir = os.path.join(TEMP_UPDATE_DIR, f"extract_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        os.makedirs(extract_dir, exist_ok=True)
        try:
            from ..security.security_utils import validate_file_operation
            validate_file_operation(extract_dir, base_dir=TEMP_UPDATE_DIR, allow_read=True, allow_write=True)
        except Exception as e:
            logger.error(f"Unsicheres Extract-Verzeichnis: {e}")
            return False

        try:
            # Pfad zum Programmverzeichnis
            program_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

            # Unpack the update
            self._report_progress(10, "Update wird entpackt...")

            from ..security.security_utils import safe_extract_zip
            safe_extract_zip(update_file_path, extract_dir)

            # Check Whether there is a pre-update script and lead it out
            pre_update_script = os.path.join(extract_dir, "pre_update.py")
            if os.path.exists(pre_update_script):
                self._report_progress(20, "Führe Vor-Update-Skript aus...")
                self._run_python_script(pre_update_script)

            # Create A Backup of the Current Installation
            backup_dir = os.path.join(TEMP_UPDATE_DIR, f"backup_{datetime.now().strftime('%Y%m%d%H%M%S')}")
            self._report_progress(30, "Erstelle Backup...")
            self._create_backup(program_dir, backup_dir)

            # Copy the update files into the program directory
            self._report_progress(50, "Installiere Update-Dateien...")
            self._copy_update_files(extract_dir, program_dir)

            # Update the version file
            if self.available_version:
                with open(VERSION_FILE, 'w') as f:
                    f.write(self.available_version)

            # Check Whether there is a post-update script and Carry it out
            post_update_script = os.path.join(extract_dir, "post_update.py")
            if os.path.exists(post_update_script):
                self._report_progress(80, "Führe Nach-Update-Skript aus...")
                self._run_python_script(post_update_script)

            # Cleaning temporary files
            self._report_progress(90, "Bereinige temporäre Dateien...")
            shutil.rmtree(extract_dir, ignore_errors=True)

            # Aktualisiere den Update-Status
            self.current_version = self.available_version
            self.update_available = False
            self.available_version = None
            self.update_info = None

            self._report_progress(100, f"Update auf Version {self.current_version} erfolgreich installiert!")
            return True

        except Exception as e:
            logger.error(f"Fehler bei der Update-Installation: {e}")
            self._report_progress(100, f"Fehler bei der Update-Installation: {e}")

            # Try to restore the backup
            try:
                if os.path.exists(backup_dir):
                    self._report_progress(0, "Update fehlgeschlagen - stelle Backup wieder her...")
                    self._restore_backup(backup_dir, program_dir)
                    self._report_progress(100, "Backup erfolgreich wiederhergestellt")
            except Exception as restore_error:
                logger.error(f"Fehler bei der Wiederherstellung des Backups: {restore_error}")

            return False

    def _run_python_script(self, script_path: str) -> None:
        """Leads a python script. Args: script_path: path to the python script"""
        subprocess.run([sys.executable, script_path], check=True)

    def _create_backup(self, source_dir: str, backup_dir: str) -> None:
        """Creates A Backup of the Program Directory. Args: Source_dir: Source Directory Backup_Dir: Target Directory for the Backup"""
        # Create the backup directory if it does not exist
        os.makedirs(backup_dir, exist_ok=True)

        # Copy all files and subdirectories
        for item in os.listdir(source_dir):
            source_item = os.path.join(source_dir, item)
            backup_item = os.path.join(backup_dir, item)

            # Ignore certain directories and files
            if item in ['.git', '__pycache__', 'logs', 'temp'] or item.endswith('.pyc'):
                continue

            if os.path.isdir(source_item):
                shutil.copytree(source_item, backup_item, symlinks=True)
            else:
                shutil.copy2(source_item, backup_item)

    def _restore_backup(self, backup_dir: str, target_dir: str) -> None:
        """Restore a backup. Args: backup_dir: backup Directory Target_dir: Table Directory for restoration"""
        # Copy all files and subdirectories back
        for item in os.listdir(backup_dir):
            backup_item = os.path.join(backup_dir, item)
            target_item = os.path.join(target_dir, item)

            if os.path.isdir(backup_item):
                # If the target directory exists, delete it first
                if os.path.exists(target_item):
                    shutil.rmtree(target_item)
                shutil.copytree(backup_item, target_item, symlinks=True)
            else:
                # If the target file exists, you will delete it first
                if os.path.exists(target_item):
                    os.remove(target_item)
                shutil.copy2(backup_item, target_item)

    def _copy_update_files(self, update_dir: str, target_dir: str) -> None:
        """Copies the update files into the target directory. Args: UPDATE_DIR: List with the update files TARGET_DIR: target directory for installation"""
        # Check whether an update.json file exists
        update_json_path = os.path.join(update_dir, "update.json")
        if os.path.exists(update_json_path):
            # Read the update instructions
            with open(update_json_path, 'r') as f:
                update_instructions = json.load(f)

            # Process the instructions
            if "files" in update_instructions:
                for file_info in update_instructions["files"]:
                    source_path = os.path.join(update_dir, file_info["source"])
                    target_path = os.path.join(target_dir, file_info["target"])

                    # Make sure the target directory exists
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)

                    # Copy the file
                    shutil.copy2(source_path, target_path)

            # Processed files to be deleted
            if "delete" in update_instructions:
                for delete_path in update_instructions["delete"]:
                    full_path = os.path.join(target_dir, delete_path)
                    if os.path.exists(full_path):
                        if os.path.isdir(full_path):
                            shutil.rmtree(full_path)
                        else:
                            os.remove(full_path)
        else:
            # Keine Anweisungen gefunden, kopiere alle Dateien
            for root, dirs, files in os.walk(update_dir):
                # Berechne den relativen Pfad
                rel_path = os.path.relpath(root, update_dir)

                # Create the target directories
                if rel_path != ".":
                    target_subdir = os.path.join(target_dir, rel_path)
                    os.makedirs(target_subdir, exist_ok=True)

                # Kopiere alle Dateien
                for file in files:
                    # Ignoriere bestimmte Dateien
                    if file in ["pre_update.py", "post_update.py"]:
                        continue

                    source_file = os.path.join(root, file)
                    if rel_path == ".":
                        target_file = os.path.join(target_dir, file)
                    else:
                        target_file = os.path.join(target_dir, rel_path, file)

                    shutil.copy2(source_file, target_file)


def check_and_update() -> None:
    """Check for updates and lead them."""
    # Konfiguriere Logging
    logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    try:
        print("Prüfe auf Updates...")

        # Erstelle Update-Manager
        update_manager = UpdateManager(auto_check=False)

        # Definiere Fortschritts-Callback
        def progress_callback(progress, message):
            print(f"[{progress}%] {message}")

        update_manager.set_progress_callback(progress_callback)

        # Check on updates
        if update_manager.check_for_updates():
            print(f"Update auf Version {update_manager.available_version} verfügbar.")

            choice = input("Möchten Sie das Update herunterladen und installieren? (j/n): ")
            if choice.lower() in ['j', 'ja', 'y', 'yes']:
                # Download the update
                update_file = update_manager.download_update()

                if update_file:
                    print(f"Update heruntergeladen: {update_file}")

                    # Install the update
                    if update_manager.install_update(update_file):
                        print("Update erfolgreich installiert.")
                        print("Bitte starten Sie das Programm neu, um die Änderungen zu übernehmen.")
                    else:
                        print("Fehler bei der Installation des Updates.")
                else:
                    print("Fehler beim Herunterladen des Updates.")
            else:
                print("Update abgebrochen.")
        else:
            print("Keine Updates verfügbar.")

    except Exception as e:
        print(f"Fehler bei der Update-Prüfung: {e}")


# Example of using the update manager
if __name__ == "__main__":
    check_and_update()
