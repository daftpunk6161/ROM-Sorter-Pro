from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type, TypeVar

T = TypeVar("T")


@dataclass
class Container:
    _singletons: Dict[Type[Any], Any] = field(default_factory=dict)

    def register_singleton(self, key: Type[T], instance: T) -> None:
        self._singletons[key] = instance

    def has(self, key: Type[Any]) -> bool:
        return key in self._singletons

    def get(self, key: Type[T]) -> Optional[T]:
        instance = self._singletons.get(key)
        return instance if instance is None or isinstance(instance, key) else instance


_default_container: Optional[Container] = None


def get_default_container() -> Container:
    global _default_container
    if _default_container is None:
        _default_container = Container()
    return _default_container
