#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Pro v2.1.5 - Universal console ROM organizer with refactored architecture

REFACTORED VERSION 2.1.5:
- FIXED: God Class complexity reduced with focused components
- ENHANCED: Better separation of concerns and single responsibility
- IMPROVED: Error handling and resource management
- ADDED: Dependency injection pattern for better testability
- OPTIMIZED: Memory management and performance monitoring
- STRENGTHENED: Security validation throughout
"""

import os
import sys
import argparse
import logging
import json
import threading
import time
import signal
import importlib.util
import shutil
import gc
from typing import Dict, Any, Optional, List, Union, Iterator
import weakref
from contextlib import contextmanager, ExitStack
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import multiprocessing
from queue import Queue, Empty

# Import from the specialized modules
from src.core.file_utils import (
    normalize_filename
)

from src.database.console_db import (
    get_all_rom_extensions
)

from src.utils.performance_enhanced import (
    PerformanceMonitor as performance_monitor
)

from src.security.security_utils import (
    sanitize_path as validate_path
)

# Import Some Functions for Legacy Compatibility
# Define A Simple Validation Function Since the Original One Cannot Be Imported
def validate_config(config: dict) -> bool:
    """
    Simple configuration validation function.

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if configuration is valid, False otherwise
    """
    return config is not None and isinstance(config, dict)

# Import Exceptions for Centralized Error Handling
from src.exceptions import (ConfigurationError, ValidationError,
                          ProcessingError, ConsoleDetectionError, FileOperationError)

# Configure Main Logger
logger = logging.getLogger(__name__)

# Optional imports with enhanced error handling
try:
# THESE Imports ARE Currently not Directly used in this file
# But May be needed in future or by other module
    # Commented out to satisfy linter but kept for reference
# From ai_features import (
# Optimizedromdabase as Romdatabase,
# Optimized metataenricher as metadataenricher,
# OptimizedonlinemememememneMatadapaprovider AS online meta provider,
# Enhancedaiconsoledetetector AS Aiconsoledetector,
# Enhancedduplicatedetetector as duplicatedetetector,
# Optimized MARMENTRECOMMENDATION SYSTEM AS SMARTREMECOMMENDATION System,
# Optimized cover artdownloader as cover artdownloader
# )))
    # Just check if the module exists, but don't import it directly
# to avoid unused import Warning
    import importlib
    spec = importlib.util.find_spec("ai_features")
    AI_FEATURES_AVAILABLE = spec is not None
    if AI_FEATURES_AVAILABLE:
        logger.info("AI features available and loaded")
except ImportError as e:
    AI_FEATURES_AVAILABLE = False
    logger.warning(f"AI features not available: {e}")
    logger.warning("Using base functionality")

# Gui Import wants be done dynamically when needed to avoid circular imports
GUI_AVAILABLE = False
try:
# Check First for the New Modular UI
    spec = importlib.util.find_spec("src.ui")
    if spec is not None:
# Check IF New Modular Ui is Available
        try:
            from src.ui.compat import is_ui_available, get_ui_mode
            GUI_AVAILABLE = is_ui_available()
            UI_MODE = get_ui_mode()
            logger.info(f"GUI module available (Mode: {UI_MODE})")
        except ImportError:
# Fallback to Direct Check of Old Gui
            spec = importlib.util.find_spec("gui")
            if spec is not None:
                GUI_AVAILABLE = True
                UI_MODE = "legacy"
                logger.info("GUI module available (Legacy)")
    else:
# Fallback to Direct Check of Old Gui
        spec = importlib.util.find_spec("gui")
        if spec is not None:
            GUI_AVAILABLE = True
            UI_MODE = "legacy"
            logger.info("GUI module available (Legacy)")
except ImportError as e:
    logger.warning(f"GUI module not available: {e}")
    UI_MODE = "none"

# Web Interface Availability
try:
    import importlib.util
    spec = importlib.util.find_spec("web_interface")
    WEB_INTERFACE_AVAILABLE = spec is not None
    if WEB_INTERFACE_AVAILABLE:
        logger.info("Web interface available")
    else:
        logger.info("Web interface not found")
except ImportError as e:
    WEB_INTERFACE_AVAILABLE = False
    logger.warning(f"Web interface not available: {e}")


# =====================================================================================================
# Refactored Components - Addressing God Class Issues
# =====================================================================================================

@contextmanager
def log_operation_context(operation_name: str,
                          details: Optional[Dict[str, Any]] = None):
    """Context manager for structured logging of operations.

    Args:
        operation_name: Name of the operation to be logged
        details: Optional details about the operation
    """
    start_time = time.time()
    operation_id = f"{int(start_time * 1000)}-{threading.get_ident()}"

# Entry at the start of the operation
    log_data = {
        'operation': operation_name,
        'operation_id': operation_id,
        'start_time': datetime.now().isoformat(),
        'thread_id': threading.get_ident(),
    }
    if details:
        log_data.update(details)

    logger.debug(f"Operation started: {operation_name}",
                 extra={'context': log_data})

    try:
        yield operation_id
# Successful end
        duration = time.time() - start_time
        log_data['duration'] = duration
        log_data['status'] = 'success'
        msg = f"Operation successful: {operation_name}"
        msg += f" (Duration: {duration:.3f}s)"
        logger.debug(msg, extra={'context': log_data})

    except Exception as e:
# Error During the Operation
        duration = time.time() - start_time
        log_data['duration'] = duration
        log_data['status'] = 'error'
        log_data['error'] = str(e)
        log_data['error_type'] = type(e).__name__

        msg = f"Operation failed: {operation_name}"
        msg += f" (Duration: {duration:.3f}s)"
        logger.error(msg, extra={'context': log_data})
        raise


@dataclass
class ProcessingOptions:
    """Centralized processing options with validation and error handling."""
    console_sorting: bool = True
    create_console_folders: bool = True
    sort_within_console: bool = True
    detect_duplicates: bool = True
    handle_homebrew: bool = True
    preserve_timestamps: bool = True
    create_backup: bool = False
    dry_run: bool = False
    max_workers: Optional[int] = None
    batch_size: int = 200
    use_work_stealing: bool = True

    def __post_init__(self):
        """Validate options after initialization."""
        self._validate_options()

# Ensure sensitive limits
        if self.max_workers and (self.max_workers < 1 or self.max_workers > 32):
            self.max_workers = min(os.cpu_count() or 4, 8)

        if self.batch_size < 1:
            self.batch_size = 100
        elif self.batch_size > 10000:
            self.batch_size = 1000

        if self.memory_limit_mb < 64:
            self.memory_limit_mb = 64
        elif self.memory_limit_mb > 8192:
            self.memory_limit_mb = 8192

        logger.debug(f"ProcessingOptions initialized: {self}")

        logger.debug(f"ProcessingOptions initialized: {self}")

    def _validate_options(self) -> None:
        """Validates the processing options."""
# Validate Batch_Size (positive and within Reasonable Range)
        if not isinstance(self.batch_size, int) or self.batch_size < 1:
            raise ValidationError("batch_size must be a positive integer",
                                  field_name="batch_size",
                                  expected_type="positive integer")
        if self.batch_size > 10000:
            logger.warning(f"Very large batch_size selected ({self.batch_size}). "
                           f"This could lead to memory issues.")

# Validate Max_Workers
        if self.max_workers is not None:
            if not isinstance(self.max_workers, int) or self.max_workers < 1:
                raise ValidationError("max_workers must be None or a positive integer",
                                      field_name="max_workers",
                                      expected_type="positive integer or None")
# Warning for Too many workers
            cpu_count = multiprocessing.cpu_count()
            if self.max_workers > cpu_count * 2:
                logger.warning(f"max_workers ({self.max_workers}) is significantly higher "
                               f"than the number of CPU cores ({cpu_count})")

    def to_dict(self) -> Dict[str, Any]:
        """Converts the options to a dictionary for structured logging."""
        return {
            'console_sorting': self.console_sorting,
            'create_console_folders': self.create_console_folders,
            'sort_within_console': self.sort_within_console,
            'detect_duplicates': self.detect_duplicates,
            'handle_homebrew': self.handle_homebrew,
            'preserve_timestamps': self.preserve_timestamps,
            'create_backup': self.create_backup,
            'dry_run': self.dry_run,
            'max_workers': self.max_workers,
            'batch_size': self.batch_size,
            'use_work_stealing': self.use_work_stealing,
        }
    enable_compression: bool = False
    verify_integrity: bool = False
    memory_limit_mb: int = 512
    io_timeout: float = 30.0
    skip_existing: bool = True
    create_symlinks: bool = False
# New Options for Unknown Roms and Duplicates
    separate_unknown_roms: bool = True  # Separate ROMs with unclear detection
    unknown_roms_folder: str = "Unknown"  # Folder for unknown ROMs
    separate_duplicates: bool = True  # Move Duplicates to a separate folder
    duplicates_folder: str = "Duplicates"  # Folder for duplicates
    min_confidence_threshold: float = 0.7  # Minimum confidence for definitive assignment
    organize_by_year: bool = False  # Organize ROMs by release year
    separate_regions: bool = False  # Separate ROMs by regions


@dataclass
class ProcessingStatistics:
    """Enhanced statistics for ROM processing operations."""
    files_processed: int = 0
    files_moved: int = 0
    files_copied: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    duplicates_found: int = 0
    homebrew_detected: int = 0
    consoles_detected: int = 0
    errors: int = 0
    warnings: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    cache_hits: int = 0
    cache_misses: int = 0
    average_file_size: float = 0.0
    total_bytes_processed: int = 0
    peak_workers: int = 0
    worker_efficiency: float = 0.0
    memory_peak_mb: float = 0.0
    gc_collections: int = 0
    io_operations: int = 0

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()

    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0

    @property
    def files_per_second(self) -> float:
        duration = self.duration
        return self.files_processed / max(duration, 0.001)

    @property
    def cache_hit_rate(self) -> float:
        total_cache_ops = self.cache_hits + self.cache_misses
        return (self.cache_hits / max(total_cache_ops, 1)) * 100

    @property
    def success_rate(self) -> float:
        total_operations = self.files_processed
        successful = total_operations - self.errors - self.files_failed
        return (successful / max(total_operations, 1)) * 100

    @property
    def throughput_mbps(self) -> float:
        """Calculate throughput in MB/s."""
        duration = self.duration
        if duration > 0:
            return (self.total_bytes_processed / (1024 * 1024)) / duration
        return 0.0


class MemoryManager:
    """Enhanced memory management for large ROM collections.

    This optimized version provides adaptive memory management with:
    - Dynamic thresholds based on system resources
    - Memory leak detection for long-running processes
    - Optimization of the garbage collector with generation-specific settings
    - Detailed memory statistics and reporting functions
    """

    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_mb = max_memory_mb
# Dynamic Threshold That Adapts to Usage
        self.gc_threshold = max_memory_mb * 0.8
# Minimum Threshold to avoid excessive GC Calls
        self.min_threshold_mb = 64
        self.last_gc = time.time()
# Adaptive GC Interval That Adjusts Based on Memory Pressure
        self.base_gc_interval = 30
        self.gc_interval = self.base_gc_interval
        self.memory_pressure = 0.0  # 0.0 bis 1.0

# Advanced Memory Statistics
        self._memory_stats = {
            'peak': 0,
            'collections': 0,
            'last_values': [],  # Last N measurements for trend analysis
            'history_size': 10,
            'leak_detection': {
                'baseline': 0,
                'growth_rate': 0.0,
                'consecutive_increases': 0
            },
            'system': {
                'total': 0,
                'available': 0,
            }
        }

# Optimization of the Garbage Collection
        self._configure_gc()

# Initialize the memory trend
        self._update_system_memory()

    def _configure_gc(self):
        """Configures the garbage collector for optimal performance.

        Optimizes collection for handling large data volumes.
        """
# ENABLE Automatic Generation Collection with Optimized Thresholds
        gc.enable()
# Adjust Generation Thresholds (Defaults are Often Too Conservative)
# Higher Thresholds Reduce Collection Frequency
        old_thresholds = gc.get_threshold()
# Increase Gen0 Threshold - Allow More Objects Before GC Trigger
        gen0_threshold = old_thresholds[0] * 2
# Adjust Gen1/Gen2 Ratios
        gen1_threshold = 10
        gen2_threshold = 10
        gc.set_threshold(gen0_threshold, gen1_threshold, gen2_threshold)
        logging.debug(f"GC thresholds adjusted from {old_thresholds} to "
                      f"{gc.get_threshold()}")

    def _update_system_memory(self):
        """Updates information about available system memory."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            # Convert to MB
            self._memory_stats['system']['total'] = mem.total / (1024 * 1024)
            self._memory_stats['system']['available'] = mem.available / (1024 * 1024)
        except (ImportError, Exception) as e:
            logging.warning(f"System memory information not available: {e}")

    def check_memory_usage(self) -> bool:
        """Checks if memory usage is within limits and dynamically adjusts
        the memory management strategy.
        """
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            # Update memory statistics
            peak = self._memory_stats['peak']
            self._memory_stats['peak'] = max(peak, memory_mb)

