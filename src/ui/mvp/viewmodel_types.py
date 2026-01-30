from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class ResultsRowDTO:
    input_path: str
    detected_system: str
    planned_target_path: Optional[str]
    action: str
    status: str
    error: Optional[str]


@dataclass(frozen=True)
class DetailsDTO:
    input_path: str
    target_path: Optional[str]
    status: str
    system: str
    reason: Optional[str]


@dataclass
class ViewModelEvents:
    log: Optional[Callable[[str], None]] = None
    progress: Optional[Callable[[int, int], None]] = None
    phase_changed: Optional[Callable[[str, int], None]] = None
    action_status: Optional[Callable[[int, str], None]] = None
    error: Optional[Callable[[str], None]] = None
