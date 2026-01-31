"""Tests for Duplicate Management Module (F75-F78).

Tests:
- F75: Hash Duplicate Finder
- F76: Fuzzy Duplicate Finder
- F77: Merge Wizard
- F78: Parent/Clone Management
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.duplicates.hash_duplicate_finder import (
    HashDuplicateFinder,
    DuplicateGroup,
    DuplicateEntry,
    find_duplicates,
    calculate_wasted_space,
)
from src.duplicates.fuzzy_duplicate_finder import (
    FuzzyDuplicateFinder,
    FuzzyMatch,
    FuzzyGroup,
    MatchReason,
    find_fuzzy_duplicates,
    _levenshtein_distance,
    _levenshtein_similarity,
    _detect_region,
)
from src.duplicates.merge_wizard import (
    MergeWizard,
    MergeStrategy,
    MergeAction,
    MergeDecision,
    MergeResult,
    auto_merge_duplicates,
)
from src.duplicates.parent_clone import (
    ParentCloneManager,
    RomRelationship,
    ParentCloneGroup,
    RelationshipType,
    build_parent_clone_hierarchy,
)


class TestHashDuplicateFinder:
    """Tests for HashDuplicateFinder (F75)."""

    def test_init_defaults(self):
        """Test default initialization."""
        finder = HashDuplicateFinder()
        assert finder.use_sha1 is True
        assert finder.use_crc32_fallback is True

    def test_no_duplicates(self, tmp_path):
        """Test with no duplicates."""
        (tmp_path / "file1.rom").write_bytes(b"unique content 1")
        (tmp_path / "file2.rom").write_bytes(b"unique content 2")

        paths = [str(p) for p in tmp_path.glob("*.rom")]
        finder = HashDuplicateFinder()
        groups = finder.find_duplicates(paths)

        assert len(groups) == 0

    def test_find_exact_duplicates(self, tmp_path):
        """Test finding exact duplicates."""
        content = b"identical content for all"
        (tmp_path / "copy1.rom").write_bytes(content)
        (tmp_path / "copy2.rom").write_bytes(content)
        (tmp_path / "copy3.rom").write_bytes(content)

        paths = [str(p) for p in tmp_path.glob("*.rom")]
        finder = HashDuplicateFinder()
        groups = finder.find_duplicates(paths)

        assert len(groups) == 1
        assert groups[0].count == 3

    def test_multiple_duplicate_groups(self, tmp_path):
        """Test multiple duplicate groups."""
        (tmp_path / "group1_a.rom").write_bytes(b"group 1 content")
        (tmp_path / "group1_b.rom").write_bytes(b"group 1 content")
        (tmp_path / "group2_a.rom").write_bytes(b"group 2 content")
        (tmp_path / "group2_b.rom").write_bytes(b"group 2 content")
        (tmp_path / "unique.rom").write_bytes(b"unique")

        paths = [str(p) for p in tmp_path.glob("*.rom")]
        finder = HashDuplicateFinder()
        groups = finder.find_duplicates(paths)

        assert len(groups) == 2

    def test_wasted_bytes_calculation(self, tmp_path):
        """Test wasted bytes calculation."""
        content = b"x" * 1000
        (tmp_path / "a.rom").write_bytes(content)
        (tmp_path / "b.rom").write_bytes(content)
        (tmp_path / "c.rom").write_bytes(content)

        paths = [str(p) for p in tmp_path.glob("*.rom")]
        finder = HashDuplicateFinder()
        groups = finder.find_duplicates(paths)

        assert len(groups) == 1
        # 3 copies of 1000 bytes, keep 1 = 2000 wasted
        assert groups[0].wasted_bytes == 2000

    def test_progress_callback(self, tmp_path):
        """Test progress callback is called."""
        (tmp_path / "file.rom").write_bytes(b"test")
        paths = [str(p) for p in tmp_path.glob("*.rom")]

        progress_calls = []

        def callback(current, total, path):
            progress_calls.append((current, total))

        finder = HashDuplicateFinder()
        finder.find_duplicates(paths, progress_callback=callback)

        assert len(progress_calls) > 0

    def test_cancellation(self, tmp_path):
        """Test cancellation support."""
        for i in range(10):
            (tmp_path / f"file{i}.rom").write_bytes(f"content{i}".encode())

        paths = [str(p) for p in tmp_path.glob("*.rom")]

        class MockCancel:
            def __init__(self):
                self.count = 0

            def is_set(self):
                self.count += 1
                return self.count > 3

        cancel = MockCancel()
        finder = HashDuplicateFinder()
        finder.find_duplicates(paths, cancel_event=cancel)
        # Should have stopped early
        assert cancel.count <= 10


class TestDuplicateGroup:
    """Tests for DuplicateGroup."""

    def test_mark_primary(self):
        """Test marking primary entry."""
        group = DuplicateGroup(hash_value="abc", hash_type="sha1")
        group.entries.append(DuplicateEntry(file_path="/a.rom", file_size=100))
        group.entries.append(DuplicateEntry(file_path="/b.rom", file_size=100))

        assert group.mark_primary("/b.rom")
        assert group.primary.file_path == "/b.rom"

    def test_get_duplicates_to_remove(self):
        """Test getting duplicates to remove."""
        group = DuplicateGroup(hash_value="abc", hash_type="sha1")
        group.entries.append(
            DuplicateEntry(file_path="/keep.rom", file_size=100, is_primary=True)
        )
        group.entries.append(DuplicateEntry(file_path="/remove1.rom", file_size=100))
        group.entries.append(DuplicateEntry(file_path="/remove2.rom", file_size=100))

        to_remove = group.get_duplicates_to_remove()
        assert len(to_remove) == 2
        assert all(e.file_path != "/keep.rom" for e in to_remove)


class TestFuzzyDuplicateFinder:
    """Tests for FuzzyDuplicateFinder (F76)."""

    def test_region_detection(self):
        """Test region detection from filenames."""
        assert _detect_region("Game (USA)") == "USA"
        assert _detect_region("Game (Europe)") == "Europe"
        assert _detect_region("Game (Japan)") == "Japan"
        assert _detect_region("Game (World)") == "World"
        assert _detect_region("Game") == "Unknown"

    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation."""
        assert _levenshtein_distance("", "") == 0
        assert _levenshtein_distance("abc", "abc") == 0
        assert _levenshtein_distance("abc", "ab") == 1
        assert _levenshtein_distance("kitten", "sitting") == 3

    def test_levenshtein_similarity(self):
        """Test similarity calculation."""
        assert _levenshtein_similarity("abc", "abc") == 1.0
        assert _levenshtein_similarity("", "") == 1.0
        assert 0.5 < _levenshtein_similarity("game", "gamer") < 1.0

    def test_find_region_variants(self, tmp_path):
        """Test finding region variants."""
        (tmp_path / "Game (USA).rom").write_bytes(b"usa")
        (tmp_path / "Game (Europe).rom").write_bytes(b"eur")
        (tmp_path / "Game (Japan).rom").write_bytes(b"jpn")

        paths = [str(p) for p in tmp_path.glob("*.rom")]
        finder = FuzzyDuplicateFinder()
        groups = finder.find_fuzzy_duplicates(paths)

        # All three should be in one group
        assert len(groups) >= 1
        total_files = sum(g.count for g in groups)
        assert total_files == 3

    def test_find_revision_variants(self, tmp_path):
        """Test finding revision variants."""
        (tmp_path / "Game (Rev A).rom").write_bytes(b"a")
        (tmp_path / "Game (Rev B).rom").write_bytes(b"b")

        paths = [str(p) for p in tmp_path.glob("*.rom")]
        finder = FuzzyDuplicateFinder()
        groups = finder.find_fuzzy_duplicates(paths)

        assert len(groups) >= 1
        # Check match reason
        for group in groups:
            for match in group.matches:
                if "Rev" in match.filename_a and "Rev" in match.filename_b:
                    assert match.match_reason == MatchReason.SAME_GAME_DIFFERENT_REVISION

    def test_find_alternate_dumps(self, tmp_path):
        """Test finding alternate dumps."""
        (tmp_path / "Game [a1].rom").write_bytes(b"a1")
        (tmp_path / "Game [a2].rom").write_bytes(b"a2")

        paths = [str(p) for p in tmp_path.glob("*.rom")]
        finder = FuzzyDuplicateFinder()
        groups = finder.find_fuzzy_duplicates(paths)

        assert len(groups) >= 1

    def test_name_normalization(self):
        """Test name normalization."""
        finder = FuzzyDuplicateFinder()

        # Should normalize to same base
        name1 = finder._normalize_name("Super Mario Bros (USA) [!]")
        name2 = finder._normalize_name("Super Mario Bros (Europe)")
        name3 = finder._normalize_name("Super Mario Bros [a1]")

        assert name1 == name2 == name3


