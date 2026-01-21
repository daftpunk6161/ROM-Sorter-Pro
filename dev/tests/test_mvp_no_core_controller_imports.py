"""Prevent new imports from src.core.controller (deprecated shim)."""

from __future__ import annotations

from pathlib import Path


def test_no_core_controller_imports() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src_root = repo_root / "src"

    offenders = []
    for path in src_root.rglob("*.py"):
        if path.name == "controller.py" and path.parent.name == "core":
            continue
        text = path.read_text(encoding="utf-8")
        if "core.controller" in text or "from src.core.controller" in text:
            offenders.append(path)

    assert offenders == []
