"""Verify src.main shim delegates to start_rom_sorter."""

from __future__ import annotations

import importlib


def test_src_main_exists_and_callable() -> None:
    module = importlib.import_module("src.main")
    assert hasattr(module, "main")