class TestMergeWizard:
    """Tests for MergeWizard (F77)."""

    def test_strategy_keep_first(self, tmp_path):
        """Test KEEP_FIRST strategy."""
        entries = [
            DuplicateEntry(file_path="/z_file.rom", file_size=100),
            DuplicateEntry(file_path="/a_file.rom", file_size=100),
        ]

        wizard = MergeWizard(strategy=MergeStrategy.KEEP_FIRST)
        selected = wizard._select_keep_entry(entries)
        assert selected.file_path == "/a_file.rom"

    def test_strategy_keep_largest(self, tmp_path):
        """Test KEEP_LARGEST strategy."""
        entries = [
            DuplicateEntry(file_path="/small.rom", file_size=100),
            DuplicateEntry(file_path="/large.rom", file_size=1000),
        ]

        wizard = MergeWizard(strategy=MergeStrategy.KEEP_LARGEST)
        selected = wizard._select_keep_entry(entries)
        assert selected.file_path == "/large.rom"

    def test_strategy_keep_smallest(self, tmp_path):
        """Test KEEP_SMALLEST strategy."""
        entries = [
            DuplicateEntry(file_path="/small.rom", file_size=100),
            DuplicateEntry(file_path="/large.rom", file_size=1000),
        ]

        wizard = MergeWizard(strategy=MergeStrategy.KEEP_SMALLEST)
        selected = wizard._select_keep_entry(entries)
        assert selected.file_path == "/small.rom"

    def test_strategy_keep_verified(self, tmp_path):
        """Test KEEP_VERIFIED strategy."""
        entries = [
            DuplicateEntry(file_path="/normal.rom", file_size=100),
            DuplicateEntry(file_path="/verified [!].rom", file_size=100),
        ]

        wizard = MergeWizard(strategy=MergeStrategy.KEEP_VERIFIED)
        selected = wizard._select_keep_entry(entries)
        assert "[!]" in selected.file_path

    def test_plan_merge(self, tmp_path):
        """Test merge planning."""
        group = DuplicateGroup(hash_value="abc", hash_type="sha1")
        group.entries.append(DuplicateEntry(file_path="/a.rom", file_size=100))
        group.entries.append(DuplicateEntry(file_path="/b.rom", file_size=100))

        wizard = MergeWizard(strategy=MergeStrategy.KEEP_FIRST)
        decisions = wizard.plan_merge([group])

        assert len(decisions) == 1
        assert len(decisions[0].remove_paths) == 1

    def test_execute_merge_dry_run(self, tmp_path):
        """Test dry-run execution."""
        content = b"test content"
        (tmp_path / "a.rom").write_bytes(content)
        (tmp_path / "b.rom").write_bytes(content)

        group = DuplicateGroup(hash_value="abc", hash_type="sha1")
        group.entries.append(
            DuplicateEntry(file_path=str(tmp_path / "a.rom"), file_size=len(content))
        )
        group.entries.append(
            DuplicateEntry(file_path=str(tmp_path / "b.rom"), file_size=len(content))
        )

        wizard = MergeWizard(strategy=MergeStrategy.KEEP_FIRST, action=MergeAction.DELETE)
        decisions = wizard.plan_merge([group])
        result = wizard.execute_merge(decisions, dry_run=True)

        # Files should still exist (dry run)
        assert (tmp_path / "a.rom").exists()
        assert (tmp_path / "b.rom").exists()
        assert result.files_removed == 1

    def test_execute_merge_delete(self, tmp_path):
        """Test actual deletion."""
        content = b"test"
        # Use alphabetical naming so KEEP_FIRST keeps 'a_keep.rom'
        (tmp_path / "a_keep.rom").write_bytes(content)
        (tmp_path / "z_delete.rom").write_bytes(content)

        group = DuplicateGroup(hash_value="abc", hash_type="sha1")
        group.entries.append(
            DuplicateEntry(
                file_path=str(tmp_path / "a_keep.rom"), file_size=len(content)
            )
        )
        group.entries.append(
            DuplicateEntry(file_path=str(tmp_path / "z_delete.rom"), file_size=len(content))
        )

        wizard = MergeWizard(strategy=MergeStrategy.KEEP_FIRST, action=MergeAction.DELETE)
        decisions = wizard.plan_merge([group])
        result = wizard.execute_merge(decisions, dry_run=False)

        assert (tmp_path / "a_keep.rom").exists()
        assert not (tmp_path / "z_delete.rom").exists()
        assert result.success


