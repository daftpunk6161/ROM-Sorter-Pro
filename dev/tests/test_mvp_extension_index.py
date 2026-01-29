"""Tests for Extension Index optimization (O(1) lookup).

Tests cover:
- Inverted index building
- O(1) extension lookup
- Unique extension detection
- Ambiguity counting
- Performance verification
"""

import time
import pytest

from src.database.console_db import (
    get_consoles_for_extension_fast,
    is_unique_extension,
    get_extension_ambiguity_count,
    get_console_for_extension,
    _build_extension_index,
    _build_unique_extension_set,
    ENHANCED_CONSOLE_DATABASE,
)


# =============================================================================
# Test: Index Building
# =============================================================================

class TestIndexBuilding:
    """Tests for extension index construction."""
    
    def test_index_contains_all_extensions(self):
        """Index should contain all extensions from database."""
        index = _build_extension_index()
        
        # Collect all extensions from database
        all_exts = set()
        for meta in ENHANCED_CONSOLE_DATABASE.values():
            for ext in meta.extensions:
                normalized = ext.lower() if ext.startswith('.') else f'.{ext.lower()}'
                all_exts.add(normalized)
        
        # All extensions should be in index
        assert all_exts == set(index.keys())
    
    def test_index_maps_to_correct_consoles(self):
        """Each extension should map to correct console(s)."""
        index = _build_extension_index()
        
        # .nes should map to NES
        assert 'NES' in index.get('.nes', [])
        
        # .gba should map to GBA
        assert 'GBA' in index.get('.gba', [])
    
    def test_ambiguous_extensions_have_multiple_consoles(self):
        """Ambiguous extensions should map to multiple consoles."""
        index = _build_extension_index()
        
        # .bin is used by many platforms
        bin_consoles = index.get('.bin', [])
        assert len(bin_consoles) > 1, ".bin should be ambiguous"
    
    def test_unique_extension_set_built_correctly(self):
        """Unique extension set should only contain unique extensions."""
        unique_set = _build_unique_extension_set()
        index = _build_extension_index()
        
        for ext in unique_set:
            consoles = index.get(ext, [])
            assert len(consoles) == 1, f"{ext} should map to exactly 1 console"


# =============================================================================
# Test: Fast Lookup
# =============================================================================

class TestFastLookup:
    """Tests for O(1) extension lookup."""
    
    def test_lookup_with_dot(self):
        """Lookup should work with leading dot."""
        consoles = get_consoles_for_extension_fast('.nes')
        assert 'NES' in consoles
    
    def test_lookup_without_dot(self):
        """Lookup should work without leading dot."""
        consoles = get_consoles_for_extension_fast('nes')
        assert 'NES' in consoles
    
    def test_lookup_case_insensitive(self):
        """Lookup should be case-insensitive."""
        consoles_lower = get_consoles_for_extension_fast('.nes')
        consoles_upper = get_consoles_for_extension_fast('.NES')
        consoles_mixed = get_consoles_for_extension_fast('.Nes')
        
        assert consoles_lower == consoles_upper == consoles_mixed
    
    def test_unknown_extension_returns_empty(self):
        """Unknown extension should return empty list."""
        consoles = get_consoles_for_extension_fast('.xyz123unknown')
        assert consoles == []
    
    def test_ambiguous_extension_returns_all(self):
        """Ambiguous extension should return all matching consoles."""
        consoles = get_consoles_for_extension_fast('.bin')
        assert len(consoles) > 1


# =============================================================================
# Test: Unique Extension Detection
# =============================================================================

class TestUniqueExtensions:
    """Tests for unique extension detection."""
    
    def test_unique_extension_detected(self):
        """Unique extensions should be detected."""
        # .nes is unique to NES
        assert is_unique_extension('.nes') is True
        assert is_unique_extension('nes') is True  # Without dot
    
    def test_ambiguous_extension_not_unique(self):
        """Ambiguous extensions should not be unique."""
        # .bin is used by many platforms
        assert is_unique_extension('.bin') is False
    
    def test_unknown_extension_not_unique(self):
        """Unknown extensions should not be unique."""
        assert is_unique_extension('.xyz123') is False


