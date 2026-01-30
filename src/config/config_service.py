from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from .models import ConfigModel, validate_config


@dataclass
class ConfigService:
    _loader: Callable[[], Dict[str, Any] | None]
    _saver: Callable[[Dict[str, Any]], None]

    def load(self) -> Dict[str, Any] | None:
        return self._loader()

    def save(self, data: Dict[str, Any]) -> None:
        self._saver(data)

    def load_validated(self) -> ConfigModel | None:
        payload = self._loader()
        if payload is None:
            return None
        try:
            return validate_config(payload)
        except RuntimeError:
            return None