class TestParentCloneManager:
    """Tests for ParentCloneManager (F78)."""

    def test_get_base_name(self):
        """Test base name extraction."""
        manager = ParentCloneManager()

        assert manager._get_base_name("Game (USA)") == "Game"
        assert manager._get_base_name("Game [!]") == "Game"
        assert manager._get_base_name("Game (Rev A) [!]") == "Game"
        assert manager._get_base_name("Game v1.0") == "Game"

    def test_looks_like_clone(self):
        """Test clone detection."""
        manager = ParentCloneManager()

        assert manager._looks_like_clone("Game [a1]")  # Alternate
        assert manager._looks_like_clone("Game [h]")  # Hack
        assert manager._looks_like_clone("Game [t]")  # Trainer
        assert manager._looks_like_clone("Game (Rev B)")  # Rev B
        assert not manager._looks_like_clone("Game [!]")  # Verified
        assert not manager._looks_like_clone("Game (USA)")  # Just region

    def test_looks_like_parent(self):
        """Test parent detection."""
        manager = ParentCloneManager()

        assert manager._looks_like_parent("Game [!]")  # Verified
        assert manager._looks_like_parent("Game (Rev A)")  # Rev A
        assert manager._looks_like_parent("Game v1.0")  # v1.0

    def test_parent_score(self):
        """Test parent scoring."""
        manager = ParentCloneManager()

        # Verified good should score highest
        verified = manager._parent_score("Game [!]")
        normal = manager._parent_score("Game (USA)")
        clone = manager._parent_score("Game [a1]")

        assert verified > normal > clone

    def test_build_hierarchy(self, tmp_path):
        """Test building parent/clone hierarchy."""
        # Create test files
        (tmp_path / "Game [!].rom").write_bytes(b"parent")
        (tmp_path / "Game [a1].rom").write_bytes(b"clone1")
        (tmp_path / "Game [a2].rom").write_bytes(b"clone2")

        paths = [str(p) for p in tmp_path.glob("*.rom")]
        manager = ParentCloneManager()
        groups = manager.build_hierarchy(paths)

        assert len(groups) == 1
        group = groups[0]
        assert group.has_parent
        assert "[!]" in group.parent.rom_name
        assert len(group.clones) == 2

    def test_suggest_parent(self, tmp_path):
        """Test parent suggestion."""
        (tmp_path / "Game (USA).rom").write_bytes(b"usa")
        (tmp_path / "Game [!].rom").write_bytes(b"verified")
        (tmp_path / "Game [a1].rom").write_bytes(b"alt")

        paths = [str(p) for p in tmp_path.glob("*.rom")]
        manager = ParentCloneManager()
        suggested = manager.suggest_parent(paths)

        # Should suggest the verified one
        assert "[!]" in suggested

    def test_get_clones_for_parent(self, tmp_path):
        """Test getting clones for a parent."""
        parent_path = str(tmp_path / "Game [!].rom")
        (tmp_path / "Game [!].rom").write_bytes(b"parent")
        (tmp_path / "Game [a1].rom").write_bytes(b"clone1")
        (tmp_path / "Game [h].rom").write_bytes(b"hack")
        (tmp_path / "Other [!].rom").write_bytes(b"other")

        paths = [str(p) for p in tmp_path.glob("*.rom")]
        manager = ParentCloneManager()
        clones = manager.get_clones_for_parent(parent_path, paths)

        assert len(clones) == 2
        assert all("Game" in c for c in clones)


