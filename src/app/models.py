"""Shared type aliases and dataclasses for app controllers."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

SortMode = Literal["copy", "move"]
ConflictPolicy = Literal["skip", "overwrite", "rename"]
ConversionMode = Literal["all", "skip", "only"]

ProgressCallback = Callable[[int, int], None]
LogCallback = Callable[[str], None]
ActionStatusCallback = Callable[[int, str], None]


class CancelToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    @property
    def event(self) -> threading.Event:
        return self._event

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


@dataclass(frozen=True)
class ScanItem:
    input_path: str
    detected_system: str
    detection_source: Optional[str] = None
    detection_confidence: Optional[float] = None
    is_exact: bool = False
    languages: Tuple[str, ...] = ()
    version: Optional[str] = None
    region: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class IdentificationResult:
    platform_id: str
    confidence: float
    is_exact: bool
    signals: List[str]
    candidates: List[str]
    reason: str
    input_kind: str
    normalized_artifact: Optional[str] = None


@dataclass(frozen=True)
class ScanResult:
    source_path: str
    items: List[ScanItem]
    stats: Dict[str, Any]
    cancelled: bool = False


@dataclass(frozen=True)
class SortAction:
    input_path: str
    detected_system: str
    planned_target_path: Optional[str]
    action: str
    status: str
    error: Optional[str] = None
    conversion_tool: Optional[str] = None
    conversion_tool_key: Optional[str] = None
    conversion_args: Optional[List[str]] = None
    conversion_rule: Optional[str] = None
    conversion_output_extension: Optional[str] = None
    source_size: Optional[int] = None
    source_mtime: Optional[float] = None
    source_sha1: Optional[str] = None


@dataclass(frozen=True)
class SortPlan:
    dest_path: str
    mode: SortMode
    on_conflict: ConflictPolicy
    actions: List[SortAction]


@dataclass(frozen=True)
class SortResumeState:
    sort_plan: SortPlan
    resume_from_index: int


@dataclass(frozen=True)
class SortReport:
    dest_path: str
    mode: SortMode
    on_conflict: ConflictPolicy
    processed: int
    copied: int
    moved: int
    overwritten: int
    renamed: int
    skipped: int
    errors: List[str]
    cancelled: bool


@dataclass(frozen=True)
class ExternalToolsReport:
    processed: int
    succeeded: int
    failed: int
    errors: List[str]
    cancelled: bool


@dataclass(frozen=True)
class ConversionAuditItem:
    input_path: str
    detected_system: str
    current_extension: str
    recommended_extension: Optional[str]
    rule_name: Optional[str]
    tool_key: Optional[str]
    status: str
    reason: Optional[str] = None


@dataclass(frozen=True)
class ConversionAuditReport:
    source_path: str
    items: List[ConversionAuditItem]
    totals: Dict[str, int]
    cancelled: bool = False