# Update Memory Trend for Leak Detection
            self._update_memory_trend(memory_mb)

# Update System Memory Status (Every 10 Checks)
            if self._memory_stats['collections'] % 10 == 0:
                self._update_system_memory()

# Calculate Memory Pressure (0.0-1.0, where 1.0 is maximum pressure)
            self.memory_pressure = min(1.0, memory_mb / self.max_memory_mb)

# Adaptive GC Interval Based on Memory Pressure
            factor = 1.0 - self.memory_pressure
            self.gc_interval = max(5, self.base_gc_interval * factor)

# Adjust Dynamic Threshold Based on Memory Pressure
# With high pressure, We Lower the Threshold more aggressively
            pressure_factor = 0.9 - 0.3 * self.memory_pressure
            self.gc_threshold = max(
                self.min_threshold_mb,
                self.max_memory_mb * pressure_factor
            )

            if memory_mb > self.gc_threshold:
                self._trigger_gc()
                memory_mb = process.memory_info().rss / 1024 / 1024
                return memory_mb < self.max_memory_mb

# Memory Leak Detection
            if self._detect_memory_leak():
                logging.warning("Possible memory leak detected! "
                                "Performing intensive garbage collection.")
                self._handle_memory_leak()

            return True
        except ImportError:
            logging.warning("Psutil not installed. Memory monitoring disabled.")
            return True
        except Exception as e:
            logging.warning(f"Error checking memory: {e}")
            return True

    def _update_memory_trend(self, current_memory_mb):
        """Updates memory trend for leak detection."""
        history = self._memory_stats['last_values']

