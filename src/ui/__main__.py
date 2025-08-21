#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROM Sorter Pro - UI Modul Einstiegspunkt
Ermöglicht direkten Start des UI-Moduls: python -m src.ui
"""

import sys
from .gui import main

if __name__ == "__main__":
    sys.exit(main())
