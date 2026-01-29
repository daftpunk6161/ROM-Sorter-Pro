"""Tests for Scanner LRU Cache implementation.

Tests cover:
- Cache hit/miss behavior
- LRU eviction when at capacity
- Thread-safe operations
- Cache statistics
- Configuration of max size
"""

import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock, patch

import pytest


def create_mock_config(scanner_overrides: dict | None = None) -> MagicMock:
    """Create a properly configured mock config for scanner tests.
    
    Args:
        scanner_overrides: Additional scanner config values to set.
        
    Returns:
        MagicMock config that returns sensible defaults.
    """
    mock_config = MagicMock()
    
    # Default scanner config - use 100 as minimum for cache_max_size
    # since the implementation enforces min=100
    scanner_cfg = {
        "cache_max_size": 100,
        "max_threads": 4,
        "chunk_size": 4 * 1024 * 1024,
        "ignore_images": True,
        "ignore_extensions": [],
    }
    if scanner_overrides:
        scanner_cfg.update(scanner_overrides)
    
    # Return different values based on the key
    def get_config(key, default=None):
        configs = {
            "scanner": scanner_cfg,
            "performance": {"processing": {"chunk_size": 4 * 1024 * 1024}},
            "cache_dir": str(Path(tempfile.gettempdir()) / "rom_sorter_test_cache"),
            "logs_dir": str(Path(tempfile.gettempdir()) / "rom_sorter_test_logs"),
        }
        return configs.get(key, default)
    
    mock_config.get.side_effect = get_config
    return mock_config


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def scanner():
    """Create a scanner instance with small cache for testing.
    
    Note: Cache minimum is 100, so we use 100 for tests.
    """
    from src.scanning.high_performance_scanner import HighPerformanceScanner
    
    mock_config = create_mock_config({"cache_max_size": 100})
    scanner = HighPerformanceScanner(config=mock_config)
    return scanner


@pytest.fixture
def temp_files(tmp_path: Path):
    """Create temporary test files."""
    files = []
    for i in range(10):
        f = tmp_path / f"test_{i}.rom"
        f.write_bytes(b"test content " * i + bytes([i]))
        files.append(f)
    return files


# =============================================================================
# Test: Basic Cache Operations
# =============================================================================

class TestBasicCacheOperations:
    """Tests for basic cache get/set operations."""
    
    def test_cache_save_and_retrieve(self, scanner, temp_files):
        """Saved entries should be retrievable."""
        test_file = temp_files[0]
        file_stat = test_file.stat()
        
        rom_info = {"name": "test.rom", "system": "NES"}
        scanner._save_to_cache(str(test_file), rom_info, file_stat)
        
        retrieved = scanner._get_from_cache(str(test_file), file_stat)
        
        assert retrieved is not None
        assert retrieved["name"] == "test.rom"
        assert retrieved["system"] == "NES"
    
    def test_cache_miss_returns_none(self, scanner, temp_files):
        """Cache miss should return None."""
        test_file = temp_files[0]
        file_stat = test_file.stat()
        
        retrieved = scanner._get_from_cache(str(test_file), file_stat)
        
        assert retrieved is None
    
    def test_cache_key_includes_mtime_and_size(self, scanner, temp_files):
        """Cache key should include file path, mtime, and size."""
        test_file = temp_files[0]
        file_stat = test_file.stat()
        
        key = scanner._make_cache_key(str(test_file), file_stat)
        
        assert len(key) == 3
        assert key[0] == str(test_file)
        assert key[1] == int(file_stat.st_mtime)
        assert key[2] == int(file_stat.st_size)
    
    def test_modified_file_cache_miss(self, scanner, temp_files):
        """Modified file (different mtime/size) should be a cache miss."""
        test_file = temp_files[0]
        
        # Save with original stat
        original_stat = test_file.stat()
        scanner._save_to_cache(str(test_file), {"system": "NES"}, original_stat)
        
        # Modify file
        time.sleep(0.01)  # Ensure different mtime
        test_file.write_bytes(b"new content with different size")
        
        new_stat = test_file.stat()
        retrieved = scanner._get_from_cache(str(test_file), new_stat)
        
        assert retrieved is None


# =============================================================================
# Test: LRU Eviction
# =============================================================================

