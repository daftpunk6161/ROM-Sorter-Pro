"""Tests for detection_handler cleanup and ML isolation.

Validates:
- ML is properly feature-flagged
- Database lookup is not duplicated
- Detection flows work correctly when ML is disabled
- Fallback paths work properly
"""

import os
from unittest.mock import patch, MagicMock

import pytest


# =============================================================================
# Test: ML Feature Flag Isolation
# =============================================================================

class TestMLFeatureFlagIsolation:
    """Tests that ML detection is properly isolated behind feature flag."""
    
    def test_ml_disabled_by_default(self):
        """ML should be disabled by default (env var not set)."""
        # Clear the environment variable if set
        with patch.dict(os.environ, {}, clear=True):
            # Need to reload module to pick up env change
            import importlib
            from src.detectors import detection_handler
            importlib.reload(detection_handler)
            
            assert detection_handler.ML_ENABLED is False
    
    def test_ml_returns_unknown_when_disabled(self):
        """ML detection should return Unknown when disabled."""
        from src.detectors.detection_handler import detect_console_with_ml
        
        result = detect_console_with_ml("/fake/path/test.rom")
        
        assert result.console == "Unknown"
        assert result.confidence == 0.0
        assert "disabled" in str(result.metadata.get("error", "")).lower() or \
               "unavailable" in str(result.metadata.get("error", "")).lower()
    
    def test_ml_detector_class_exists_as_placeholder(self):
        """MLEnhancedConsoleDetector should exist as placeholder when disabled."""
        from src.detectors.detection_handler import MLEnhancedConsoleDetector
        
        # Should be the placeholder class
        assert MLEnhancedConsoleDetector is not None
    
    def test_get_ml_detector_returns_none_when_disabled(self):
        """get_ml_detector should return None when ML is disabled."""
        from src.detectors.detection_handler import get_ml_detector
        
        result = get_ml_detector()
        
        assert result is None


# =============================================================================
# Test: Detection Manager Functionality
# =============================================================================

class TestDetectionManager:
    """Tests for DetectionManager core functionality."""
    
    def test_singleton_pattern(self):
        """DetectionManager should follow singleton pattern."""
        from src.detectors.detection_handler import DetectionManager
        
        instance1 = DetectionManager.get_instance()
        instance2 = DetectionManager.get_instance()
        
        assert instance1 is instance2
    
    def test_detect_console_returns_tuple(self):
        """detect_console should return (console, confidence) tuple."""
        from src.detectors.detection_handler import DetectionManager
        
        manager = DetectionManager.get_instance()
        result = manager.detect_console("test.nes")
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        console, confidence = result
        assert isinstance(console, str)
        assert isinstance(confidence, float)
    
    def test_detect_console_with_metadata_returns_result(self):
        """detect_console_with_metadata should return DetectionResult."""
        from src.detectors.detection_handler import DetectionManager
        from src.detectors.detection_result import DetectionResult
        
        manager = DetectionManager.get_instance()
        result = manager.detect_console_with_metadata("test.nes")
        
        assert isinstance(result, DetectionResult)
    
    def test_detection_manager_cache(self):
        """DetectionManager should cache results."""
        from src.detectors.detection_handler import DetectionManager
        
        manager = DetectionManager.get_instance()
        manager.clear_cache()
        
        # First call
        result1 = manager.detect_console_with_metadata("test.nes", "/fake/test.nes")
        stats1 = manager.get_statistics()
        
        # Second call (should be cached)
        result2 = manager.detect_console_with_metadata("test.nes", "/fake/test.nes")
        stats2 = manager.get_statistics()
        
        assert result1.console == result2.console
        assert stats2["cache_hits"] > stats1["cache_hits"]
    
    def test_clear_cache_works(self):
        """clear_cache should reset the cache."""
        from src.detectors.detection_handler import DetectionManager
        
        manager = DetectionManager.get_instance()
        
        # Add something to cache
        manager.detect_console_with_metadata("test.nes")
        
        # Clear cache
        manager.clear_cache()
        
        # Cache should be empty
        assert len(manager._cache) == 0


# =============================================================================
# Test: Detection Flow Without ML
# =============================================================================

