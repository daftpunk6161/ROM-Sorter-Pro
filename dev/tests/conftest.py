from __future__ import annotations

from pathlib import Path


def pytest_configure() -> None:
    """Ensure pytest base temp directory exists for CI runs."""

    repo_root = Path(__file__).resolve().parents[2]
    base_temp = repo_root / "temp" / "pytest"
    base_temp.mkdir(parents=True, exist_ok=True)