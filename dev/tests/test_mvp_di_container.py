from __future__ import annotations

from src.utils.di import Container


class Foo:
    def __init__(self, value: int) -> None:
        self.value = value


def test_container_singleton_roundtrip() -> None:
    container = Container()
    foo = Foo(42)
    container.register_singleton(Foo, foo)

    assert container.has(Foo) is True
    assert container.get(Foo) is foo