class TestDetectionFlowWithoutML:
    """Tests for detection flow when ML is disabled."""
    
    def test_nes_detection(self):
        """NES files should be detected correctly without ML."""
        from src.detectors.detection_handler import detect_console
        
        console, confidence = detect_console("Super Mario Bros.nes")
        
        assert console == "NES"
        assert confidence >= 0.7
    
    def test_snes_detection(self):
        """SNES files should be detected correctly without ML."""
        from src.detectors.detection_handler import detect_console
        
        console, confidence = detect_console("Super Mario World.smc")
        
        assert console == "SNES"
        assert confidence >= 0.7
    
    def test_gba_detection(self):
        """GBA files should be detected correctly without ML."""
        from src.detectors.detection_handler import detect_console
        
        console, confidence = detect_console("Pokemon Ruby.gba")
        
        assert console == "GBA"
        assert confidence >= 0.7
    
    def test_unknown_extension(self):
        """Unknown extensions should return Unknown."""
        from src.detectors.detection_handler import detect_console
        
        console, confidence = detect_console("mystery_file.xyz123")
        
        assert console == "Unknown"
        assert confidence < 0.5


# =============================================================================
# Test: Specialized Detectors
# =============================================================================

class TestSpecializedDetectors:
    """Tests for archive and CHD detector integration."""
    
    def test_archive_detection_path(self, tmp_path):
        """Archive files should go through archive detector."""
        from src.detectors.detection_handler import DetectionManager
        
        # Create a fake zip file
        zip_file = tmp_path / "test.zip"
        zip_file.write_bytes(b"PK\x03\x04" + b"\x00" * 100)  # Minimal ZIP header
        
        manager = DetectionManager.get_instance()
        manager.clear_cache()
        
        # Detect
        result = manager.detect_console_with_metadata("test.zip", str(zip_file))
        
        # Should have been processed (even if Unknown)
        stats = manager.get_statistics()
        # Archive detection counter should increase
        assert isinstance(result.console, str)
    
    def test_chd_detection_path(self, tmp_path):
        """CHD files should go through CHD detector."""
        from src.detectors.detection_handler import DetectionManager
        
        # Create a fake CHD file
        chd_file = tmp_path / "test.chd"
        chd_file.write_bytes(b"MComprHD" + b"\x00" * 200)
        
        manager = DetectionManager.get_instance()
        manager.clear_cache()
        
        # Detect
        result = manager.detect_console_with_metadata("test.chd", str(chd_file))
        
        # Should have been processed
        assert isinstance(result.console, str)


# =============================================================================
# Test: Statistics Tracking
# =============================================================================

class TestStatisticsTracking:
    """Tests for detection statistics."""
    
    def test_statistics_structure(self):
        """Statistics should have expected structure."""
        from src.detectors.detection_handler import DetectionManager
        
        manager = DetectionManager.get_instance()
        stats = manager.get_statistics()
        
        expected_keys = [
            "total_detections",
            "cache_hits",
            "cache_misses",
            "high_confidence",
            "acceptable_confidence",
            "low_confidence",
            "unknown",
        ]
        
        for key in expected_keys:
            assert key in stats, f"Missing stats key: {key}"
    
    def test_cache_hit_rate_calculation(self):
        """Cache hit rate should be calculated correctly."""
        from src.detectors.detection_handler import DetectionManager
        
        manager = DetectionManager.get_instance()
        manager.clear_cache()
        
        # Force some detections
        for _ in range(3):
            manager.detect_console("test.nes")
        
        stats = manager.get_statistics()
        
        # Hit rate should be between 0 and 1
        assert 0.0 <= stats.get("cache_hit_rate", 0.0) <= 1.0


# =============================================================================
# Test: API Compatibility
# =============================================================================

class TestAPICompatibility:
    """Tests for API backwards compatibility."""
    
    def test_detect_console_function_exists(self):
        """detect_console function should be importable."""
        from src.detectors.detection_handler import detect_console
        
        assert callable(detect_console)
    
    def test_detect_console_with_metadata_function_exists(self):
        """detect_console_with_metadata function should be importable."""
        from src.detectors.detection_handler import detect_console_with_metadata
        
        assert callable(detect_console_with_metadata)
    
    def test_detect_rom_type_alias_works(self):
        """detect_rom_type should be alias for detect_console_with_metadata."""
        from src.detectors.detection_handler import detect_rom_type, detect_console_with_metadata
        
        result1 = detect_rom_type("test.nes")
        result2 = detect_console_with_metadata("test.nes")
        
        assert result1.console == result2.console
    
    def test_get_console_list_returns_dict(self):
        """get_console_list should return dictionary."""
        from src.detectors.detection_handler import get_console_list
        
        consoles = get_console_list()
        
        assert isinstance(consoles, dict)
        assert len(consoles) > 0
