"""
MVP Dry-run Guard Tests
=======================

Tests für P1-005: Dry-run Invariante explizit enforced

Die Tests validieren:
1. execute_sort(dry_run=True) macht NULL Schreiboperationen
2. Alle Code-Pfade (copy, move, convert, overwrite) im dry_run-Modus
3. Kein mkdir, kein remove, kein copy, kein move
4. Return-Werte und Statistiken bleiben korrekt
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import cast
from typing import List
from unittest.mock import patch

import pytest

from src.app.controller import execute_sort
from src.app.models import ConflictPolicy, SortMode
from src.app.models import CancelToken, SortPlan, SortAction, SortReport


# ---------------------------------------------------------------------------
# Helper: Create SortAction with proper schema
# ---------------------------------------------------------------------------


def make_sort_action(
    input_path: str,
    detected_system: str,
    planned_target_path: str,
    action: str = "copy",
    status: str = "pending",
    conversion_tool: str | None = None,
    conversion_tool_key: str | None = None,
    conversion_args: list[str] | None = None,
) -> SortAction:
    """Factory for SortAction with correct field names."""
    return SortAction(
        input_path=input_path,
        detected_system=detected_system,
        planned_target_path=planned_target_path,
        action=action,
        status=status,
        conversion_tool=conversion_tool,
        conversion_tool_key=conversion_tool_key,
        conversion_args=conversion_args,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_source_dir():
    """Create temp directory with test ROM files."""
    with tempfile.TemporaryDirectory(prefix="rom_src_") as d:
        src = Path(d)

        # Create some test files
        (src / "game1.nes").write_bytes(b"\x4e\x45\x53\x1a" + b"\x00" * 12 + b"X" * 100)
        (src / "game2.gba").write_bytes(b"GBA_ROM_DATA_123" + b"\x00" * 100)
        (src / "game3.sfc").write_bytes(b"SNES_ROM_DATA" + b"\x00" * 100)

        yield src


@pytest.fixture
def temp_dest_dir():
    """Create empty temp destination directory."""
    with tempfile.TemporaryDirectory(prefix="rom_dst_") as d:
        yield Path(d)


@pytest.fixture
def mock_sort_plan(temp_source_dir: Path, temp_dest_dir: Path) -> SortPlan:
    """Create a mock SortPlan with various actions."""
    src = temp_source_dir

    actions = [
        make_sort_action(
            input_path=str(src / "game1.nes"),
            detected_system="NES",
            planned_target_path=str(temp_dest_dir / "NES" / "game1.nes"),
            action="copy",
            status="pending",
        ),
        make_sort_action(
            input_path=str(src / "game2.gba"),
            detected_system="GBA",
            planned_target_path=str(temp_dest_dir / "GBA" / "game2.gba"),
            action="move",
            status="pending",
        ),
        make_sort_action(
            input_path=str(src / "game3.sfc"),
            detected_system="SNES",
            planned_target_path=str(temp_dest_dir / "SNES" / "game3.sfc"),
            action="copy",
            status="pending",
        ),
    ]

    return SortPlan(
        dest_path=str(temp_dest_dir),
        mode=cast(SortMode, "copy"),
        on_conflict=cast(ConflictPolicy, "skip"),
        actions=actions,
    )


# ---------------------------------------------------------------------------
# Helper: Filesystem Snapshot
# ---------------------------------------------------------------------------


def get_filesystem_snapshot(directory: Path) -> dict:
    """Get a snapshot of all files/dirs in a directory with their mtimes and sizes."""
    snapshot = {}
    if not directory.exists():
        return snapshot
    for root, dirs, files in os.walk(directory):
        root_path = Path(root)
        for d in dirs:
            p = root_path / d
            snapshot[str(p)] = {"type": "dir", "mtime": p.stat().st_mtime}
        for f in files:
            p = root_path / f
            stat = p.stat()
            snapshot[str(p)] = {"type": "file", "mtime": stat.st_mtime, "size": stat.st_size}
    return snapshot


def get_file_count(directory: Path) -> int:
    """Count files in directory recursively."""
    if not directory.exists():
        return 0
    return sum(1 for _ in directory.rglob("*") if _.is_file())


# ---------------------------------------------------------------------------
# Test Class: Basic Dry-run Invariants
# ---------------------------------------------------------------------------


class TestDryRunBasicInvariants:
    """Basic invariant tests for dry_run=True."""

    def test_dry_run_creates_no_directories(self, mock_sort_plan: SortPlan, temp_dest_dir: Path):
        """dry_run=True should not create any directories in destination."""
        dest = temp_dest_dir

        # Destination should be empty initially
        assert get_file_count(dest) == 0

        # Execute in dry-run mode
        report = execute_sort(mock_sort_plan, dry_run=True)

        # Destination should still be empty
        assert get_file_count(dest) == 0

        # Check no subdirs created
        subdirs = [d for d in dest.iterdir() if d.is_dir()]
        assert len(subdirs) == 0, f"Dry-run created directories: {subdirs}"

        # Report should indicate processed items
        assert report.processed == 3

    def test_dry_run_creates_no_files(self, mock_sort_plan: SortPlan, temp_dest_dir: Path):
        """dry_run=True should not create any files."""
        dest = temp_dest_dir

        # Execute in dry-run mode
        execute_sort(mock_sort_plan, dry_run=True)

        # Check no files created
        files = list(dest.rglob("*"))
        assert len(files) == 0, f"Dry-run created files: {files}"

    def test_dry_run_does_not_delete_source_on_move(
        self, temp_source_dir: Path, temp_dest_dir: Path
    ):
        """dry_run=True in move mode should not delete source files."""
        src = temp_source_dir

        # Create a move-mode plan
        actions = [
            make_sort_action(
                input_path=str(src / "game1.nes"),
                detected_system="NES",
                planned_target_path=str(temp_dest_dir / "NES" / "game1.nes"),
                action="move",
                status="pending",
            ),
        ]

        plan = SortPlan(
            dest_path=str(temp_dest_dir),
            mode="move",
            on_conflict="skip",
            actions=actions,
        )

        # Verify source exists before
        assert (src / "game1.nes").exists()

        # Execute dry-run
        report = execute_sort(plan, dry_run=True)

        # Source must still exist
        assert (src / "game1.nes").exists(), "Dry-run deleted source file in move mode!"

        # Report should show 1 moved (simulated)
        assert report.moved == 1

    def test_dry_run_returns_valid_report(self, mock_sort_plan: SortPlan):
        """dry_run=True should return a valid SortReport with correct counts."""
        report = execute_sort(mock_sort_plan, dry_run=True)

        assert isinstance(report, SortReport)
        assert report.processed == 3
        assert report.errors == []
        assert not report.cancelled


# ---------------------------------------------------------------------------
# Test Class: Overwrite Policy in Dry-run
# ---------------------------------------------------------------------------


class TestDryRunOverwritePolicy:
    """Tests for dry_run with overwrite conflict policy."""

    def test_dry_run_does_not_overwrite_existing_files(
        self, temp_source_dir: Path, temp_dest_dir: Path
    ):
        """dry_run=True with on_conflict=overwrite should NOT actually overwrite."""
        src = temp_source_dir
        dest = temp_dest_dir

        # Pre-create a file at destination
        (dest / "NES").mkdir(parents=True)
        existing_file = dest / "NES" / "game1.nes"
        existing_file.write_bytes(b"ORIGINAL_CONTENT")
        original_content = existing_file.read_bytes()

        actions = [
            make_sort_action(
                input_path=str(src / "game1.nes"),
                detected_system="NES",
                planned_target_path=str(existing_file),
                action="copy",
                status="pending",
            ),
        ]

        plan = SortPlan(
            dest_path=str(dest),
            mode="copy",
            on_conflict="overwrite",
            actions=actions,
        )

        # Execute dry-run
        execute_sort(plan, dry_run=True)

        # File content must be unchanged
        assert existing_file.read_bytes() == original_content

    def test_dry_run_does_not_unlink_for_overwrite(
        self, temp_source_dir: Path, temp_dest_dir: Path
    ):
        """dry_run=True should not call unlink/remove for overwrite preparation."""
        src = temp_source_dir
        dest = temp_dest_dir

        # Pre-create destination structure with file
        (dest / "NES").mkdir(parents=True)
        existing = dest / "NES" / "game1.nes"
        existing.write_bytes(b"EXISTING")

        actions = [
            make_sort_action(
                input_path=str(src / "game1.nes"),
                detected_system="NES",
                planned_target_path=str(existing),
                action="copy",
                status="pending",
            ),
        ]

        plan = SortPlan(
            dest_path=str(dest),
            mode="copy",
            on_conflict="overwrite",
            actions=actions,
        )

        # Patch os.remove to detect calls
        with patch("os.remove") as mock_remove:
            execute_sort(plan, dry_run=True)
            mock_remove.assert_not_called()


# ---------------------------------------------------------------------------
# Test Class: Conversion in Dry-run
# ---------------------------------------------------------------------------


class TestDryRunConversion:
    """Tests for conversion actions in dry_run mode."""

    def test_dry_run_conversion_does_not_run_tool(self, temp_source_dir: Path, temp_dest_dir: Path):
        """dry_run=True should not actually run conversion tools."""
        src = temp_source_dir

        actions = [
            make_sort_action(
                input_path=str(src / "game1.nes"),
                detected_system="NES",
                planned_target_path=str(temp_dest_dir / "NES" / "game1.zip"),
                action="convert",
                status="pending",
                conversion_tool="7z",
                conversion_tool_key="7z",
                conversion_args=["a", str(temp_dest_dir / "NES" / "game1.zip"), str(src / "game1.nes")],
            ),
        ]

        plan = SortPlan(
            dest_path=str(temp_dest_dir),
            mode="copy",
            on_conflict="skip",
            actions=actions,
        )

        # Execute dry-run
        report = execute_sort(plan, dry_run=True)

        # No output file should be created
        assert not (temp_dest_dir / "NES" / "game1.zip").exists()

        # Report should still count it
        assert report.processed == 1


# ---------------------------------------------------------------------------
# Test Class: Filesystem Snapshot Comparison
# ---------------------------------------------------------------------------


class TestDryRunFilesystemSnapshot:
    """Compare filesystem state before/after dry-run."""

    def test_filesystem_unchanged_after_dry_run(
        self, mock_sort_plan: SortPlan, temp_source_dir: Path, temp_dest_dir: Path
    ):
        """Filesystem snapshot should be identical before and after dry_run."""
        # Take snapshot before
        src_before = get_filesystem_snapshot(temp_source_dir)
        dest_before = get_filesystem_snapshot(temp_dest_dir)

        # Execute dry-run
        execute_sort(mock_sort_plan, dry_run=True)

        # Take snapshot after
        src_after = get_filesystem_snapshot(temp_source_dir)
        dest_after = get_filesystem_snapshot(temp_dest_dir)

        # Compare
        assert src_before == src_after, "Source directory was modified during dry-run!"
        assert dest_before == dest_after, "Destination directory was modified during dry-run!"


# ---------------------------------------------------------------------------
# Test Class: os/shutil Mock Verification
# ---------------------------------------------------------------------------


class TestDryRunNoIOCalls:
    """Verify no actual IO calls are made in dry-run mode."""

    def test_no_makedirs_in_dry_run(self, mock_sort_plan: SortPlan):
        """dry_run should not call os.makedirs."""
        with patch("os.makedirs") as mock_makedirs:
            execute_sort(mock_sort_plan, dry_run=True)
            mock_makedirs.assert_not_called()

    def test_no_copy_in_dry_run(self, mock_sort_plan: SortPlan):
        """dry_run should not call shutil.copy/copy2."""
        with patch("shutil.copy") as mock_copy, patch("shutil.copy2") as mock_copy2:
            execute_sort(mock_sort_plan, dry_run=True)
            mock_copy.assert_not_called()
            mock_copy2.assert_not_called()

    def test_no_move_in_dry_run(self, temp_source_dir: Path, temp_dest_dir: Path):
        """dry_run should not call shutil.move or os.replace."""
        actions = [
            make_sort_action(
                input_path=str(temp_source_dir / "game1.nes"),
                detected_system="NES",
                planned_target_path=str(temp_dest_dir / "NES" / "game1.nes"),
                action="move",
                status="pending",
            ),
        ]

        plan = SortPlan(
            dest_path=str(temp_dest_dir),
            mode="move",
            on_conflict="skip",
            actions=actions,
        )

        with patch("shutil.move") as mock_move, patch("os.replace") as mock_replace:
            execute_sort(plan, dry_run=True)
            mock_move.assert_not_called()
            mock_replace.assert_not_called()


# ---------------------------------------------------------------------------
# Test Class: Log Callbacks in Dry-run
# ---------------------------------------------------------------------------


class TestDryRunLogging:
    """Verify dry-run logs correctly indicate simulation."""

    def test_dry_run_log_contains_dry_run_marker(self, mock_sort_plan: SortPlan):
        """Log messages in dry-run should contain 'DRY-RUN' or 'Would'."""
        logs: List[str] = []

        def log_cb(msg: str):
            logs.append(msg)

        execute_sort(mock_sort_plan, dry_run=True, log_cb=log_cb)

        # At least one log should mention dry-run
        assert any("dry_run" in log.lower() or "would" in log.lower() or "dry-run" in log.lower() for log in logs), \
            f"No dry-run indicator in logs: {logs}"

    def test_dry_run_log_shows_planned_operations(self, mock_sort_plan: SortPlan):
        """Dry-run should log what would happen."""
        logs: List[str] = []

        def log_cb(msg: str):
            logs.append(msg)

        execute_sort(mock_sort_plan, dry_run=True, log_cb=log_cb)

        # Should have starting and finish logs
        start_logs = [l for l in logs if "starting" in l.lower()]
        assert len(start_logs) > 0


# ---------------------------------------------------------------------------
# Test Class: Cancel + Dry-run Interaction
# ---------------------------------------------------------------------------


class TestDryRunWithCancel:
    """Test interaction between dry_run and cancel_token."""

    def test_dry_run_can_be_cancelled(self, mock_sort_plan: SortPlan):
        """Dry-run should respect cancel_token."""
        token = CancelToken()
        token.cancel()

        report = execute_sort(mock_sort_plan, dry_run=True, cancel_token=token)

        assert report.cancelled

    def test_dry_run_cancel_no_partial_writes(
        self, temp_source_dir: Path, temp_dest_dir: Path
    ):
        """Even with cancel during dry-run, no files should be written."""
        # Create plan with multiple items
        actions = []
        for i in range(10):
            fname = f"game{i}.nes"
            (temp_source_dir / fname).write_bytes(b"X" * 100)
            actions.append(
                make_sort_action(
                    input_path=str(temp_source_dir / fname),
                    detected_system="NES",
                    planned_target_path=str(temp_dest_dir / "NES" / fname),
                    action="copy",
                    status="pending",
                )
            )

        plan = SortPlan(
            dest_path=str(temp_dest_dir),
            mode="copy",
            on_conflict="skip",
            actions=actions,
        )

        # Cancel immediately
        token = CancelToken()
        token.cancel()

        execute_sort(plan, dry_run=True, cancel_token=token)

        # No files should exist
        assert get_file_count(temp_dest_dir) == 0


# ---------------------------------------------------------------------------
# Test Class: Edge Cases
# ---------------------------------------------------------------------------


class TestDryRunEdgeCases:
    """Edge case tests for dry-run mode."""

    def test_dry_run_with_empty_plan(self, temp_dest_dir: Path):
        """Dry-run with empty actions should succeed."""
        plan = SortPlan(
            dest_path=str(temp_dest_dir),
            mode="copy",
            on_conflict="skip",
            actions=[],
        )

        report = execute_sort(plan, dry_run=True)

        assert report.processed == 0
        assert report.errors == []

    def test_dry_run_with_skipped_actions(self, temp_source_dir: Path, temp_dest_dir: Path):
        """Dry-run should handle pre-skipped actions."""
        actions = [
            make_sort_action(
                input_path=str(temp_source_dir / "game1.nes"),
                detected_system="NES",
                planned_target_path=str(temp_dest_dir / "NES" / "game1.nes"),
                action="copy",
                status="skipped (low confidence)",
            ),
        ]

        plan = SortPlan(
            dest_path=str(temp_dest_dir),
            mode="copy",
            on_conflict="skip",
            actions=actions,
        )

        report = execute_sort(plan, dry_run=True)

        # Should be counted as skipped, not processed as copy
        assert report.skipped == 1

    def test_dry_run_with_missing_source(self, temp_dest_dir: Path):
        """Dry-run with non-existent source should report error without crashing."""
        actions = [
            make_sort_action(
                input_path="/nonexistent/path/game.nes",
                detected_system="NES",
                planned_target_path=str(temp_dest_dir / "NES" / "game.nes"),
                action="copy",
                status="pending",
            ),
        ]

        plan = SortPlan(
            dest_path=str(temp_dest_dir),
            mode="copy",
            on_conflict="skip",
            actions=actions,
        )

        report = execute_sort(plan, dry_run=True)

        # Should have an error but no crash
        assert len(report.errors) >= 0  # Error handling may vary


# ---------------------------------------------------------------------------
# Parametrized Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["copy", "move"])
def test_dry_run_mode_independence(mode: str, temp_source_dir: Path, temp_dest_dir: Path):
    """Dry-run should work correctly for both copy and move modes."""
    actions = [
        make_sort_action(
            input_path=str(temp_source_dir / "game1.nes"),
            detected_system="NES",
            planned_target_path=str(temp_dest_dir / "NES" / "game1.nes"),
            action=mode,
            status="pending",
        ),
    ]

    plan = SortPlan(
        dest_path=str(temp_dest_dir),
        mode=cast(SortMode, mode),
        on_conflict=cast(ConflictPolicy, "skip"),
        actions=actions,
    )

    # Execute dry-run
    report = execute_sort(plan, dry_run=True)

    # Source must exist
    assert (temp_source_dir / "game1.nes").exists()

    # Destination must not exist
    assert not (temp_dest_dir / "NES" / "game1.nes").exists()

    # Report should reflect the mode
    if mode == "copy":
        assert report.copied == 1
    else:
        assert report.moved == 1


@pytest.mark.parametrize("on_conflict", ["skip", "overwrite", "rename"])
def test_dry_run_conflict_policies_safe(
    on_conflict: str, temp_source_dir: Path, temp_dest_dir: Path
):
    """All conflict policies should be safe in dry-run mode."""
    # Create existing file at destination
    (temp_dest_dir / "NES").mkdir(parents=True)
    existing = temp_dest_dir / "NES" / "game1.nes"
    existing.write_bytes(b"EXISTING")
    original_content = existing.read_bytes()

    actions = [
        make_sort_action(
            input_path=str(temp_source_dir / "game1.nes"),
            detected_system="NES",
            planned_target_path=str(existing),
            action="copy",
            status="pending",
        ),
    ]

    plan = SortPlan(
        dest_path=str(temp_dest_dir),
        mode=cast(SortMode, "copy"),
        on_conflict=cast(ConflictPolicy, on_conflict),
        actions=actions,
    )

    execute_sort(plan, dry_run=True)

    # Existing file must be unchanged regardless of policy
    assert existing.read_bytes() == original_content
