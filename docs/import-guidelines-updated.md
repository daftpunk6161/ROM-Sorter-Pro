# Import Structure Standardization for ROM Sorter Pro

## Overview

This document defines the standardized import structure for the ROM Sorter Pro project. Following these standards improves code readability, reduces potential import errors, and enhances maintainability.

## Principles

1. **Consistent grouping**: Imports are divided into logical groups
2. **Clear hierarchy**: Standard libraries before third-party libraries before own modules
3. **Avoidance of circular dependencies**: No mutual imports between modules
4. **No dynamic imports**: Imports belong at the beginning of the file, not in functions
5. **Simplicity over cleverness**: Preference for explicit, clear imports

## Standard Import Structure

Each Python file should contain the following import groups in the specified order:

```python
# Group 1: Standard libraries
import os
import sys
import logging
# more standard libraries...

# Group 2: Third-party libraries (e.g., PyQt5, numpy, etc.)
import numpy as np
from PyQt5 import QtCore

# Group 3: Project-specific imports
# When importing from outside src directory:
from src.core.file_utils import create_directory_if_not_exists

# Group 4: Project-specific imports from within src directory
# Always use relative imports when within the src directory
from .database.rom_database import ROMDatabase

# Group 5: Relative imports (only within the same package)
from .theme_manager import ThemeManager
```

## Specific Rules

### Absolute vs. Relative Imports

- **Absolute Imports** (`from src.utils import x`) for:
  - Imports from outside the src directory
  - Imports in scripts that are at the project root level

- **Relative Imports** (`from .submodule import x`) for:
  - All imports within the src directory
  - Imports within the same package
  - Closely related functionality

### Avoid Dynamic Imports

The following should be avoided:

```python
def some_function():
    # WRONG: Import belongs at the beginning of the file
    from src.database.console_db import get_console_for_extension
    # ...
```

Instead:

```python
# RIGHT: Import at the beginning of the file
from .database.console_db import get_console_for_extension

def some_function():
    # Use the imported function
    # ...
```

### Import Aliases

Import aliases should be used sparingly and only for name conflicts or standardized abbreviations:

```python
# Acceptable use of aliasing
import numpy as np
from .utils.performance_enhanced import PerformanceMonitor as perf_mon
```

## Notes on Circular Dependencies

### Avoiding Circular Imports

To avoid circular dependencies:

1. Consider restructuring your code to avoid the need for circular imports
2. Move shared functionality to a common module that can be imported by both
3. Use late imports (import inside functions) only as a last resort
4. Consider using dependency injection

### Best Practices for Importing in `__init__.py`

When creating package `__init__.py` files:

1. Keep them minimal - don't import everything
2. Only expose the APIs that are intended to be public
3. Use conditional imports for optional dependencies
4. Be careful with imports that might create circular dependencies

## Version 2.1.8 Import Guidelines Update

As of version 2.1.8, we have standardized all imports within the src directory to use relative imports. This helps avoid circular dependency issues and makes the code more maintainable.

Example:

```python
# OLD (not preferred):
from src.utils.logger import setup_logger

# NEW (preferred within src directory):
from .utils.logger import setup_logger
```
