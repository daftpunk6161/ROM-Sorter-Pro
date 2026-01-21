from __future__ import annotations

import pytest


@pytest.mark.integration
def test_scanning_exports_only_primary_scanner() -> None:
    import src.scanning as scanning

    assert hasattr(scanning, "HighPerformanceScanner")
    assert getattr(scanning, "__all__") == ["HighPerformanceScanner"]
