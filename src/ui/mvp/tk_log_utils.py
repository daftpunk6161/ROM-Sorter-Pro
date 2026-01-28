"""Tk log buffer utilities for MVP UI."""

from __future__ import annotations

from typing import Callable, List


class TkLogBuffer:
    def __init__(
        self,
        root,
        log_text,
        get_filter_text: Callable[[], str],
        *,
        max_lines: int = 5000,
    ) -> None:
        self._root = root
        self._log_text = log_text
        self._get_filter_text = get_filter_text
        self._max_lines = max_lines
        self._buffer: List[str] = []
        self._history: List[str] = []
        self._flush_scheduled = False

    def append(self, text: str) -> None:
        if not text:
            return
        self._buffer.append(str(text))
        if not self._flush_scheduled:
            self._flush_scheduled = True
            self._root.after(100, self.flush)

    def flush(self) -> None:
        self._flush_scheduled = False
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
        filter_text = (self._get_filter_text() or "").strip().lower()
        if filter_text:
            lines = [line for line in lines if filter_text in line.lower()]
        payload = "\n".join(lines) + ("\n" if lines else "")
        if payload:
            self._log_text.insert("end", payload)
        try:
            lines_count = int(self._log_text.index("end-1c").split(".")[0])
            if lines_count > self._max_lines:
                self._log_text.delete("1.0", f"{lines_count - self._max_lines}.0")
        except Exception:
            return

    def apply_filter(self, text: str) -> None:
        filter_text = (text or "").strip().lower()
        try:
            self._log_text.delete("1.0", "end")
        except Exception:
            return
        if not self._history:
            return
        if not filter_text:
            self._log_text.insert("end", "\n".join(self._history) + "\n")
            return
        filtered = [line for line in self._history if filter_text in line.lower()]
        if filtered:
            self._log_text.insert("end", "\n".join(filtered) + "\n")
