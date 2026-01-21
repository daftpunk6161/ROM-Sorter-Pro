"""Ensure src.ui.compat import does not eagerly load GUI bindings."""

from __future__ import annotations

import subprocess
import sys


def test_ui_compat_import_lightweight() -> None:
    code = (
        "import sys; import importlib; "
        "importlib.import_module('src.ui.compat'); "
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