class TestLRUEviction:
    """Tests for LRU (Least Recently Used) eviction."""
    
    def test_eviction_when_at_capacity(self, temp_files):
        """Oldest entries should be evicted when cache is full."""
        from src.scanning.high_performance_scanner import HighPerformanceScanner
        
        # Use cache_max_size=100 (minimum enforced by implementation)
        mock_config = create_mock_config({"cache_max_size": 100})
        scanner = HighPerformanceScanner(config=mock_config)
        
        # Fill cache with 100 entries
        for i in range(100):
            stat = temp_files[i % len(temp_files)].stat()
            # Use unique paths to avoid key collision
            fake_path = f"/fake/path/file_{i}.rom"
            class FakeStat:
                def __init__(self, idx):
                    self.st_mtime = float(idx)
                    self.st_size = 1000 + idx
            scanner._save_to_cache(fake_path, {"id": i}, FakeStat(i))
        
        # Verify cache is full
        stats = scanner.get_cache_stats()
        assert stats["size"] == 100
        
        # Add 101st entry - should evict first
        class FakeStat100:
            st_mtime = 100.0
            st_size = 1100

        scanner._save_to_cache("/fake/path/file_100.rom", {"id": 100}, FakeStat100())
        
        # First entry should be evicted (key with mtime=0)
        key0 = ("/fake/path/file_0.rom", 0, 1000)
        assert key0 not in scanner._cache
        
        # Size should still be 100
        stats = scanner.get_cache_stats()
        assert stats["size"] == 100
    
    def test_access_updates_recency(self, temp_files):
        """Accessing an entry should move it to most recently used."""
        from src.scanning.high_performance_scanner import HighPerformanceScanner
        
        mock_config = create_mock_config({"cache_max_size": 100})
        scanner = HighPerformanceScanner(config=mock_config)
        
        # Fill cache with 100 entries
        for i in range(100):
            class FakeStat:
                def __init__(self, idx):
                    self.st_mtime = float(idx)
                    self.st_size = 1000 + idx
            scanner._save_to_cache(f"/fake/file_{i}.rom", {"id": i}, FakeStat(i))
        
        # Access first entry (making it most recently used)
        class Stat0:
            st_mtime = 0.0
            st_size = 1000
        scanner._get_from_cache("/fake/file_0.rom", Stat0())
        
        # Add new entry - should evict second entry (now oldest)
        class Stat100:
            st_mtime = 100.0
            st_size = 1100
        scanner._save_to_cache("/fake/file_100.rom", {"id": 100}, Stat100())
        
        # First entry should still exist (was accessed, moved to end)
        result0 = scanner._get_from_cache("/fake/file_0.rom", Stat0())
        assert result0 is not None, "Entry 0 should exist (was accessed)"
        
        # Second entry should be evicted
        class Stat1:
            st_mtime = 1.0
            st_size = 1001
        result1 = scanner._get_from_cache("/fake/file_1.rom", Stat1())
        assert result1 is None, "Entry 1 should be evicted (was oldest)"
    
    def test_update_existing_entry(self, temp_files):
        """Updating existing entry should not increase cache size."""
        from src.scanning.high_performance_scanner import HighPerformanceScanner
        
        mock_config = create_mock_config({"cache_max_size": 100})
        scanner = HighPerformanceScanner(config=mock_config)
        
        # Fill cache with some entries
        for i in range(50):
            stat = temp_files[i % len(temp_files)].stat()
            scanner._save_to_cache(str(temp_files[i % len(temp_files)]) + f"_{i}", {"id": i}, stat)
        
        initial_stats = scanner.get_cache_stats()
        initial_size = initial_stats["size"]
        
        # Update first entry (using same key)
        stat0 = temp_files[0].stat()
        scanner._save_to_cache(str(temp_files[0]) + "_0", {"id": 0, "updated": True}, stat0)
        
        # Size should be same
        final_stats = scanner.get_cache_stats()
        assert final_stats["size"] == initial_size
        
        # Updated value should be retrievable
        result = scanner._get_from_cache(str(temp_files[0]) + "_0", stat0)
        assert result is not None
        assert result.get("updated") is True


# =============================================================================
# Test: Cache Statistics
# =============================================================================

class TestCacheStatistics:
    """Tests for cache statistics tracking."""
    
    def test_hit_miss_tracking(self, scanner, temp_files):
        """Cache should track hits and misses."""
        test_file = temp_files[0]
        stat = test_file.stat()
        
        # Miss
        scanner._get_from_cache(str(test_file), stat)
        
        # Save
        scanner._save_to_cache(str(test_file), {"system": "NES"}, stat)
        
        # Hit
        scanner._get_from_cache(str(test_file), stat)
        scanner._get_from_cache(str(test_file), stat)
        
        stats = scanner.get_cache_stats()
        
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_ratio"] == pytest.approx(2/3)
    
    def test_cache_size_tracking(self, scanner, temp_files):
        """Cache size should be accurately reported."""
        stats = scanner.get_cache_stats()
        assert stats["size"] == 0
        
        for i in range(3):
            stat = temp_files[i].stat()
            scanner._save_to_cache(str(temp_files[i]), {"id": i}, stat)
        
        stats = scanner.get_cache_stats()
        assert stats["size"] == 3
        assert stats["max_size"] == 100  # Minimum enforced by implementation
    
    def test_clear_cache_resets_stats(self, scanner, temp_files):
        """Clearing cache should reset statistics."""
        # Add some entries and generate hits/misses
        for i in range(3):
            stat = temp_files[i].stat()
            scanner._save_to_cache(str(temp_files[i]), {"id": i}, stat)
            scanner._get_from_cache(str(temp_files[i]), stat)
        
        scanner.clear_cache()
        
        stats = scanner.get_cache_stats()
        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0


