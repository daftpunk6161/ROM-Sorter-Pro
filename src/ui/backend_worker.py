"""Backend worker abstraction for UI threads."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class BackendWorker(Protocol):
    def start(self) -> None: ...
    def cancel(self) -> None: ...
    def is_running(self) -> bool: ...


@dataclass
class BackendWorkerHandle:
    thread: Any
    cancel_token: Any

    def start(self) -> bool:
        try:
            self.thread.start()
            return True
        except Exception as exc:
            logger.exception("Backend worker start failed: %s", exc)
            return False

    def cancel(self) -> bool:
        try:
            if self.cancel_token is not None:
                self.cancel_token.cancel()
            return True
        except Exception as exc:
            logger.exception("Backend worker cancel failed: %s", exc)
            return False

    def is_running(self) -> bool:
        try:
            if hasattr(self.thread, "isRunning"):
                return bool(self.thread.isRunning())
            if hasattr(self.thread, "is_alive"):
                return bool(self.thread.is_alive())
        except Exception:
            return False
        return False
