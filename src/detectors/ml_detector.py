#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optional ML detector stub.

This module provides no-op ML detection to keep optional dependency imports
from breaking the GUI or type checking.
"""

from __future__ import annotations

from typing import Optional

from .detection_result import DetectionResult


def detect_console_with_ml(file_path: str) -> DetectionResult:
    return DetectionResult(
        "Unknown",
        0.0,
        method="ml",
        file_path=file_path,
        metadata={"error": "ml_unavailable"},
    )


class MLEnhancedConsoleDetector:
    def __init__(self) -> None:
        self.available = False

    def detect(self, file_path: str) -> DetectionResult:
        return detect_console_with_ml(file_path)


def get_ml_detector() -> Optional[MLEnhancedConsoleDetector]:
    return None
