#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ROM Sorter Pro - module entry point.

This shim keeps `python -m src` working by delegating to start_rom_sorter.py.
GUI-first entry remains: python start_rom_sorter.py --gui
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

    import start_rom_sorter

    result = start_rom_sorter.main()
    if result is None:
        return 0
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
