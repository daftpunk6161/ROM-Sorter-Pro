#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro - Test-Module für die ML-Detection

Dieses Modul stellt eine einfache Schnittstelle zum Testen der ML-basierten
ROM-Erkennung bereit.
"""

import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import sys
import os

# Add the main directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detectors.detection_handler import DetectionManager, DetectionResult
from src.detectors.ml_detector import detect_console_with_ml

# Aliases for downward compatibility
DetectionHandler = DetectionManager

def test_detection_pipeline(rom_path: str) -> Tuple[str, float]:
    """
    Testet die Detection-Pipeline mit einem ROM-Pfad.

    Args:
        rom_path: Pfad zur ROM-Datei

    Returns:
        Tuple aus (Konsolenname, Konfidenz)
    """
    if not os.path.exists(rom_path):
        print(f"Datei nicht gefunden: {rom_path}")
        return "Unknown", 0.0

# Create A Manager Instance
    manager = DetectionManager.get_instance()

# Extract file names
    file_path = Path(rom_path)
    filename = file_path.name

# Create detection
    result = manager.detect_console_with_metadata(filename, str(file_path))

# Alternative: Direct test of ML detection
    ml_result = detect_console_with_ml(rom_path)

    print(f"Standard-Erkennung: {result}")
    print(f"ML-Erkennung: {ml_result}")

    return result.console, result.confidence

if __name__ == "__main__":
# Example of use
    import sys

    if len(sys.argv) > 1:
        rom_path = sys.argv[1]
        console, confidence = test_detection_pipeline(rom_path)
        print(f"Erkannte Konsole: {console} (Konfidenz: {confidence:.2f})")
    else:
        print("Verwendung: python detection_test.py <pfad_zur_rom>")
