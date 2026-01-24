#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rome Sarter Pro - Optimized Performance Monitoring Modules This File is a Consolidated version of the Performance Monitoring Tools. It combes the functionality from SRC/Core/Performance.py and SRC/Utils/Performance.py for Better Maintenance and Reduced Redundancy. Improved Features: - Optimized Memory Usage - Improved Thread Security - Extended Metracking - Uniform API for All Components - Automatic Resource APPROVAL"""

import time
import threading
import functools
import gc
import logging
import sys
from typing import Dict, Any, Optional, Callable, TypeVar
from collections import defaultdict, deque
from datetime import datetime
from contextlib import contextmanager

# Type definitions for generics
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

# Optional: Use psutil for extended system metrics if available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


def measure_time(func=None, name=None, log_level=logging.DEBUG):
    """Optimized Decorator for Measuring the Execution Time of a Function. ARGS: Func: The Function to Be Decorated Name: Optional Name for Logging (Standard: Function Name) Log_level: The Log Level for Time Measurement Return: The Decorated Function"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            operation_name = name or func.__name__
            start_time = time.perf_counter()  # More precise time measurement
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                duration = end_time - start_time
                logger.log(log_level, f"Operation '{operation_name}' dauerte {duration:.4f} Sekunden")
                
                # Optional: Send to performance monitor if available
                try:
                    monitor = PerformanceMonitor.get_instance()
                    monitor.record_operation_time(operation_name, duration)
                except (NameError, AttributeError):
                    pass  # Not available monitor, ignore
        return wrapper

    # Enables use with or without arguments
    if func is None:
        return decorator
    return decorator(func)


class PerformanceMetric:
    """Saving power metrics for surgery."""

    def __init__(self, name: str, max_samples: int = 100):
        """Initialized a new metricist. ARGS: Name: Name of the Metrik Max_samples: Maximum number to be saved"""
        self.name = name
        self.max_samples = max_samples
        self.durations = deque(maxlen=max_samples)
        self.start_times = {}
        self.lock = threading.RLock()

        # Spezielle Tracking-Variablen
        self.last_duration = 0.0
        self.total_duration = 0.0
        self.count = 0
        self.failed = 0
        self._min = float('inf')
        self._max = float('-inf')

        # Multi-Phase-Metriken
        self.phase_durations = defaultdict(float)
        self.current_phase = None

    def start(self, key: Optional[Any] = None) -> float:
        """Starts the time measurement. Args: Key: Optional key for several parallel measurements Return: Current time as start time"""
        key = key if key is not None else 'default'
        with self.lock:
            start_time = time.perf_counter()
            self.start_times[key] = start_time
            return start_time

    def stop(self, key: Optional[Any] = None, success: bool = True) -> float:
        """Stop the time measurement and save the duration. Args: Key: Key of the measurement started Success: whether the operation was successful Return: Duration in seconds Raises: Keyerror: If there is no start for the specified key"""
        key = key if key is not None else 'default'
        with self.lock:
            if key not in self.start_times:
                raise KeyError(f"Kein Start für Schlüssel '{key}' gefunden")

            end_time = time.perf_counter()
            start_time = self.start_times.pop(key)
            duration = end_time - start_time

            self.durations.append(duration)
            self.last_duration = duration
            self.total_duration += duration
            self.count += 1

            if not success:
                self.failed += 1

            # Aktualisiere Min/Max
            if duration < self._min:
                self._min = duration
            if duration > self._max:
                self._max = duration

            return duration


class PerformanceMonitor:
    """Optimized and consolidated performance monitor for Rome Sorter Pro. Singleton implementation for easy access from all components."""

    _instance = None
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls):
        """Gives back the monitor's singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = PerformanceMonitor()
            return cls._instance

    def __init__(self):
        """Initialisiert den Leistungsmonitor."""
        self.metrics = {}
        self.operation_times = defaultdict(list)
        self.operation_counts = defaultdict(int)
        self.memory_snapshots = []
        self.peak_memory = 0
        self.start_time = time.perf_counter()
        self._lock = threading.RLock()
        
        # Memory-Monitoring starten
        self._last_memory_check = 0
        self._memory_check_interval = 5  # Sekunden
        
        # Speichermetriken initialisieren
        self._update_memory_usage()

    def record_operation_time(self, operation_name: str, duration: float) -> None:
        """Records the time of an operation. Args: Operation_Name: Name of the Operation Duration: Duration in seconds"""
        with self._lock:
            self.operation_times[operation_name].append(duration)
            self.operation_counts[operation_name] += 1
            
            # Update regular memory use
            current_time = time.perf_counter()
            if current_time - self._last_memory_check > self._memory_check_interval:
                self._update_memory_usage()
                self._last_memory_check = current_time

    def start_operation(self, operation_name: str) -> float:
        """The time measurement for an operation begins. Args: Operation_Name: Name of the Operation Return: Start time in seconds"""
        start_time = time.perf_counter()
        with self._lock:
            if operation_name not in self.metrics:
                self.metrics[operation_name] = PerformanceMetric(operation_name)
            self.metrics[operation_name].start()
        return start_time

    def end_operation(self, operation_name: str, start_time: float = None) -> float:
        """Ends the time measurement for an operation. Args: Operation_Name: Name of the Operation Start_Time: Optional, if not started via Start_Operation Return: Duration in seconds"""
        end_time = time.perf_counter()
        
        with self._lock:
            if operation_name in self.metrics:
                duration = self.metrics[operation_name].stop()
            elif start_time is not None:
                duration = end_time - start_time
                self.record_operation_time(operation_name, duration)
            else:
                raise ValueError(f"Operation '{operation_name}' wurde nicht gestartet")
                
        return duration

    def _update_memory_usage(self) -> Dict[str, Any]:
        """Updates the storage use statistics. Return: Save usage information"""
        memory_info = {}
        
        # Grundlegende Python-Speichernutzung
        memory_info['python_alloc'] = sys.getsizeof(0)  # Base for measurements
        
        # GC-Informationen sammeln
        gc.collect()  # Optional: Forcierter GC
        memory_info['gc_objects'] = len(gc.get_objects())
        
        # Use psutil for extended system information if available
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            mem_info = process.memory_info()
            memory_info['rss'] = mem_info.rss  # Resident Set Size
            memory_info['vms'] = mem_info.vms  # Virtual Memory Size
            
            # Aktuelle CPU-Nutzung
            memory_info['cpu_percent'] = process.cpu_percent(interval=0.1)
            
            # Setze Peak-Memory
            if mem_info.rss > self.peak_memory:
                self.peak_memory = mem_info.rss
        
        # Add snapshot with time stamps
        snapshot = {
            'timestamp': time.time(),
            'memory': memory_info
        }
        self.memory_snapshots.append(snapshot)
        
        # Limit the number of snapshots
        if len(self.memory_snapshots) > 1000:
            self.memory_snapshots = self.memory_snapshots[-1000:]
            
        return memory_info

    def get_summary(self) -> Dict[str, Any]:
        """A Summary of the Performance Metrics Returns. Return: Summary of All Performance Metrics"""
        with self._lock:
            total_runtime = time.perf_counter() - self.start_time
            
            # Operation-Statistiken berechnen
            operation_stats = {}
            for op_name, times in self.operation_times.items():
                if not times:
                    continue
                    
                operation_stats[op_name] = {
                    'count': self.operation_counts[op_name],
                    'total_time': sum(times),
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times)
                }
            
            # Memory-Statistiken
            memory_stats = {}
            if self.memory_snapshots:
                latest = self.memory_snapshots[-1]['memory']
                memory_stats = {
                    'current': latest,
                    'peak': {'rss': self.peak_memory} if PSUTIL_AVAILABLE else {}
                }
            
            return {
                'total_runtime': total_runtime,
                'operations': operation_stats,
                'memory': memory_stats,
                'timestamp': datetime.now().isoformat()
            }


@contextmanager
def measure_block(name: str, log_level: int = logging.DEBUG):
    """Context Managers for Measuring A Code Block. ARGS: Name: Name of the Block Log_Level: Log Level for the Output"""
    monitor = PerformanceMonitor.get_instance()
    start_time = monitor.start_operation(name)
    
    try:
        yield
    finally:
        duration = monitor.end_operation(name, start_time)
        logger.log(log_level, f"Block '{name}' ausgeführt in {duration:.4f} Sekunden")


# Alias for compatibility with old code
AdvancedPerformanceMonitor = PerformanceMonitor