# Store Last N Values for Trend Analysis
        history.append(current_memory_mb)
        if len(history) > self._memory_stats['history_size']:
            history.pop(0)

        # If we have enough data, calculate growth rate
        if len(history) >= 3:
# Simple linear regression to Estimate Growth Rate
            x = list(range(len(history)))
            y = history
            n = len(x)

            # Calculate slope coefficient
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x_i * y_i for x_i, y_i in zip(x, y))
            sum_xx = sum(x_i * x_i for x_i in x)

            # Avoid division by zero
            denominator = n * sum_xx - sum_x * sum_x
            if denominator != 0:
                numerator = n * sum_xy - sum_x * sum_y
                slope = numerator / denominator
                self._memory_stats['leak_detection']['growth_rate'] = slope

# Count Consecutive Increases
            increases = 0
            for i in range(1, len(history)):
                if history[i] > history[i-1]:
                    increases += 1

            if increases == len(history) - 1:
                path = self._memory_stats['leak_detection']
                path['consecutive_increases'] += 1
            else:
                path = self._memory_stats['leak_detection']
                path['consecutive_increases'] = 0

    def _detect_memory_leak(self) -> bool:
        """Detects possible memory leaks based on usage trends."""
        leak_data = self._memory_stats['leak_detection']

# Continuous Increase in Memory Consumpto Over Time
        if leak_data['consecutive_increases'] >= 5:
            return True

# Positive Growth Rate Above Threshold
# 5% of Maximum Memory Limit
        growth_rate_threshold = 0.05 * self.max_memory_mb

# ONLY Check at High Memory Pressure
        high_pressure = self.memory_pressure > 0.7
        high_growth = leak_data['growth_rate'] > growth_rate_threshold

        if high_growth and high_pressure:
            return True

        return False

    def _handle_memory_leak(self):
        """Response to detected memory leaks."""
# Perform a Complete Garbage Collection
        gc.collect(0)  # Generation 0
        gc.collect(1)  # Generation 1
        gc.collect(2)  # Generation 2 (oldest)

# Explicit Cleanup of Large Data Structures (IF Known)
        # This could be a custom function that deletes critical objects

# Reset Leak Detection After Cleanup
        self._memory_stats['leak_detection']['consecutive_increases'] = 0

    def _trigger_gc(self):
        """Triggers garbage collection when enough time has passed."""
        current_time = time.time()
        if current_time - self.last_gc > self.gc_interval:
            logging.debug(f"Triggering garbage collection "
                          f"(memory pressure: {self.memory_pressure:.2f})")

# Selective Collection Based on Memory Pressure
            if self.memory_pressure > 0.9:
# Critical Memory Pressure: Complete Collection of All Generations
                collected = gc.collect()
                logging.debug(f"Complete GC: {collected} objects collected")
            elif self.memory_pressure > 0.7:
                # High memory pressure: Generation 1 and 0
                collected_gen1 = gc.collect(1)
                collected_gen0 = gc.collect(0)
                collected = collected_gen0 + collected_gen1
                logging.debug(f"GC Gen0+1: {collected} objects collected")
            else:
# Normal Memory Pressure: ONLY Generation 0
                collected = gc.collect(0)
                logging.debug(f"GC Gen0: {collected} objects collected")

            self.last_gc = current_time
            self._memory_stats['collections'] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Returns detailed memory statistics."""
        stats = self._memory_stats.copy()

# Add Current Process Information IF Available
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            stats['current'] = {
                'rss': memory_info.rss / (1024 * 1024),  # Resident Set Size in MB
                'vms': memory_info.vms / (1024 * 1024),  # Virtual Memory Size in MB
                'shared': getattr(memory_info, 'shared', 0) / (1024 * 1024),  # Shared Memory in MB
                'text': getattr(memory_info, 'text', 0) / (1024 * 1024),  # Text (Code) in MB
                'lib': getattr(memory_info, 'lib', 0) / (1024 * 1024),  # Library in MB
                'data': getattr(memory_info, 'data', 0) / (1024 * 1024),  # Data + Stack in MB
            }
            stats['status'] = {
                'pressure': self.memory_pressure,
                'gc_interval': self.gc_interval,
                'gc_threshold': self.gc_threshold
            }
        except (ImportError, Exception):
            pass

# Add GC Information
        stats['gc'] = {
            'enabled': gc.isenabled(),
            'thresholds': gc.get_threshold(),
            'counts': gc.get_count()
        }

        return stats

    def reduce_memory_pressure(self, target_pressure: float = 0.5) -> bool:
        """Actively tries to reduce memory pressure using various strategies.

        Args:
            target_pressure: Target memory pressure (0.0-1.0)

        Returns:
            bool: True if memory pressure was successfully reduced
        """
        if self.memory_pressure <= target_pressure:
            return True

        current = self.memory_pressure
        logging.info(f"Active memory pressure reduction attempt "
                     f"(current: {current:.2f}, target: {target_pressure:.2f})")

# Strategy 1: Complete Garbage Collection
        logging.debug("Performing complete garbage collection")
        gc.collect()

# Strategy 2: Clear Python Object Cache
        logging.debug("Cleaning up cache objects")
        gc.collect()

# Re-Check Memory Pressure After Measures
        self.check_memory_usage()

        return self.memory_pressure <= target_pressure


class WorkStealingQueue:
    """Work-stealing queue for better load balancing."""

    def __init__(self, num_workers: int):
        self.num_workers = num_workers
        self.queues = [Queue() for _ in range(num_workers)]
        self.worker_index = 0
        self.lock = threading.Lock()
        self._stats = {'items_stolen': 0, 'total_items': 0}

    def put(self, item):
        """Put item in the least loaded queue."""
        with self.lock:
            min_queue = min(self.queues, key=lambda q: q.qsize())
            min_queue.put(item)
            self._stats['total_items'] += 1

    def get(self, worker_id: int, timeout: float = 0.1):
        """Get item with work stealing."""
        try:
            return self.queues[worker_id].get_nowait()
        except Empty:
            pass

        for i in range(self.num_workers):
            if i != worker_id:
                try:
                    item = self.queues[i].get_nowait()
                    self._stats['items_stolen'] += 1
                    return item
                except Empty:
                    continue

        try:
            return self.queues[worker_id].get(timeout=timeout)
        except Empty:
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get work-stealing statistics."""
        total = max(self._stats['total_items'], 1)
        steal_rate = (self._stats['items_stolen'] / total) * 100
        return {
            'total_items': self._stats['total_items'],
            'items_stolen': self._stats['items_stolen'],
            'steal_rate_percent': steal_rate
        }


class FileOperationsManager:
    """Focused file operations manager with security validation."""

    def __init__(self, allowed_base_dirs: Optional[List[str]] = None):
        self.allowed_base_dirs = [Path(d) for d in allowed_base_dirs] if allowed_base_dirs else None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def safe_move_file(self, source: Union[str, Path],
                    destination: Union[str, Path]) -> bool:
        """Securely move file with validation."""
        try:
# Direct Path Conversion
            source_path = Path(source).resolve()
            dest_path = Path(destination).resolve()

# Ensure Destination Directory Exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)

# Perform The Move
            shutil.move(str(source_path), str(dest_path))
            return True

        except Exception as e:
            self.logger.error(f"Error moving file {source} to {destination}: {e}")
            return False

    def safe_copy_file(self, source: Union[str, Path],
                      destination: Union[str, Path]) -> bool:
        """Securely copy file with validation."""
        try:
