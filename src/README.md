# ROM Sorter Pro - Source Code Structure

This document provides an overview of the ROM Sorter Pro source code organization.

## Module Structure

The application is designed with a modular architecture to improve maintainability, testability, and separation of concerns:

### Core Modules

- `main.py`: Application entry point and main orchestration
- `config.py`: Configuration management (gradually being modularized)
- `exceptions.py`: Centralized exception handling

### Specialized Modules

- `config/`: Configuration management
  - `modules/`: Modularized configuration components
  - `manager.py`: Central configuration orchestration

- `core/`: Core functionality
  - `rom_models.py`: Data models for ROM files
  - `file_utils.py`: File manipulation utilities

- `detectors/`: ROM detection and classification
  - `archive_detector.py`: Archive file analysis
  - `console_detector.py`: Console detection
  - `ml_detector.py`: Machine learning detection

- `utils/`: Utility functions and helpers
  - `performance_enhanced.py`: Performance monitoring
  - `logging_integration.py`: Centralized logging

- `ui/`: User interfaces
  - `gui.py`: Tk GUI entry
  - `main_window.py`: Tk window composition (core/handlers/scanner)
  - `gui_core.py`: Core layout and setup
  - `gui_handlers.py`: Event handlers
  - `gui_scanner.py`: Background worker helpers
  - `gui_components.py`: Reusable widgets
  - `cli/`: Command-line interface

## Dependency Graph

The application follows a layered architecture:

1. **Presentation Layer**: UI components (GUI, CLI, Web)
2. **Application Layer**: Main orchestration, processing logic
3. **Domain Layer**: Core business logic, ROM models
4. **Infrastructure Layer**: File I/O, configuration, logging

## Future Improvements

As part of the ongoing modularization:

- Further decomposition of `main.py` into specialized service classes
- Complete migration from `config.py` to modular configuration components
- Increased test coverage for core components
