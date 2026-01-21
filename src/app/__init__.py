"""App-level APIs.

This package contains thin controller functions intended to be called by GUI/CLI.
It keeps the UI decoupled from low-level scanner/sorter internals.
"""

from . import api

__all__ = ["api"]
