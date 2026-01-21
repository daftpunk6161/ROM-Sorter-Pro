#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared DetectionResult model for detector outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

MINIMUM_CONFIDENCE_THRESHOLD = 0.65
HIGH_CONFIDENCE_THRESHOLD = 0.85


class DetectionResult:
    """Represents a ROM console detection result with metadata."""

    def __init__(
        self,
        console: str = "Unknown",
        confidence: float = 0.0,
        method: str = "unknown",
        file_path: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        *,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        analysis: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.console = console or "Unknown"
        try:
            conf_val = float(confidence)
        except (TypeError, ValueError):
            conf_val = 0.0
        self.confidence = max(0.0, min(1.0, conf_val))
        self.method = source or method or "unknown"
        self.file_path = str(file_path or "")
        if metadata is None and analysis is not None:
            metadata = analysis
        self.metadata: Dict[str, Any] = metadata or {}

        if filename is None:
            self.filename = Path(self.file_path).name if self.file_path else ""
        else:
            self.filename = filename

    @property
    def source(self) -> str:
        """Alias for method for compatibility."""
        return self.method

    @property
    def analysis(self) -> Dict[str, Any]:
        """Alias for metadata for compatibility."""
        return self.metadata

    @property
    def is_confident(self) -> bool:
        return self.confidence >= HIGH_CONFIDENCE_THRESHOLD

    @property
    def is_highly_confident(self) -> bool:
        return self.is_confident

    @property
    def is_acceptable(self) -> bool:
        return self.confidence >= MINIMUM_CONFIDENCE_THRESHOLD

    @property
    def is_unknown(self) -> bool:
        return self.console == "Unknown" or self.confidence < 0.3

    def to_tuple(self) -> Tuple[str, float]:
        return (self.console, self.confidence)

    @staticmethod
    def from_tuple(result: Tuple[str, float], method: str = "unknown", file_path: str = "") -> "DetectionResult":
        console, confidence = result
        return DetectionResult(console, confidence, method=method, file_path=file_path)

    def __str__(self) -> str:
        confidence_percent = int(self.confidence * 100)
        confidence_str = f"{confidence_percent}%"
        if self.is_confident:
            status = "SICHER"
        elif self.is_acceptable:
            status = "AKZEPTABEL"
        else:
            status = "UNSICHER"
        return f"{self.console} ({confidence_str}, {status})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "console": self.console,
            "confidence": self.confidence,
            "method": self.method,
            "file_path": self.file_path,
            "filename": self.filename,
            "is_confident": self.is_confident,
            "is_acceptable": self.is_acceptable,
            "is_unknown": self.is_unknown,
            **self.metadata,
        }
