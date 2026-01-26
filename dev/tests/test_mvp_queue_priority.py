from __future__ import annotations

from pathlib import Path
import sys

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_sort_job_queue_orders_by_priority_then_id() -> None:
    from src.ui.queue_utils import sort_job_queue

    jobs = [
        {"id": 3, "priority": 1, "label": "normal-late"},
        {"id": 1, "priority": 2, "label": "low-early"},
        {"id": 2, "priority": 0, "label": "high"},
        {"id": 4, "priority": 1, "label": "normal-latest"},
    ]

    sort_job_queue(jobs)

    assert [job["id"] for job in jobs] == [2, 3, 4, 1]