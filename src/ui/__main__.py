#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ROM Sorter Pro - UI module entry point."""

import sys
import logging


def main():
    """Main entry point for the UI module."""
    logging.info("Starting GUI via compat launcher")
    try:
        from .compat import launch_gui

        return int(launch_gui(backend=None))
    except ImportError:
        logging.error("Konnte MVP GUI nicht starten.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
