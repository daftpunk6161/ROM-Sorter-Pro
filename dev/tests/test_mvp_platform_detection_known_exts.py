from __future__ import annotations

from src.database.console_db import ENHANCED_CONSOLE_DATABASE


def test_console_db_has_lynx_extensions() -> None:
    lynx = ENHANCED_CONSOLE_DATABASE["Lynx"]
    assert ".lnx" in lynx.extensions
    assert ".lyx" in lynx.extensions
    assert ".o" in lynx.extensions


def test_console_db_has_intellivision_extension() -> None:
    intv = ENHANCED_CONSOLE_DATABASE["Intellivision"]
    assert ".int" in intv.extensions
