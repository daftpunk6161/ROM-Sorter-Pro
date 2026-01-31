"""Detection Confidence Tuner - F62 Implementation.

Provides global confidence threshold configuration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class ConfidenceLevel(Enum):
    """Predefined confidence levels."""

    STRICT = auto()  # 95%+ only
    HIGH = auto()  # 85%+
    BALANCED = auto()  # 70%+ (default)
    PERMISSIVE = auto()  # 50%+
    ACCEPT_ALL = auto()  # Any match


@dataclass
class ConfidenceThresholds:
    """Confidence thresholds configuration."""

    # Global minimum threshold (0.0 - 1.0)
    global_minimum: float = 0.70

    # Per-action thresholds
    auto_sort_minimum: float = 0.85  # For automatic sorting
    suggestion_minimum: float = 0.50  # For showing suggestions
    warning_threshold: float = 0.70  # Below this shows warning

    # Per-system overrides
    system_overrides: Dict[str, float] = field(default_factory=dict)

    # Per-detector overrides
    detector_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class ConfidencePreset:
    """A confidence preset configuration."""

    name: str
    level: ConfidenceLevel
    thresholds: ConfidenceThresholds
    description: str = ""


# Built-in presets
PRESETS: Dict[ConfidenceLevel, ConfidencePreset] = {
    ConfidenceLevel.STRICT: ConfidencePreset(
        name="Strict",
        level=ConfidenceLevel.STRICT,
        description="Only high-confidence matches (95%+). Minimizes false positives.",
        thresholds=ConfidenceThresholds(
            global_minimum=0.95,
            auto_sort_minimum=0.98,
            suggestion_minimum=0.80,
            warning_threshold=0.95,
        ),
    ),
    ConfidenceLevel.HIGH: ConfidencePreset(
        name="High",
        level=ConfidenceLevel.HIGH,
        description="High-confidence matches (85%+). Good balance for curated collections.",
        thresholds=ConfidenceThresholds(
            global_minimum=0.85,
            auto_sort_minimum=0.90,
            suggestion_minimum=0.60,
            warning_threshold=0.85,
        ),
    ),
    ConfidenceLevel.BALANCED: ConfidencePreset(
        name="Balanced",
        level=ConfidenceLevel.BALANCED,
        description="Balanced detection (70%+). Default for most users.",
        thresholds=ConfidenceThresholds(
            global_minimum=0.70,
            auto_sort_minimum=0.85,
            suggestion_minimum=0.50,
            warning_threshold=0.70,
        ),
    ),
    ConfidenceLevel.PERMISSIVE: ConfidencePreset(
        name="Permissive",
        level=ConfidenceLevel.PERMISSIVE,
        description="Permissive detection (50%+). More matches, more manual review.",
        thresholds=ConfidenceThresholds(
            global_minimum=0.50,
            auto_sort_minimum=0.70,
            suggestion_minimum=0.30,
            warning_threshold=0.50,
        ),
    ),
    ConfidenceLevel.ACCEPT_ALL: ConfidencePreset(
        name="Accept All",
        level=ConfidenceLevel.ACCEPT_ALL,
        description="Accept any match. Maximum recall, requires manual verification.",
        thresholds=ConfidenceThresholds(
            global_minimum=0.01,
            auto_sort_minimum=0.30,
            suggestion_minimum=0.01,
            warning_threshold=0.30,
        ),
    ),
}


class ConfidenceTuner:
    """Confidence threshold tuner.

    Implements F62: Detection-Confidence-Tuner

    Features:
    - Global confidence slider
    - Per-system thresholds
    - Per-detector weights
    - Preset configurations
    """

    CONFIG_FILENAME = "confidence_config.json"

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize confidence tuner.

        Args:
            config_dir: Configuration directory
        """
        self._config_dir = Path(config_dir) if config_dir else Path("config")
        self._thresholds = ConfidenceThresholds()
        self._current_level = ConfidenceLevel.BALANCED
        self._callbacks: List[Callable[[ConfidenceThresholds], None]] = []

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        config_file = self._config_dir / self.CONFIG_FILENAME

        if not config_file.exists():
            return

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._thresholds = ConfidenceThresholds(
                global_minimum=data.get("global_minimum", 0.70),
                auto_sort_minimum=data.get("auto_sort_minimum", 0.85),
                suggestion_minimum=data.get("suggestion_minimum", 0.50),
                warning_threshold=data.get("warning_threshold", 0.70),
                system_overrides=data.get("system_overrides", {}),
                detector_weights=data.get("detector_weights", {}),
            )

            level_name = data.get("level", "BALANCED")
            try:
                self._current_level = ConfidenceLevel[level_name]
            except KeyError:
                self._current_level = ConfidenceLevel.BALANCED

        except Exception:
            pass

    def _save_config(self) -> None:
        """Save configuration to file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        config_file = self._config_dir / self.CONFIG_FILENAME

        data = {
            "level": self._current_level.name,
            "global_minimum": self._thresholds.global_minimum,
            "auto_sort_minimum": self._thresholds.auto_sort_minimum,
            "suggestion_minimum": self._thresholds.suggestion_minimum,
            "warning_threshold": self._thresholds.warning_threshold,
            "system_overrides": self._thresholds.system_overrides,
            "detector_weights": self._thresholds.detector_weights,
        }

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _notify_callbacks(self) -> None:
        """Notify registered callbacks of threshold changes."""
        for callback in self._callbacks:
            try:
                callback(self._thresholds)
            except Exception:
                pass

    @property
    def thresholds(self) -> ConfidenceThresholds:
        """Get current thresholds."""
        return self._thresholds

    @property
    def current_level(self) -> ConfidenceLevel:
        """Get current confidence level."""
        return self._current_level

    @property
    def global_minimum(self) -> float:
        """Get global minimum threshold."""
        return self._thresholds.global_minimum

    @global_minimum.setter
    def global_minimum(self, value: float) -> None:
        """Set global minimum threshold."""
        self._thresholds.global_minimum = max(0.0, min(1.0, value))
        self._current_level = ConfidenceLevel.BALANCED  # Custom
        self._save_config()
        self._notify_callbacks()

    def set_preset(self, level: ConfidenceLevel) -> None:
        """Apply a preset configuration.

        Args:
            level: Confidence level preset
        """
        if level not in PRESETS:
            return

        preset = PRESETS[level]
        self._thresholds = ConfidenceThresholds(
            global_minimum=preset.thresholds.global_minimum,
            auto_sort_minimum=preset.thresholds.auto_sort_minimum,
            suggestion_minimum=preset.thresholds.suggestion_minimum,
            warning_threshold=preset.thresholds.warning_threshold,
            system_overrides=dict(self._thresholds.system_overrides),
            detector_weights=dict(self._thresholds.detector_weights),
        )
        self._current_level = level
        self._save_config()
        self._notify_callbacks()

    def set_system_threshold(self, system: str, threshold: float) -> None:
        """Set per-system threshold override.

        Args:
            system: System name
            threshold: Threshold value (0.0 - 1.0)
        """
        self._thresholds.system_overrides[system] = max(0.0, min(1.0, threshold))
        self._save_config()
        self._notify_callbacks()

    def remove_system_threshold(self, system: str) -> None:
        """Remove per-system threshold override.

        Args:
            system: System name
        """
        self._thresholds.system_overrides.pop(system, None)
        self._save_config()
        self._notify_callbacks()

    def set_detector_weight(self, detector: str, weight: float) -> None:
        """Set detector weight.

        Args:
            detector: Detector name
            weight: Weight multiplier (0.0 - 2.0)
        """
        self._thresholds.detector_weights[detector] = max(0.0, min(2.0, weight))
        self._save_config()
        self._notify_callbacks()

    def get_threshold_for_system(self, system: str) -> float:
        """Get effective threshold for a system.

        Args:
            system: System name

        Returns:
            Threshold value
        """
        return self._thresholds.system_overrides.get(
            system, self._thresholds.global_minimum
        )

    def should_auto_sort(self, confidence: float, system: Optional[str] = None) -> bool:
        """Check if confidence is high enough for auto-sort.

        Args:
            confidence: Detection confidence
            system: Optional system name

        Returns:
            True if should auto-sort
        """
        threshold = self._thresholds.auto_sort_minimum
        if system and system in self._thresholds.system_overrides:
            threshold = max(threshold, self._thresholds.system_overrides[system])

        return confidence >= threshold

    def should_show_suggestion(
        self, confidence: float, system: Optional[str] = None
    ) -> bool:
        """Check if confidence is high enough to show suggestion.

        Args:
            confidence: Detection confidence
            system: Optional system name

        Returns:
            True if should show
        """
        threshold = self._thresholds.suggestion_minimum
        if system and system in self._thresholds.system_overrides:
            threshold = min(threshold, self._thresholds.system_overrides[system])

        return confidence >= threshold

    def should_warn(self, confidence: float) -> bool:
        """Check if confidence warrants a warning.

        Args:
            confidence: Detection confidence

        Returns:
            True if should warn
        """
        return confidence < self._thresholds.warning_threshold

    def apply_detector_weights(
        self, scores: Dict[str, float]
    ) -> Dict[str, float]:
        """Apply detector weights to scores.

        Args:
            scores: Detector scores

        Returns:
            Weighted scores
        """
        weighted = {}
        for detector, score in scores.items():
            weight = self._thresholds.detector_weights.get(detector, 1.0)
            weighted[detector] = score * weight

        return weighted

    def register_callback(
        self, callback: Callable[[ConfidenceThresholds], None]
    ) -> None:
        """Register callback for threshold changes.

        Args:
            callback: Callback function
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(
        self, callback: Callable[[ConfidenceThresholds], None]
    ) -> None:
        """Unregister callback.

        Args:
            callback: Callback function
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def get_presets(self) -> List[Dict[str, Any]]:
        """Get available presets.

        Returns:
            List of preset info
        """
        return [
            {
                "level": preset.level.name,
                "name": preset.name,
                "description": preset.description,
                "global_minimum": preset.thresholds.global_minimum,
                "is_current": preset.level == self._current_level,
            }
            for preset in PRESETS.values()
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get current configuration status.

        Returns:
            Status dict
        """
        return {
            "level": self._current_level.name,
            "global_minimum": self._thresholds.global_minimum,
            "auto_sort_minimum": self._thresholds.auto_sort_minimum,
            "suggestion_minimum": self._thresholds.suggestion_minimum,
            "warning_threshold": self._thresholds.warning_threshold,
            "system_overrides_count": len(self._thresholds.system_overrides),
            "detector_weights_count": len(self._thresholds.detector_weights),
        }

    def reset_to_defaults(self) -> None:
        """Reset to default configuration."""
        self.set_preset(ConfidenceLevel.BALANCED)
        self._thresholds.system_overrides.clear()
        self._thresholds.detector_weights.clear()
        self._save_config()
        self._notify_callbacks()
