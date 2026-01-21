"""Ensure UI uses controller API surface only."""

from __future__ import annotations

from pathlib import Path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_ui_uses_app_api_only() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    qt_app = repo_root / "src" / "ui" / "mvp" / "qt_app.py"
    tk_app = repo_root / "src" / "ui" / "mvp" / "tk_app.py"
    export_utils = repo_root / "src" / "ui" / "mvp" / "export_utils.py"

    qt_text = _read(qt_app)
    tk_text = _read(tk_app)
    export_text = _read(export_utils)

    forbidden = ["app.controller", "from ...app.controller", "from src.app.controller"]

    for needle in forbidden:
        assert needle not in qt_text
        assert needle not in tk_text
        assert needle not in export_text
