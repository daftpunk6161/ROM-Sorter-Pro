"""Backend worker abstraction for UI threads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class BackendWorker(Protocol):
    def start(self) -> None: ...
    def cancel(self) -> None: ...
    def is_running(self) -> bool: ...


@dataclass
class BackendWorkerHandle:
    thread: Any
    cancel_token: Any

    def start(self) -> None:
        try:
            self.thread.start()
        except Exception:
            return None

    def cancel(self) -> None:
        try:
            if self.cancel_token is not None:
                self.cancel_token.cancel()
        except Exception:
            return None

    def is_running(self) -> bool:
        try:
            if hasattr(self.thread, "isRunning"):
                return bool(self.thread.isRunning())
            if hasattr(self.thread, "is_alive"):
                return bool(self.thread.is_alive())
        except Exception:
            return False
        return False
