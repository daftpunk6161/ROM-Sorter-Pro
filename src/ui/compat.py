"""ROM Sorter Pro - UI Compatibility / Backend Selection

Goals:
- Deterministic GUI backend selection (Qt preferred, Tk fallback)
- Lazy imports so missing optional packages (ML/Web/pandas/etc.) do not break GUI start
- A single stable launcher API used by entry points

Public API:
- launch_gui(backend: Optional[str]) -> int
- select_backend(backend: Optional[str]) -> str
- is_ui_available() -> bool
- get_ui_mode() -> str

Environment override:
- ROM_SORTER_GUI_BACKEND=qt|tk
"""

from __future__ import annotations

import os
import logging
import traceback
from typing import Optional, Literal

logger = logging.getLogger(__name__)

GUIBackend = Literal["qt", "tk"]

# Drag-and-drop availability flag (kept for UI state).
DND_AVAILABLE = False


class GUIBackendError(RuntimeError):
    """Raised when no usable GUI backend can be started."""


def _detect_qt_binding() -> Optional[str]:
    """Return the available Qt binding name, or None.

    Order of preference for this project:
    1) PySide6
    2) PyQt5
    """

    try:
        import PySide6  # noqa: F401

        return "pyside6"
    except Exception:
        pass

    try:
        import PyQt5  # noqa: F401

        return "pyqt5"
    except Exception:
        pass

    return None


def is_ui_available() -> bool:
    """Check whether at least one UI backend is usable."""

    if _detect_qt_binding() is not None:
        return True

    try:
        import tkinter  # noqa: F401

        return True
    except Exception:
        return False


def select_backend(backend: Optional[str] = None) -> GUIBackend:
    """Select exactly one GUI backend deterministically.

    Priority:
    1) Explicit `backend` argument
    2) Env var ROM_SORTER_GUI_BACKEND
    3) Auto: Qt if available else Tk
    """

    if backend:
        backend_normalized = backend.strip().lower()
        if backend_normalized in ("qt", "tk"):
            return backend_normalized  # type: ignore[return-value]
        raise GUIBackendError(f"Invalid backend: {backend!r} (expected 'qt' or 'tk')")

    env_backend = (os.environ.get("ROM_SORTER_GUI_BACKEND") or "").strip().lower()
    if env_backend in ("qt", "tk"):
        return env_backend  # type: ignore[return-value]

    return "qt" if _detect_qt_binding() is not None else "tk"


def get_ui_mode() -> str:
    """Return the selected UI mode (qt/tk/none)."""

    try:
        return select_backend(None)
    except Exception:
        return "none"


def launch_gui(backend: Optional[str] = None) -> int:
    """Launch the GUI.

    Args:
        backend: 'qt' or 'tk' (optional). If None, auto-select.

    Returns:
        Process exit code (0 ok, non-zero on failure).
    """

    chosen = select_backend(backend)
    logger.info("Selected GUI backend: %s", chosen)

    qt_error: Optional[BaseException] = None
    tk_error: Optional[BaseException] = None

    if chosen == "qt":
        try:
            from .mvp.qt_app import run as run_qt

            return int(run_qt())
        except Exception as exc:
            qt_error = exc
            # Do not hard-crash if Qt isn't actually usable.
            logger.warning("Qt backend failed to start (%s). Falling back to Tk.", exc)
            logger.debug("Qt backend traceback:\n%s", traceback.format_exc())

    try:
        from .mvp.tk_app import run as run_tk

        return int(run_tk())
    except Exception as exc:
        tk_error = exc
        logger.exception("Tk backend failed to start.")
        logger.debug("Tk backend traceback:\n%s", traceback.format_exc())
        qt_detail = f"{type(qt_error).__name__}: {qt_error}" if qt_error else "not attempted"
        tk_detail = f"{type(tk_error).__name__}: {tk_error}" if tk_error else "unknown"
        raise GUIBackendError(
            "No usable GUI backend found. Install PySide6/PyQt5 or ensure Tk is available. "
            f"Qt error: {qt_detail}. Tk error: {tk_detail}."
        ) from exc