# Direct Path Conversion
            source_path = Path(source).resolve()
            dest_path = Path(destination).resolve()

# Ensure Destination Directory Exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)

# Perform The Copy
            shutil.copy2(str(source_path), str(dest_path))
            return True

        except Exception as e:
            self.logger.error(f"Error copying file {source} to {destination}: {e}")
            return False

    def ensure_directory_exists(self, directory: Union[str, Path]) -> bool:
        """Securely ensure directory exists."""
        try:
# Direct Path Conversion to Avoid Validate_Path Problems
            dir_path = Path(directory).resolve()
            dir_path.mkdir(parents=True, exist_ok=True)
            return True

        except Exception as e:
            self.logger.error(f"Error creating directory {directory}: {e}")
            return False


class ConsoleAnalyzer:
    """Focused console analysis and detection."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._cache = {}
        self._cache_lock = threading.RLock()

    def analyze_files(self, rom_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze ROM files for console distribution."""
        console_stats = defaultdict(lambda: {'count': 0, 'size': 0, 'files': []})

        for rom_file in rom_files:
            console = rom_file.get('console', 'Unknown')
            console_stats[console]['count'] += 1
            console_stats[console]['size'] += rom_file.get('size', 0)
            console_stats[console]['files'].append(rom_file['filename'])

# Convert to Regular Dict and Add Statistics
        result = {}
        for console, stats in console_stats.items():
            result[console] = {
                'count': stats['count'],
                'total_size_mb': stats['size'] / (1024 * 1024),
                'average_size_mb': (stats['size'] / stats['count']) / (1024 * 1024) if stats['count'] > 0 else 0,
                'sample_files': stats['files'][:5]
            }

        logging.info(f"Console analysis complete: {len(result)} different consoles detected")
        return result


