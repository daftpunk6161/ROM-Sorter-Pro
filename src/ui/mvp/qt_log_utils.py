"""Qt log buffer utilities for MVP UI."""

from __future__ import annotations

from typing import List


import logging
import time


class QtLogHandler(logging.Handler):
    def __init__(self, emit_fn):
        super().__init__()
        self._emit_fn = emit_fn
        self._last_message = ""
        self._last_ts = 0.0
        self._qt_gui_handler = False

    def emit(self, record):
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        now = time.monotonic()
        if msg == self._last_message and (now - self._last_ts) < 0.5:
            return
        self._last_message = msg
        self._last_ts = now
        try:
            self._emit_fn(msg)
        except Exception:
            return


class QtLogBuffer:
    def __init__(self, log_view, *, max_lines: int = 5000) -> None:
        self._log_view = log_view
        self._max_lines = max_lines
        self._buffer: List[str] = []
        self._history: List[str] = []
        self._filter_text = ""
        self._level_filter = ""
        self._autoscroll = True

    def set_level_filter(self, level: str) -> None:
        self._level_filter = (level or "").strip().upper()

    def _line_matches_level(self, line: str) -> bool:
        if not self._level_filter or self._level_filter == "ALL":
            return True
        marker = f" - {self._level_filter} - "
        return marker in line

    def set_autoscroll(self, enabled: bool) -> None:
        self._autoscroll = bool(enabled)

    def append(self, text: str) -> None:
        if not text:
            return
        self._buffer.append(str(text))

    def flush(self) -> None:
        if not self._buffer:
            return
        lines: List[str] = []
        for entry in self._buffer:
            lines.extend(str(entry).splitlines())
        self._buffer.clear()
        if lines:
            self._history.extend(lines)
            if len(self._history) > self._max_lines:
                self._history = self._history[-self._max_lines :]
        try:
            bar = self._log_view.verticalScrollBar()
            at_bottom = bar.value() >= bar.maximum()
        except Exception:
            bar = None
            at_bottom = True
        if not self._filter_text and not self._level_filter:
            if lines:
                self._log_view.appendPlainText("\n".join(lines))
            if bar is not None and (self._autoscroll or at_bottom):
                bar.setValue(bar.maximum())
            return
        filtered = [
            line
            for line in lines
            if self._line_matches_level(line) and self._filter_text in line.lower()
        ]
        if filtered:
            self._log_view.appendPlainText("\n".join(filtered))
            if bar is not None and (self._autoscroll or at_bottom):
                bar.setValue(bar.maximum())

    def apply_filter(self, text: str) -> None:
        self._filter_text = (text or "").strip().lower()
        try:
            self._log_view.clear()
        except Exception:
            return
        if not self._history:
            return
        if not self._filter_text and not self._level_filter:
            self._log_view.appendPlainText("\n".join(self._history))
            return
        filtered = [
            line
            for line in self._history
            if self._line_matches_level(line) and self._filter_text in line.lower()
        ]
        if filtered:
            self._log_view.appendPlainText("\n".join(filtered))