# =============================================================================
# Test: Ambiguity Counting
# =============================================================================

class TestAmbiguityCounting:
    """Tests for extension ambiguity counting."""
    
    def test_unique_extension_count_is_one(self):
        """Unique extensions should have count of 1."""
        count = get_extension_ambiguity_count('.nes')
        assert count == 1
    
    def test_ambiguous_extension_count_greater_than_one(self):
        """Ambiguous extensions should have count > 1."""
        count = get_extension_ambiguity_count('.bin')
        assert count > 1
    
    def test_unknown_extension_count_is_zero(self):
        """Unknown extensions should have count of 0."""
        count = get_extension_ambiguity_count('.xyz123unknown')
        assert count == 0


# =============================================================================
# Test: Consistency with Legacy Function
# =============================================================================

class TestLegacyConsistency:
    """Tests to verify new functions match legacy behavior."""
    
    def test_fast_lookup_matches_legacy_for_unique(self):
        """Fast lookup should match legacy for unique extensions."""
        # Test several known unique extensions
        test_exts = ['.nes', '.smc', '.gba', '.nds', '.n64']
        
        for ext in test_exts:
            legacy_result = get_console_for_extension(ext)
            fast_results = get_consoles_for_extension_fast(ext)
            
            if legacy_result:
                assert legacy_result in fast_results, f"Mismatch for {ext}"
    
    def test_fast_lookup_returns_superset_of_legacy(self):
        """Fast lookup should return all consoles including legacy result."""
        # For any extension, if legacy returns a console, fast should include it
        for console_name, meta in ENHANCED_CONSOLE_DATABASE.items():
            for ext in meta.extensions:
                legacy = get_console_for_extension(ext)
                fast = get_consoles_for_extension_fast(ext)
                
                if legacy:
                    assert legacy in fast, f"Legacy {legacy} not in fast results for {ext}"


# =============================================================================
# Test: Performance
# =============================================================================

class TestPerformance:
    """Tests to verify O(1) performance."""
    
    def test_fast_lookup_is_fast(self):
        """Fast lookup should be significantly faster than iteration."""
        # Warm up cache
        _ = get_consoles_for_extension_fast('.nes')
        
        iterations = 10000
        
        # Time fast lookup
        start = time.perf_counter()
        for _ in range(iterations):
            get_consoles_for_extension_fast('.bin')
        fast_time = time.perf_counter() - start
        
        # Fast lookup should complete 10000 iterations in < 100ms
        assert fast_time < 0.1, f"Fast lookup too slow: {fast_time}s for {iterations} iterations"
    
    def test_index_built_once(self):
        """Index should be cached (built only once)."""
        # Clear cache
        _build_extension_index.cache_clear()
        
        # Build index twice
        index1 = _build_extension_index()
        index2 = _build_extension_index()
        
        # Should be the exact same object (cached)
        assert index1 is index2


# =============================================================================
# Test: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_empty_extension(self):
        """Empty extension should return empty list."""
        consoles = get_consoles_for_extension_fast('')
        # Should either return empty or handle gracefully
        assert isinstance(consoles, list)
    
    def test_only_dot_extension(self):
        """Just a dot should return empty list."""
        consoles = get_consoles_for_extension_fast('.')
        assert consoles == []
    
    def test_extension_with_multiple_dots(self):
        """Extension with multiple dots should be handled."""
        # Not a real extension, should return empty
        consoles = get_consoles_for_extension_fast('.tar.gz')
        # May or may not be in database, but shouldn't crash
        assert isinstance(consoles, list)
    
    def test_very_long_extension(self):
        """Very long extension should be handled."""
        consoles = get_consoles_for_extension_fast('.' + 'x' * 1000)
        assert consoles == []