class DuplicateDetector:
    """Focused duplicate detection and handling."""

    def __init__(self, region_priorities: Optional[Dict[str, int]] = None):
        self.region_priorities = region_priorities or {
            "World": 10, "Europe": 9, "USA": 8, "Germany": 7,
            "France": 6, "Spain": 5, "Italy": 4, "Japan": 3, "Other": 1
        }
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def detect_and_filter_duplicates(self, rom_files: List[Dict[str, Any]]) -> List[Dict[str, Any]
]:
        """Detect duplicates and select best versions."""
        filename_groups = defaultdict(list)

        for rom_file in rom_files:
            normalized_name = normalize_filename(rom_file['filename'])
            filename_groups[normalized_name].append(rom_file)

        filtered_files = []
        duplicates_removed = 0

        for group in filename_groups.values():
            if len(group) > 1:
                best_file = self._select_best_version(group)
                if best_file:
                    filtered_files.append(best_file)
                    duplicates_removed += len(group) - 1
            else:
                filtered_files.extend(group)

        self.logger.info(f"Duplicate detection complete: removed {duplicates_removed} duplicates")
        return filtered_files

    def _select_best_version(self, files: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select best version from duplicate files using scoring system."""
        if not files:
            return None

        if len(files) == 1:
            return files[0]

        def score_file(rom_file):
            score = 0
            filename = rom_file['filename'].lower()

# Prefer Larger Files
            score += rom_file.get('size', 0) / 1024

# Preferences region
            for region, priority in self.region_priorities.items():
                if region.lower() in filename:
                    score += priority * 1000
                    break

# Penalize Unperted Patterns
            unwanted_patterns = [r'\b(beta|alpha|demo|prototype)\b']
            import re
            for pattern in unwanted_patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    score -= 5000

            return score

        return max(files, key=score_file)


class RefactoredROMSorterPro:
    """
    Refactored ROM Sorter with improved architecture and reduced complexity.

    This class now uses dependency injection and has focused responsibilities:
    - Orchestration and coordination
    - Configuration management
    - Error handling and logging
    """

    def __init__(self, config_path: str = "src/config.json", options: Optional[ProcessingOptions] = None):
        self.config_path = config_path
        self.options = options or ProcessingOptions()
        self.config = self.load_config()
        self.setup_logging()

# Initialize Focused Components via Dependency Injection
        allowed_dirs = [os.path.dirname(self.config_path), os.getcwd()]
        self.file_ops = FileOperationsManager(allowed_dirs)
        self.console_analyzer = ConsoleAnalyzer()
        self.duplicate_detector = DuplicateDetector(
            self.config.get('region_priorities', {})
        )

# Enhanced Components
        self.performance_monitor = performance_monitor
        self.stats = ProcessingStatistics()
        self.memory_manager = MemoryManager(self.options.memory_limit_mb)

# Threading and Concurrency
        self._shutdown_event = threading.Event()
        self._worker_pool: Optional[ThreadPoolExecutor] = None
        self._work_queue: Optional[WorkStealingQueue] = None

        # Resource management
        self._resource_stack = ExitStack()
        self._file_handles = weakref.WeakSet()

# Secure Signal Handling - Only in Main Thread
        if threading.current_thread() is threading.main_thread():
            try:
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
                logging.debug("Signal handlers registered in main thread")
            except ValueError as e:
                logging.warning(f"Signal handling not available: {e}")

        logging.info("Refactored ROM Sorter Pro v2.1.5 initialized with improved architecture")

    def _signal_handler(self, signum, frame):
        """Thread-safe signal handler for graceful shutdown."""
        if not self._shutdown_event.is_set():
            logging.info(f"Signal {signum} received - starting graceful shutdown...")
            self._shutdown_event.set()

            if self._worker_pool:
                try:
                    self._worker_pool.shutdown(wait=False)
                    logging.info("Worker pool shutdown initiated")
                except Exception as e:
                    logging.error(f"Error shutting down worker pool: {e}")

    def load_config(self) -> Dict[str, Any]:
        """Enhanced config loading with security validation."""
        try:
            config_path = validate_path(self.config_path)

            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                if validate_config(config):
                    logging.info(f"Configuration loaded: {config_path}")
                    return config
                else:
                    logging.warning("Invalid configuration - using defaults")

        except Exception as e:
            logging.warning(f"Configuration error: {e}")

        return self.get_default_config()

    def get_default_config(self) -> Dict[str, Any]:
        """Enhanced default configuration."""
        return {
            "rom_extensions": list(get_all_rom_extensions())[:30],
            "unwanted_patterns": [
                r"\b(japan|jp)\b", r"\b(demo)\b", r"\b(beta)\b",
                r"\b(hack)\b", r"\b(prototype|proto)\b", r"\b(sample)\b"
            ],
            "region_priorities": {
                "World": 10, "Europe": 9, "USA": 8, "Germany": 7,
                "France": 6, "Spain": 5, "Italy": 4, "Japan": 3, "Other": 1
            },
            "console_sorting": {
                "enabled": True,
                "create_console_folders": True,
                "sort_within_console": True
            },
            "performance": {
                "enable_caching": True,
                "cache_size": 5000,
                "parallel_workers": min(os.cpu_count() or 4, 12),
                "batch_size": 300,
                "memory_limit_mb": 1024,
                "use_work_stealing": True,
                "io_timeout": 30.0
            }
        }

    def setup_logging(self):
        """Enhanced logging with performance tracking."""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'

        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        handlers = [
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                logs_dir / f'rom_sorter_{datetime.now():%Y%m%d}.log',
                encoding='utf-8'
            )
        ]

        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=handlers,
            force=True
        )

    def sort_by_console_advanced(self, source_dir: str, dest_dir: str) -> Dict[str, Any]:
        """Advanced console-based sorting with refactored architecture."""
        logging.info("="*100)
        logging.info("STARTING REFACTORED CONSOLE SORTING v2.1.5")
        logging.info("="*100)
        logging.info(f"Source: {source_dir}")
        logging.info(f"Destination: {dest_dir}")

        self.stats = ProcessingStatistics()
        self.performance_monitor.start_monitoring()

        try:
# Enhanced Validation Using File Operations Manager
            self._validate_directories(source_dir, dest_dir)

# Phase 1: Enhanced Rome Scanning
            rom_files = self._scan_rom_files(source_dir)
            if not rom_files:
                logging.warning("No ROM files found!")
                return self._get_final_stats()

# Phase 2: Console Analysis Using focused analyzer
            console_stats = self.console_analyzer.analyze_files(rom_files)

# Phase 3: Enhanced Duplicate Detection Using Focused Detector
            if self.options.detect_duplicates:
                rom_files = self.duplicate_detector.detect_and_filter_duplicates(rom_files)

# Phase 4: Optimized Sorting
            if not self.options.dry_run:
                self._perform_sorting(rom_files, dest_dir)
            else:
                logging.info("DRY-RUN mode - no files will be moved")
                self._simulate_sorting(rom_files, dest_dir)

# Phase 5: Enhanced Statistics
            self.stats.end_time = datetime.now()
            final_stats = self._get_final_stats()

            self._print_comprehensive_report(final_stats, console_stats)

            return final_stats

        except KeyboardInterrupt:
            logging.warning("Sorting cancelled by user")
            self.stats.errors += 1
            raise
        except Exception as e:
            logging.error(f"Sorting error: {e}", exc_info=True)
            self.stats.errors += 1
            raise
        finally:
            self._cleanup_resources()

    def _validate_directories(self, source_dir: str, dest_dir: str):
        """Enhanced directory validation using file operations manager."""
        try:
# Validate Source Directory-Direct Path use to avoid import problems
            source_path = Path(source_dir).resolve()
            if not source_path.exists():
                raise FileNotFoundError(f"Source directory not found: {source_path}")

            if not source_path.is_dir():
                raise ValueError(f"Source path is not a directory: {source_path}")

# Validate Destination Directory
            dest_path = Path(dest_dir).resolve()
            self.file_ops.ensure_directory_exists(dest_path)

            logging.info("Enhanced directory validation completed")

        except Exception as e:
            logging.error(f"Directory validation failed: {e}")
            raise

    def _scan_rom_files(self, source_dir: str) -> List[Dict[str, Any]]:
        """Scan ROM files with enhanced security validation and structured logging."""
        rom_files = []

        with log_operation_context("scan_rom_files", {'source_dir': source_dir}) as op_id:
            # Load allowed file extensions from configuration
            try:
                rom_extensions = set(get_all_rom_extensions())
                if not rom_extensions:
                    logger.warning("No ROM extensions defined in configuration - using standard extensions")
                    rom_extensions = {'.rom', '.zip', '.7z', '.rar', '.iso', '.bin', '.smc', '.n64', '.z64', '.nes', '.gba', '.gb', '.gbc'}
            except Exception as e:
                raise ConfigurationError("Error loading ROM extensions",
                                        error_code="CONFIG_EXTENSIONS_ERROR",
                                        details={'error': str(e)})

            logger.info(f"Searching for ROMs with {len(rom_extensions)} supported file extensions")

# Path Validation with Improved Security
            try:
                source_path = Path(source_dir).resolve()
                logger.debug(f"Validated source path: {source_path}")
            except Exception as e:
                raise FileOperationError(f"Invalid source path: {e}", file_path=source_dir, operation="validate")

# Import Optimized Module
            from src.detectors.console_detector import ConsoleDetector, CACHE_SIZE
            from src.scanning.optimized_scanner import OptimizedFileScanner

# Singleton instance for optimized processing
            console_detector = ConsoleDetector()

# Start Optimized File Scan
            start_time = time.time()
            logger.info(f"Starting optimized ROM scan in {source_path}")
            scanner = OptimizedFileScanner(extensions=rom_extensions)

            # Use the high-performance optimized scanner
            found_paths = scanner.scan_directory(
                str(source_path),
                progress_callback=lambda progress, msg: logger.debug(f"Scan progress: {progress:.1f}% - {msg}")
                                   if progress % 10 == 0 else None
            )

            # Get statistics from the scanner
            hidden_dirs_skipped = scanner.stats.get('hidden_dirs_skipped', 0)
            hidden_files_skipped = scanner.stats.get('hidden_files_skipped', 0)
            unsupported_files_skipped = scanner.stats.get('unsupported_files_skipped', 0)
            dirs_processed = scanner.stats.get('dirs_processed', 0)

            logger.info(f"Optimized scan completed: {len(found_paths)} potential ROM files found in {dirs_processed} directories")

# Extract Rome Information with Optimized Batching Strategy
            batch_size = 100  # Optimal batch size for ROM processing
            current_batch = []

# Process All Found Rome Files
            for i, file_path in enumerate(found_paths):
# Progress Indicator for Large File Sets
                if i % 1000 == 0 and i > 0:
                    elapsed = time.time() - start_time
                    files_per_sec = i / max(0.001, elapsed)
                    logger.info(f"Progress: {i}/{len(found_paths)} files processed in {elapsed:.2f}s ({files_per_sec:.1f} files/sec)")

# Security Validation for Each File
                try:
                    validated_file_path = Path(file_path) if isinstance(file_path, str) else file_path

# Batch Processing for optimal performance
                    current_batch.append(validated_file_path)
                    if len(current_batch) >= batch_size:
# Process Current Batch
                        console_detector.process_batch(current_batch)
                        current_batch = []
                    file_size = validated_file_path.stat().st_size
                    self.stats.total_bytes_processed += file_size

                    # Extract file information
                    filename = validated_file_path.name
                    file_ext = validated_file_path.suffix.lower()

# Extended ROM information recording
                    rom_info = {
                        'path': str(validated_file_path),
                        'filename': filename,
                        'size': file_size,
                        'extension': file_ext.lstrip('.'),
                        'relative_path': os.path.relpath(validated_file_path, source_path),
                        'last_modified': datetime.fromtimestamp(validated_file_path.stat().st_mtime).isoformat()
                    }

# Console detection with improved error treatment and performance measurement
                    with log_operation_context("console_detection", {
                        'file': filename,
                        'path': str(validated_file_path),
                        'operation_id': op_id
                    }):
                        try:
# Improved Console Detection with Optimized Cache
                            detection_result = console_detector.detect_console(filename, str(validated_file_path))
                            console = detection_result.console
                            confidence = detection_result.confidence

# Detailed Log Information with Optimized Threshold Values
                            if confidence < 0.3:
# Reduced Logging Frequency for Low Confidence
                                if self.stats.files_processed % 10 == 0:  # Log only every 10th file
                                    logger.warning(f"Low detection confidence for {filename}: {confidence:.2f}, detected as {console}")
                            elif confidence < 0.6:
                                if self.stats.files_processed % 5 == 0:  # Log only every 5th file
                                    logger.info(f"Medium detection confidence for {filename}: {confidence:.2f}, detected as {console}")
                            else:
                                if logger.isEnabledFor(logging.DEBUG):  # Log only when debug is enabled
                                    logger.debug(f"High detection confidence for {filename}: {confidence:.2f}, detected as {console}")

                        except Exception as e:
                            logger.error(f"Console detection failed for {filename}: {e}")
                            console = "unknown"
                            confidence = 0.0
                            # Detailed error capturing
                            if not isinstance(e, ConsoleDetectionError):
                                # Wrap the error for uniform handling
                                e = ConsoleDetectionError(
                                    f"Error during console detection: {str(e)}",
                                    rom_path=str(validated_file_path),
                                    details={'original_error': str(e), 'error_type': type(e).__name__}
                                )

                    rom_info['console'] = console
                    rom_info['confidence'] = confidence

                    rom_files.append(rom_info)
                    self.stats.files_processed += 1

                    # Adaptive memory usage optimization
                    if self.stats.files_processed % 1000 == 0:
# IMPROVED GC Strategy With Two Tiers
                        if self.stats.files_processed % 5000 == 0:
                            # Intensive memory optimization every 5000 files
                            gc.collect(generation=2)
                            logger.debug(f"Complete memory cleanup after {self.stats.files_processed} files")
                        else:
# Light Memory Optimization Every 1000 Files
                            gc.collect(generation=0)

# Remove Old Cache Entries with Large File Volumes
                        if hasattr(console_detector, '_in_memory_cache') and len(console_detector._in_memory_cache) > CACHE_SIZE:
# Remove the Oldest 20% of Cache Entries
                            cache_keys = list(console_detector._in_memory_cache.keys())
                            entries_to_remove = len(cache_keys) // 5
                            for key in cache_keys[:entries_to_remove]:
                                del console_detector._in_memory_cache[key]

                            logger.debug(f"Cache optimization: {entries_to_remove} old entries removed")

                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    self.stats.errors += 1

# Processed remaining batch
            if current_batch:
                console_detector.process_batch(current_batch)

            # Calculate performance metrics
            scan_duration = time.time() - start_time
            files_per_second = self.stats.files_processed / max(scan_duration, 0.001)

# Extended Cache Statistics
            cache_stats = getattr(console_detector, '_performance_stats', {})

# Summary Logging Information with Performance Data
            logger.info(f"ROM scan completed: {len(rom_files)} ROMs found, "
                        f"{hidden_dirs_skipped} hidden directories skipped, "
                        f"{hidden_files_skipped} hidden files skipped, "
                        f"{unsupported_files_skipped} unsupported files skipped, "
                        f"Performance: {files_per_second:.1f} files/sec, Duration: {scan_duration:.1f}s")

# Detailed Performance Metrics in Debug Level
            if logger.isEnabledFor(logging.DEBUG):
                cache_hit_rate = cache_stats.get('cache_hits', 0) / max(cache_stats.get('cache_hits', 0) + cache_stats.get('cache_misses', 1), 1) * 100
                logger.debug(f"Performance metrics: Dirs: {dirs_processed}, "
                            f"Cache hit rate: {cache_hit_rate:.1f}%, "
                            f"Batch hits: {cache_stats.get('batch_hits', 0)}, "
                            f"Memory usage: {gc.get_stats()}")

# Warning for Empty Results
            if len(rom_files) == 0:
                if unsupported_files_skipped > 0:
                    logger.warning(f"No supported ROM files found, but {unsupported_files_skipped} "
                                  f"unsupported files skipped. Check ROM extensions in configuration.")
                else:
                    logger.warning("No ROM files found in source directory.")

            return rom_files

    def _perform_sorting(self, rom_files: List[Dict[str, Any]], dest_dir: str):
        """Perform sorting using file operations manager."""
        with self._managed_worker_pool() as executor:
            futures = []

            for rom_file in rom_files:
                if self._shutdown_event.is_set():
                    break

                future = executor.submit(self._process_single_file, rom_file, dest_dir)
                futures.append(future)

            for future in as_completed(futures):
                try:
                    result = future.result(timeout=self.options.io_timeout)
                    if result:
                        if result['action'] == 'moved':
                            self.stats.files_moved += 1
                        elif result['action'] == 'copied':
                            self.stats.files_copied += 1
                        elif result['action'] == 'skipped':
                            self.stats.files_skipped += 1
                except Exception as e:
                    logging.error(f"File processing error: {e}")
                    self.stats.files_failed += 1

    def _process_single_file(self, rom_file: Dict[str, Any], dest_dir: str) -> Dict[str, str]:
        """Process a single ROM file using file operations manager."""
        try:
            console = rom_file.get('console', 'Unknown')
            source_path = rom_file['path']

# Ensure Console Directory Exists
            dest_dir_path = Path(dest_dir)
            console_dir = dest_dir_path / console
            self.file_ops.ensure_directory_exists(console_dir)

# Determine Destination Path
            dest_path = console_dir / rom_file['filename']

# Check IF File Already Exists
            if dest_path.exists() and self.options.skip_existing:
                return {'action': 'skipped', 'reason': 'already_exists'}

# Move Or Copy File Using File Operations Manager
            if self.options.create_backup:
                success = self.file_ops.safe_copy_file(source_path, dest_path)
                action = 'copied'
            else:
                success = self.file_ops.safe_move_file(source_path, dest_path)
                action = 'moved'

            if success:
                self.stats.io_operations += 1
                return {'action': action, 'source': source_path, 'dest': str(dest_path)}
            else:
                return {'action': 'failed', 'reason': 'io_error'}

        except Exception as e:
            logging.error(f"Error processing {rom_file.get('path', 'unknown')}: {e}")
            return {'action': 'failed', 'reason': str(e)}

    @contextmanager
    def _managed_worker_pool(self, max_workers: Optional[int] = None):
        """Enhanced worker pool with work-stealing queue."""
        if max_workers is None:
            max_workers = self.options.max_workers or min(os.cpu_count() or 4, 8)

        if self.options.use_work_stealing:
            self._work_queue = WorkStealingQueue(max_workers)

        self._worker_pool = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="ROMSorter"
        )
        self.stats.peak_workers = max_workers

        try:
            logging.info(f"Enhanced thread pool started with {max_workers} workers")
            yield self._worker_pool
        finally:
            self._worker_pool.shutdown(wait=True)
            self._worker_pool = None
            if self._work_queue:
                stats = self._work_queue.get_stats()
                logging.info(f"Work-stealing stats: {stats}")
                self._work_queue = None

    def _simulate_sorting(self, rom_files: List[Dict[str, Any]], dest_dir: str):
        """Simulate sorting with detailed reporting."""
        simulation_stats = defaultdict(int)

        for rom_file in rom_files:
            console = rom_file.get('console', 'Unknown')
            dest_dir_path = Path(dest_dir)
            console_dir = dest_dir_path / console
            dest_path = console_dir / rom_file['filename']

            if dest_path.exists():
                simulation_stats['would_skip'] += 1
            else:
                simulation_stats['would_process'] += 1

        logging.info(f"DRY-RUN Results: {dict(simulation_stats)}")
        self.stats.files_processed = simulation_stats['would_process']
        self.stats.files_skipped = simulation_stats['would_skip']

    def _get_final_stats(self) -> Dict[str, Any]:
        """Get comprehensive final statistics."""
        memory_stats = self.memory_manager.get_stats()

        return {
            'files_processed': self.stats.files_processed,
            'files_moved': self.stats.files_moved,
            'files_copied': self.stats.files_copied,
            'files_skipped': self.stats.files_skipped,
            'files_failed': self.stats.files_failed,
            'duplicates_found': self.stats.duplicates_found,
            'consoles_detected': self.stats.consoles_detected,
            'errors': self.stats.errors,
            'duration_seconds': self.stats.duration,
            'files_per_second': self.stats.files_per_second,
            'cache_hit_rate': self.stats.cache_hit_rate,
            'success_rate': self.stats.success_rate,
            'throughput_mbps': self.stats.throughput_mbps,
            'memory_peak_mb': memory_stats.get('peak', 0),
            'gc_collections': memory_stats.get('collections', 0),
            'total_bytes_processed': self.stats.total_bytes_processed,
            'io_operations': self.stats.io_operations
        }

    def _print_comprehensive_report(self, final_stats: Dict[str, Any], console_stats: Dict[str, Any]):
        """Print comprehensive processing report."""
        logging.info("="*100)
        logging.info("COMPREHENSIVE PROCESSING REPORT")
        logging.info("="*100)

# Summary Statistics
        logging.info(f"Total files processed: {final_stats['files_processed']}")
        logging.info(f"Files moved: {final_stats['files_moved']}")
        logging.info(f"Files copied: {final_stats['files_copied']}")
        logging.info(f"Files skipped: {final_stats['files_skipped']}")
        logging.info(f"Files failed: {final_stats['files_failed']}")

# Performance Metrics
        logging.info(f"Duration: {final_stats['duration_seconds']:.2f} seconds")
        logging.info(f"Processing rate: {final_stats['files_per_second']:.2f} files/sec")
        logging.info(f"Success rate: {final_stats['success_rate']:.1f}%")

        # Console breakdown
        logging.info("\nConsole breakdown:")
        for console, stats in console_stats.items():
            logging.info(f"  {console}: {stats['count']} files ({stats['total_size_mb']:.1f} MB)")

    def _cleanup_resources(self):
        """Enhanced resource cleanup."""
        try:
# Close All Database Connections
            try:
                from src.database.connection_pool import DatabaseConnectionPool
# Close All Connections in the pool
                pool = DatabaseConnectionPool.get_instance()
                pool.close_all()
                logging.debug("All database connections closed")
            except Exception as db_error:
                logging.warning(f"Error closing database connections: {db_error}")

# Close Any Open File Handles
            for handle in list(self._file_handles):
                try:
                    if hasattr(handle, 'close'):
                        handle.close()
                except:
                    pass

# Clear Caches
            if hasattr(self, '_config_cache'):
                self._config_cache.clear()

# Force Garbage Collection
            collected = gc.collect()
            logging.debug(f"Final cleanup: collected {collected} objects")

            # Stop performance monitoring
            try:
                self.performance_monitor.stop_monitoring()
            except:
                pass

            logging.info("Enhanced resource cleanup completed")

        except Exception as e:
            logging.error(f"Cleanup error: {e}")


# Compatibility alias for Backward Compatibility
OptimizedROMSorterPro = RefactoredROMSorterPro  # Main alias
AdvancedROMSorterPro = RefactoredROMSorterPro   # Legacy alias
SortingOptions = ProcessingOptions              # Legacy alias
EnhancedSortingOptions = ProcessingOptions     # Legacy alias
ProcessingStats = ProcessingStatistics         # Legacy alias
EnhancedProcessingStats = ProcessingStatistics # Legacy alias


# =====================================================================================================
# Cli Interface
# =====================================================================================================

def create_argument_parser():
    """Create argument parser for command line interface."""
    parser = argparse.ArgumentParser(
        description='ROM Sorter Pro v2.1.5 - Refactored ROM Organization Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --source ~/ROMs --dest ~/Organized_ROMs
  %(prog)s --source ~/ROMs --dest ~/Organized_ROMs --dry-run
  %(prog)s --source ~/ROMs --dest ~/Organized_ROMs --config custom.json
        '''
    )

    parser.add_argument('--source', '-s', required=False,
                        help='Source directory containing ROM files')
    parser.add_argument('--dest', '-d', required=False,
                        help='Destination directory for organized ROMs')
    parser.add_argument('--config', '-c', default='src/config.json',
                        help='Configuration file path (default: src/config.json)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simulate sorting without moving files')
    parser.add_argument('--gui', action='store_true',
                        help='Launch GUI interface')
    parser.add_argument('--web', action='store_true',
                        help='Launch web interface')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--workers', type=int, default=None,
                        help='Number of worker threads (default: auto)')
    parser.add_argument('--batch-size', type=int, default=300,
                        help='Batch size for processing (default: 300)')

    return parser


def handle_exception(exc: Exception) -> int:
    """Central exception handler for uniform error handling.

    Args:
        exc: The exception to catch

    Returns:
        Exit code for the program (0 = success, 1 = error)
    """
    if isinstance(exc, KeyboardInterrupt):
        logger.warning("Program aborted by user (CTRL+C)")
        print("\nProgram was aborted by user.")
        return 1

    if isinstance(exc, ConfigurationError):
        logger.error(f"Configuration error: {exc}", exc_info=True)
        print(f"Configuration error: {exc}")
        if hasattr(exc, 'details') and exc.details:
            print(f"Details: {exc.details}")
        return 1

    if isinstance(exc, ValidationError):
        logger.error(f"Validation error: {exc}", exc_info=True)
        print(f"Validation error: {exc}")
        return 1

    if isinstance(exc, ProcessingError):
        logger.error(f"Processing error: {exc}", exc_info=True)
        print(f"Error during ROM processing: {exc}")
        if hasattr(exc, 'rom_path') and exc.details.get('rom_path'):
            print(f"Affected file: {exc.details['rom_path']}")
        return 1

# General Error Case
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    print(f"An unexpected error occurred: {exc}")
    return 1


def main():
    """Main entry point for ROM Sorter Pro."""
    try:
        parser = create_argument_parser()
        args = parser.parse_args()

# Configure Logging Level
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.info("Verbose logging mode activated")

# Create Processing options with validation
        try:
            options = ProcessingOptions(
                dry_run=args.dry_run,
                max_workers=args.workers,
                batch_size=args.batch_size
            )
            if options.dry_run:
                logger.info("Test mode (Dry-Run) activated - no files will be changed")
        except ValidationError as ve:
            logger.error(f"Invalid processing options: {ve}")
            print(f"Fehler: {ve}")
            return 1

# Launch Appropriate Interface
        if args.gui:
            if GUI_AVAILABLE:
                try:
                    if UI_MODE == "new":
# Use the new modular ui
                        from src.ui.compat import launch_gui
                        logger.info("Starting modular GUI...")
                        launch_gui()
                    elif UI_MODE == "legacy":
# Use the old gui
                        from src.ui.gui import launch_gui
                        logger.info("Starting legacy GUI...")
                        launch_gui()
                    else:
# Direct import Attempts as Fallback
                        try:
                            from src.ui import main as ui_main
                            logger.info("Starting GUI (direct import)...")
                            ui_main()
                        except ImportError:
                            from src.ui.gui import launch_gui
                            logger.info("Starting legacy GUI (direct import)...")
                            launch_gui()
                except ImportError as e:
                    logger.error(f"GUI could not be imported: {e}")
                    print("GUI not available. Please install the required dependencies.")
                    return 1
            else:
                logger.error("GUI not available")
                print("GUI not available. Please install the required dependencies.")
                return 1
        elif args.web:
            if WEB_INTERFACE_AVAILABLE:
                try:
                    from web_interface import run_web_interface
                    logger.info("Starting web interface...")
                    run_web_interface()
                except ImportError as e:
                    logger.error(f"Web interface could not be imported: {e}")
                    print("Web interface not available. Please install Flask and required dependencies.")
                    return 1
            else:
                logger.error("Web interface not available")
                print("Web interface not available. Please install Flask and required dependencies.")
                return 1
        else:
# Command Line Interface
            logger.info(f"Command line mode: Sorting from '{args.source}' to '{args.dest}'")
            sorter = RefactoredROMSorterPro(args.config, options)
            result = sorter.sort_by_console_advanced(args.source, args.dest)

# Detailed Success or Error Messages
            if result.get('errors', 0) > 0:
                logger.error(f"Sorting completed with {result.get('errors', 0)} errors")
                print(f"Sorting completed with {result.get('errors', 0)} errors.")
                return 1
            else:
                logger.info(f"Sorting successfully completed: {result.get('processed', 0)} ROMs processed")
                print(f"Sorting successful: {result.get('processed', 0)} ROMs processed.")

        return 0

    except Exception as e:
        return handle_exception(e)


def memory_optimized_batch_process_roms(
    directory: str,
    batch_size: int = 200,
    max_memory_mb: int = 512,
    extensions: Optional[List[str]] = None
) -> Iterator[Dict[str, Any]]:
    """Process ROMs in batches with optimized memory usage.

    This memory-optimized version uses:
    1. A generator to process ROMs incrementally and minimize memory
       consumption
    2. Dynamic memory management for large collections
    3. Adaptive batch size based on available memory
    4. Automatic cleanup after each batch

    Args:
        directory (str): The directory to scan
        batch_size (int): Maximum number of ROMs per batch (dynamically
            adjusted)
        max_memory_mb (int): Maximum RAM to use in megabytes
        extensions (List[str], optional): List of file extensions to look for

    Returns:
        Iterator[Dict[str, Any]]: A generator with ROM information
    """
    msg = f"Starting memory-optimized batch processing of ROMs in {directory}"
    logging.info(msg)

# Use all Known Rome Extensions by Default
    if extensions is None:
        try:
            # We already imported get_all_rom_extensions at the top of the file
# So just use it directly
            ext_set = get_all_rom_extensions()
            extensions = list(ext_set) if ext_set else []
        except (ImportError, AttributeError):
# Fallback to a List of Common Extensions
            extensions = [
                ".rom", ".bin", ".iso", ".cue", ".chd", ".gba",
                ".nes", ".smc", ".z64", ".n64", ".v64", ".smd",
                ".md", ".gb", ".gbc", ".sfc", ".wsc", ".ngc"
            ]

# Memory Manager for Monitoring and Optimizing Memory Usage
    memory_manager = MemoryManager(max_memory_mb=max_memory_mb)

# Statistics for Logging
    stats = {
        "processed_files": 0,
        "detected_roms": 0,
        "batches_processed": 0,
        "start_time": time.time()
    }

    try:
# Traverse Directory and Find Rome Files
        def find_rom_files():
            for root, _, files in os.walk(directory):
                for file in files:
# Check If File Has a Known Rome Extension
                    file_lower = file.lower()
                    if any(file_lower.endswith(ext.lower())
                           for ext in extensions):
                        yield os.path.join(root, file)

# Monitor Memory Usage and Adjust Dynamically
                    memory_manager.check_memory_usage()

# Generator for Rome Files
        rom_files = find_rom_files()

        current_batch = []
        # Start with conservative value
        current_batch_size = min(batch_size, 100)

        for rom_file in rom_files:
            stats["processed_files"] += 1
            current_batch.append(rom_file)

# Process Batch When Batch Size is Reached
            if len(current_batch) >= current_batch_size:
# Process the Current Batch
# Process the Batch and Yield Results
                for rom_info in _process_rom_batch(
                    current_batch, memory_manager
                ):
                    stats["detected_roms"] += 1
                    yield rom_info

                # Update statistics for this batch
                stats["batches_processed"] += 1
                current_batch = []

# Dynamically Adjust Batch Size Based on Memory Pressure
                memory_pressure = memory_manager.memory_pressure
                if memory_pressure > 0.8:
# Reduce Batch Size When Memory Pressure is high
                    current_batch_size = max(10, int(current_batch_size * 0.7))
                    logging.info(
                        f"High memory pressure ({memory_pressure:.2f}): "
                        f"Batch size reduced to {current_batch_size}"
                    )
                elif memory_pressure < 0.3 and current_batch_size < batch_size:
# Increase Batch size when memory pressure is low
                    new_size = int(current_batch_size * 1.3)
                    current_batch_size = min(batch_size, new_size)
                    logging.info(
                        f"Low memory pressure ({memory_pressure:.2f}): "
                        f"Batch size increased to {current_batch_size}"
                    )

# Reduce Memory Pressure After Each Batch
                memory_manager.reduce_memory_pressure(target_pressure=0.5)

        # Process remaining files
        if current_batch:
            for rom_info in _process_rom_batch(current_batch, memory_manager):
                stats["detected_roms"] += 1
                yield rom_info
            stats["batches_processed"] += 1

# Log Final Statistics
        elapsed = time.time() - stats["start_time"]
        memory_stats = memory_manager.get_stats()
        logging.info(
            f"Batch processing completed: {stats['detected_roms']} ROMs in "
            f"{stats['batches_processed']} batches processed. "
            f"Duration: {elapsed:.1f}s, Peak: {memory_stats['peak']:.1f}MB"
        )

    except Exception as e:
        logging.error(f"Error during batch processing: {e}")
        raise


def _process_rom_batch(
    rom_files: List[str],
    memory_manager: MemoryManager
) -> Iterator[Dict[str, Any]]:
    """Processes a single batch of ROM files.

    This function is called by memory_optimized_batch_process_roms.
    """
    for rom_file in rom_files:
        try:
# Perform Rome Detection and Data Extraction
            # Normally we would call detect_console and other functions here
            # In this simplified version, we return basic information
            rom_name = os.path.basename(rom_file)
            file_size = os.path.getsize(rom_file)
            file_extension = os.path.splitext(rom_file)[1].lower()

# Create Basic Rome Info
            rom_info = {
                "path": rom_file,
                "name": rom_name,
                "size": file_size,
                "extension": file_extension,
# We would add more information here, search as detected console,
# Metadata, etc., Depending on Available Functions
            }

# Try to Detect the Console if the Function is Available
            try:
                from .detectors.ml_detector_fixed import detect_console_with_ml
                console_name, confidence = detect_console_with_ml(rom_file)
                if console_name:
                    rom_info["console"] = console_name
                    rom_info["detection_confidence"] = confidence
            except ImportError:
                pass

# Monitor Memory Usage
            memory_manager.check_memory_usage()

            yield rom_info

        except Exception as e:
            logging.error(f"Error processing ROM {rom_file}: {e}")
# Continue Despite Error and Skip The Problematic Rome
            continue


# Export the New Function as The Standard Batch Processing Function
batch_process_roms = memory_optimized_batch_process_roms

if __name__ == "__main__":
    sys.exit(main())
