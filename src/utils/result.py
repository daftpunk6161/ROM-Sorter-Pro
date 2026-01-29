"""Lightweight Result types (Ok/Err)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Optional, TypeGuard, TypeVar, Union

T = TypeVar("T")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T


@dataclass(frozen=True)
class Err:
    error: Exception


Result = Union[Ok[T], Err]


def is_ok(result: Result[T]) -> TypeGuard[Ok[T]]:
    return isinstance(result, Ok)


def is_err(result: Result[T]) -> TypeGuard[Err]:
    return isinstance(result, Err)


def unwrap(result: Result[T]) -> T:
    if isinstance(result, Ok):
        return result.value
    raise result.error


def unwrap_or(result: Result[T], default: T) -> T:
    if isinstance(result, Ok):
        return result.value
    return default


def error_message(result: Result[T]) -> Optional[str]:
    if isinstance(result, Err):
        return str(result.error)
    return None
