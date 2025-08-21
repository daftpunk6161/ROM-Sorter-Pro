#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""Rome Sorter Pro - Basic Detector This Module Definition The Basic Class for All Detectors, To A Uniform Interface and Common Functionality to Ensure for All Detectors."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class BaseDetector(ABC):
    """Basic Class for All Detectors in the Rome Sorter via application. Defense A Common Interface and Basic Functions."""

    def __init__(self, confidence_threshold: float = 0.5):
        """Initialized the detector. Args: Confidence_threshold: Minimal confidence threshold for positive detection"""
        self.confidence_threshold = confidence_threshold
        self.last_result = None
        self.last_confidence = 0.0

    @abstractmethod
    def detect(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Recognize the Console Type for A File. ARGS: File_Path: Path to the File to Be Examined Return: Dict with Console Information or None If No Detection is possible"""
        pass

    def is_supported_file(self, file_path: Path) -> bool:
        """Check whether the file is supported by this detector. Args: File_Path: path to the file to be examined Return: True if the file is supported, otherwise false"""
        return False

    def get_last_result(self) -> Optional[Dict[str, Any]]:
        """Gives back the last detection result. Return: Dict with console information or none if there is no detection"""
        return self.last_result

    def get_confidence(self) -> float:
        """Gives back the confidence value of the last detection. Return: Confidence between 0.0 and 1.0"""
        return self.last_confidence