class TestRomRelationship:
    """Tests for RomRelationship dataclass."""

    def test_is_parent_property(self):
        """Test is_parent property."""
        parent = RomRelationship(
            file_path="/test.rom",
            rom_name="Test",
            relationship_type=RelationshipType.PARENT,
        )
        clone = RomRelationship(
            file_path="/test.rom",
            rom_name="Test",
            relationship_type=RelationshipType.CLONE,
        )

        assert parent.is_parent
        assert not clone.is_parent

    def test_has_clones_property(self):
        """Test has_clones property."""
        rel = RomRelationship(file_path="/test.rom", rom_name="Test")
        assert not rel.has_clones

        rel.clones.append("/clone.rom")
        assert rel.has_clones


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_find_duplicates_function(self, tmp_path):
        """Test find_duplicates convenience function."""
        content = b"duplicate"
        (tmp_path / "a.rom").write_bytes(content)
        (tmp_path / "b.rom").write_bytes(content)

        paths = [str(p) for p in tmp_path.glob("*.rom")]
        groups = find_duplicates(paths)

        assert len(groups) == 1

    def test_calculate_wasted_space_function(self):
        """Test calculate_wasted_space function."""
        group = DuplicateGroup(hash_value="abc", hash_type="sha1")
        group.entries.append(DuplicateEntry(file_path="/a.rom", file_size=1000))
        group.entries.append(DuplicateEntry(file_path="/b.rom", file_size=1000))

        wasted = calculate_wasted_space([group])
        assert wasted == 1000

    def test_find_fuzzy_duplicates_function(self, tmp_path):
        """Test find_fuzzy_duplicates convenience function."""
        (tmp_path / "Game (USA).rom").write_bytes(b"usa")
        (tmp_path / "Game (Europe).rom").write_bytes(b"eur")

        paths = [str(p) for p in tmp_path.glob("*.rom")]
        groups = find_fuzzy_duplicates(paths)

        assert len(groups) >= 1

    def test_auto_merge_duplicates_function(self):
        """Test auto_merge_duplicates function."""
        group = DuplicateGroup(hash_value="abc", hash_type="sha1")
        group.entries.append(
            DuplicateEntry(file_path="/a.rom", file_size=100, is_primary=True)
        )
        group.entries.append(DuplicateEntry(file_path="/b.rom", file_size=100))

        result = auto_merge_duplicates([group], dry_run=True)
        assert result.success

    def test_build_parent_clone_hierarchy_function(self, tmp_path):
        """Test build_parent_clone_hierarchy function."""
        (tmp_path / "Game [!].rom").write_bytes(b"parent")
        (tmp_path / "Game [a].rom").write_bytes(b"clone")

        paths = [str(p) for p in tmp_path.glob("*.rom")]
        groups = build_parent_clone_hierarchy(paths)

        assert len(groups) == 1
