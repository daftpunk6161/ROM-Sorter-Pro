#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Database path helpers."""

from __future__ import annotations

import os
from typing import Optional

from ..config.io import load_config

DEFAULT_ROM_DB_RELATIVE = os.path.join("rom_databases", "roms.db")


def get_repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resolve_db_path(path: Optional[str]) -> str:
    if not path:
        path = DEFAULT_ROM_DB_RELATIVE
    if os.path.isabs(path):
        return path
    return os.path.join(get_repo_root(), path)


def get_rom_db_path() -> str:
    config = load_config()
    db_config = config.get("database", {}) if isinstance(config, dict) else {}
    return resolve_db_path(db_config.get("rom_db_path"))
