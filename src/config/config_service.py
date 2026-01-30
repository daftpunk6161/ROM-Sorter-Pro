from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass
class ConfigService:
    _loader: Callable[[], Dict[str, Any] | None]
    _saver: Callable[[Dict[str, Any]], None]

    def load(self) -> Dict[str, Any] | None:
        return self._loader()

    def save(self, data: Dict[str, Any]) -> None:
        self._saver(data)
