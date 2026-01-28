"""DAT index controller helpers."""

from __future__ import annotations

import threading
from typing import Dict, Optional, Protocol

from ..config import Config
from ..core.dat_index_sqlite import build_index_from_config


class CancelTokenProtocol(Protocol):
    @property
    def event(self) -> threading.Event: ...


def build_dat_index(
    config: Optional[Config] = None,
    cancel_token: Optional[CancelTokenProtocol] = None,
) -> Dict[str, int]:
    cancel_event = cancel_token.event if cancel_token is not None else None
    return build_index_from_config(config=config, cancel_event=cancel_event)
