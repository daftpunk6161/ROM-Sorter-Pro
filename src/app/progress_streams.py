"""Optional progress observables (RxPY)."""

from __future__ import annotations

from typing import Any, Callable, Tuple
import importlib

SubjectType = Any

try:
    _rx_subject = importlib.import_module("rx.subject")
    _subject_factory = getattr(_rx_subject, "Subject", None)
    RX_AVAILABLE = _subject_factory is not None
except Exception:  # pragma: no cover
    _subject_factory = None
    RX_AVAILABLE = False


def progress_observable() -> Tuple[SubjectType, Callable[[int, int], None]]:
    if not RX_AVAILABLE or _subject_factory is None:
        raise RuntimeError("RxPY not available")
    subject: SubjectType = _subject_factory()

    def progress_cb(current: int, total: int) -> None:
        subject.on_next((int(current), int(total)))

    return subject, progress_cb
