"""Legacy Qt typography helpers removed (MVP cleanup)."""

from typing import Optional


def try_load_font(_font_path: str) -> Optional[str]:
    return None


def set_app_font(_family: str, _point_size: int = 10) -> None:
    return None
