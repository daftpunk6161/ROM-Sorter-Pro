"""Queue helpers for UI job scheduling."""

from __future__ import annotations

from typing import Any, Iterable, List


def _job_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return int(default)
        try:
            return int(float(text))
        except Exception:
            return int(default)
    return int(default)


def sort_job_queue(jobs: List[dict[str, Any]]) -> List[dict[str, Any]]:
    """Sort jobs in-place by priority then id (stable)."""
    jobs.sort(
        key=lambda item: (
            _job_int(item.get("priority", 1), 1),
            _job_int(item.get("id", 0), 0),
        )
    )
    return jobs