# =============================================================================
# Test: Thread Safety
# =============================================================================

class TestThreadSafety:
    """Tests for thread-safe cache operations."""
    
    def test_concurrent_reads_and_writes(self, scanner, temp_files):
        """Concurrent reads and writes should not cause errors."""
        errors = []
        
        def writer(file_idx):
            try:
                for _ in range(100):
                    stat = temp_files[file_idx % len(temp_files)].stat()
                    scanner._save_to_cache(
                        str(temp_files[file_idx % len(temp_files)]),
                        {"id": file_idx},
                        stat
                    )
            except Exception as e:
                errors.append(e)
        
        def reader(file_idx):
            try:
                for _ in range(100):
                    stat = temp_files[file_idx % len(temp_files)].stat()
                    scanner._get_from_cache(
                        str(temp_files[file_idx % len(temp_files)]),
                        stat
                    )
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            t1 = threading.Thread(target=writer, args=(i,))
            t2 = threading.Thread(target=reader, args=(i,))
            threads.extend([t1, t2])
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Thread errors: {errors}"
    
    def test_concurrent_eviction(self, scanner, temp_files):
        """Concurrent writes causing eviction should not corrupt cache."""
        errors = []
        
        def writer(start_idx):
            try:
                for i in range(50):
                    idx = (start_idx + i) % len(temp_files)
                    stat = temp_files[idx].stat()
                    scanner._save_to_cache(str(temp_files[idx]), {"id": idx}, stat)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        
        # Cache should respect max size
        stats = scanner.get_cache_stats()
        assert stats["size"] <= stats["max_size"]


# =============================================================================
# Test: Configuration
# =============================================================================

class TestCacheConfiguration:
    """Tests for cache configuration from config."""
    
    def test_default_cache_size(self):
        """Default cache size should be used when not configured."""
        from src.scanning.high_performance_scanner import (
            HighPerformanceScanner,
            DEFAULT_CACHE_MAX_SIZE,
        )
        
        mock_config = create_mock_config({"cache_max_size": None})
        scanner = HighPerformanceScanner(config=mock_config)
        
        assert scanner._cache_max_size == DEFAULT_CACHE_MAX_SIZE
    
    def test_custom_cache_size_from_config(self):
        """Custom cache size should be read from config."""
        from src.scanning.high_performance_scanner import HighPerformanceScanner
        
        mock_config = create_mock_config({"cache_max_size": 2000})
        scanner = HighPerformanceScanner(config=mock_config)
        
        assert scanner._cache_max_size == 2000
    
    def test_cache_size_bounds(self):
        """Cache size should be bounded to reasonable limits."""
        from src.scanning.high_performance_scanner import HighPerformanceScanner
        
        # Too small
        mock_config = create_mock_config({"cache_max_size": 10})  # Below minimum
        scanner = HighPerformanceScanner(config=mock_config)
        assert scanner._cache_max_size >= 100  # Minimum enforced
        
        # Too large
        mock_config2 = create_mock_config({"cache_max_size": 999999})  # Above maximum
        scanner2 = HighPerformanceScanner(config=mock_config2)
        assert scanner2._cache_max_size <= 100000  # Maximum enforced


# =============================================================================
# Test: Memory Bounds
# =============================================================================

class TestMemoryBounds:
    """Tests to verify cache does not grow unbounded."""
    
    def test_cache_never_exceeds_max_size(self, tmp_path):
        """Cache should never exceed configured max size."""
        from src.scanning.high_performance_scanner import HighPerformanceScanner
        
        mock_config = create_mock_config({"cache_max_size": 100})  # Min is 100
        scanner = HighPerformanceScanner(config=mock_config)
        
        # Add many more entries than max size
        for i in range(200):
            class FakeStat:
                def __init__(self, idx):
                    self.st_mtime = float(idx)
                    self.st_size = 1000 + idx
            scanner._save_to_cache(f"/fake/file_{i}.rom", {"id": i}, FakeStat(i))
            
            # Check size after each add
            stats = scanner.get_cache_stats()
            assert stats["size"] <= 100, f"Cache exceeded max at iteration {i}"
    
    def test_large_scan_simulation(self, tmp_path):
        """Simulate a large scan to verify memory is bounded."""
        from src.scanning.high_performance_scanner import HighPerformanceScanner
        
        mock_config = create_mock_config({"cache_max_size": 100})
        scanner = HighPerformanceScanner(config=mock_config)
        
        # Create and process 500 "files" (using fake stats)
        for i in range(500):
            fake_path = str(tmp_path / f"file_{i}.rom")
            # Create a mock stat result
            class FakeStat:
                st_mtime = float(i)
                st_size = 1000 + i
            
            scanner._save_to_cache(fake_path, {"id": i}, FakeStat())
        
        stats = scanner.get_cache_stats()
        assert stats["size"] == 100  # Should be exactly at max
        assert stats["max_size"] == 100
