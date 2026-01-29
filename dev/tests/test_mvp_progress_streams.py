from __future__ import annotations

import os

import pytest

from src.app.progress_streams import RX_AVAILABLE, progress_observable


pytestmark = pytest.mark.integration


def test_progress_observable_smoke() -> None:
    if os.environ.get("ROM_SORTER_RX_TEST") != "1":
        pytest.skip("Set ROM_SORTER_RX_TEST=1 to enable Rx progress test.")
    if not RX_AVAILABLE:
        pytest.skip("RxPY not available.")

    subject, cb = progress_observable()
    events: list[tuple[int, int]] = []
    sub = subject.subscribe(lambda value: events.append(value))
    cb(1, 10)
    cb(2, 10)
    subject.on_completed()
    sub.dispose()

    assert events == [(1, 10), (2, 10)]
