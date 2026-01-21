"""Ensure src.app.api import does not pull optional UI bindings."""

from __future__ import annotations

import subprocess
import sys


def test_app_api_import_lightweight() -> None:
    code = (
        "import sys; import importlib; "
        "importlib.import_module('src.app.api'); "
        "mods = {'PySide6','PyQt5','tkinter'}; "
        "print(','.join(sorted(m for m in sys.modules if m in mods)))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""
