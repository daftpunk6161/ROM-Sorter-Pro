"""Legacy Qt themes removed (MVP cleanup)."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    qss: str
    palette: Optional[object] = None
    base_font_family: Optional[str] = None
    base_font_size: int = 10


THEMES = {}


class ThemeManager:
    def __init__(self, _app: Optional[object] = None) -> None:
        self._app = _app

    def available(self):
        return THEMES

    def apply(self, _key: str) -> bool:
        return False


__all__ = ["Theme", "ThemeManager", "THEMES"]
