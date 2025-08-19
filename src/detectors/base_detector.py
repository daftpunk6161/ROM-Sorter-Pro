#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Basis-Detektor

Dieses Modul definiert die Basisklasse für alle Detektoren,
um eine einheitliche Schnittstelle und gemeinsame Funktionalität
für alle Detektoren sicherzustellen.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class BaseDetector(ABC):
    """
    Basisklasse für alle Detektoren in der ROM Sorter Pro Anwendung.
    Definiert eine gemeinsame Schnittstelle und Basisfunktionen.
    """

    def __init__(self, confidence_threshold: float = 0.5):
        """
        Initialisiert den Detektor.

        Args:
            confidence_threshold: Minimaler Konfidenzschwellenwert für eine positive Erkennung
        """
        self.confidence_threshold = confidence_threshold
        self.last_result = None
        self.last_confidence = 0.0

    @abstractmethod
    def detect(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Erkennt den Konsolentyp für eine Datei.

        Args:
            file_path: Pfad zur zu untersuchenden Datei

        Returns:
            Dict mit Konsoleninformationen oder None, wenn keine Erkennung möglich ist
        """
        pass

    def is_supported_file(self, file_path: Path) -> bool:
        """
        Überprüft, ob die Datei von diesem Detektor unterstützt wird.

        Args:
            file_path: Pfad zur zu untersuchenden Datei

        Returns:
            True, wenn die Datei unterstützt wird, sonst False
        """
        return False

    def get_last_result(self) -> Optional[Dict[str, Any]]:
        """
        Gibt das letzte Erkennungsergebnis zurück.

        Returns:
            Dict mit Konsoleninformationen oder None, wenn keine Erkennung vorliegt
        """
        return self.last_result

    def get_confidence(self) -> float:
        """
        Gibt den Konfidenzwert der letzten Erkennung zurück.

        Returns:
            Konfidenzwert zwischen 0.0 und 1.0
        """
        return self.last_confidence
