"""Tests for plan determinism and dry-run invariants.

These tests verify:
1. Same input always produces the same plan (determinism)
2. Dry-run mode never writes any files
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import List

import pytest

from src.app.controller import (
    CancelToken,
    ScanItem,
    ScanResult,
    SortAction,
    SortPlan,
    execute_sort,
    plan_sort,
)
from src.config import Config


class TestPlanDeterminism:
    """Tests for deterministic plan generation."""

    def test_same_input_same_output_basic(self, tmp_path: Path) -> None:
        """Same scan result should always produce the same plan."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create some ROM files
        (src_dir / "game_a.nes").write_bytes(b"\x00" * 100)
        (src_dir / "game_b.nes").write_bytes(b"\x00" * 100)
        (src_dir / "game_c.gba").write_bytes(b"\x00" * 100)

        scan = ScanResult(
            source_path=str(src_dir),
            items=[
                ScanItem(
                    input_path=str(src_dir / "game_a.nes"),
                    detected_system="NES",
                    detection_source="manual",
                    detection_confidence=1.0,
                    is_exact=True,
                ),
                ScanItem(
                    input_path=str(src_dir / "game_b.nes"),
                    detected_system="NES",
                    detection_source="manual",
                    detection_confidence=1.0,
                    is_exact=True,
                ),
                ScanItem(
                    input_path=str(src_dir / "game_c.gba"),
                    detected_system="GBA",
                    detection_source="manual",
                    detection_confidence=1.0,
                    is_exact=True,
                ),
            ],
            stats={},
            cancelled=False,
        )

        dest = tmp_path / "dest"
        cfg = Config({"features": {"sorting": {"create_console_folders": True}}})

        # Run plan_sort 10 times
        plans: List[SortPlan] = []
        for _ in range(10):
            plan = plan_sort(scan, str(dest), config=cfg, mode="copy", on_conflict="rename")
            plans.append(plan)

        # All plans should be identical
        first_plan = plans[0]
        for i, plan in enumerate(plans[1:], start=2):
            assert len(plan.actions) == len(first_plan.actions), f"Plan {i} has different action count"
            for j, (a, b) in enumerate(zip(plan.actions, first_plan.actions)):
                assert a.input_path == b.input_path, f"Plan {i} action {j} input_path differs"
                assert a.planned_target_path == b.planned_target_path, f"Plan {i} action {j} target differs"
                assert a.action == b.action, f"Plan {i} action {j} action differs"
                assert a.status == b.status, f"Plan {i} action {j} status differs"

    def test_determinism_with_shuffled_input(self, tmp_path: Path) -> None:
        """Plan should be deterministic regardless of scan item order."""
        import random

        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create files
        files = [f"rom_{i:03d}.nes" for i in range(20)]
        for f in files:
            (src_dir / f).write_bytes(b"\x00" * 100)

        # Create scan items in shuffled orders
        base_items = [
            ScanItem(
                input_path=str(src_dir / f),
                detected_system="NES",
                detection_source="manual",
                detection_confidence=1.0,
                is_exact=True,
            )
            for f in files
        ]

        dest = tmp_path / "dest"
        cfg = Config({"features": {"sorting": {"create_console_folders": True}}})

        plans: List[SortPlan] = []
        for seed in range(5):
            items = list(base_items)
            random.seed(seed)
            random.shuffle(items)

            scan = ScanResult(
                source_path=str(src_dir),
                items=items,
                stats={},
                cancelled=False,
            )

            plan = plan_sort(scan, str(dest), config=cfg, mode="copy", on_conflict="rename")
            plans.append(plan)

        # All plans should produce same actions (sorted by input_path internally)
        first_actions = [(a.input_path, a.planned_target_path) for a in plans[0].actions]
        for i, plan in enumerate(plans[1:], start=2):
            actions = [(a.input_path, a.planned_target_path) for a in plan.actions]
            assert actions == first_actions, f"Plan {i} differs from first plan"

    def test_determinism_with_conflict_rename(self, tmp_path: Path) -> None:
        """Rename numbering should be deterministic."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create files that will have same target name
        for i in range(5):
            subdir = src_dir / f"folder_{i}"
            subdir.mkdir()
            (subdir / "game.nes").write_bytes(b"\x00" * (100 + i))

        items = [
            ScanItem(
                input_path=str(src_dir / f"folder_{i}" / "game.nes"),
                detected_system="NES",
                detection_source="manual",
                detection_confidence=1.0,
                is_exact=True,
            )
            for i in range(5)
        ]

        dest = tmp_path / "dest"
        cfg = Config({"features": {"sorting": {"create_console_folders": True}}})

        # Create first file to trigger rename logic
        (dest / "NES").mkdir(parents=True)
        (dest / "NES" / "game.nes").write_bytes(b"\x00" * 50)

        plans: List[SortPlan] = []
        for _ in range(5):
            scan = ScanResult(
                source_path=str(src_dir),
                items=items,
                stats={},
                cancelled=False,
            )
            plan = plan_sort(scan, str(dest), config=cfg, mode="copy", on_conflict="rename")
            plans.append(plan)

        # Check all plans have same targets
        first_targets = sorted(a.planned_target_path for a in plans[0].actions if a.planned_target_path)
        for i, plan in enumerate(plans[1:], start=2):
            targets = sorted(a.planned_target_path for a in plan.actions if a.planned_target_path)
            assert targets == first_targets, f"Plan {i} has different rename numbering"


class TestDryRunInvariant:
    """Tests for dry-run mode guaranteeing zero writes."""

    def test_dry_run_creates_no_files(self, tmp_path: Path) -> None:
        """Dry-run should not create any files or directories."""
        src = tmp_path / "source.txt"
        src.write_text("data")

        dest_root = tmp_path / "dest"
        # Do NOT create dest_root - let's see if dry_run creates it

        plan = SortPlan(
            dest_path=str(dest_root),
            mode="copy",
            on_conflict="rename",
            actions=[
                SortAction(
                    input_path=str(src),
                    detected_system="NES",
                    planned_target_path=str(dest_root / "NES" / "source.txt"),
                    action="copy",
                    status="planned",
                )
            ],
        )

        report = execute_sort(plan, dry_run=True)

        assert report.processed == 1
        assert not dest_root.exists(), "Dry-run created destination directory"

    def test_dry_run_does_not_copy(self, tmp_path: Path) -> None:
        """Dry-run should not copy files."""
        src = tmp_path / "source.txt"
        src.write_text("original content")

        dest_root = tmp_path / "dest"
        dest_root.mkdir()

        target = dest_root / "target.txt"

        plan = SortPlan(
            dest_path=str(dest_root),
            mode="copy",
            on_conflict="overwrite",
            actions=[
                SortAction(
                    input_path=str(src),
                    detected_system="Unknown",
                    planned_target_path=str(target),
                    action="copy",
                    status="planned",
                )
            ],
        )

        report = execute_sort(plan, dry_run=True)

        assert report.processed == 1
        assert report.copied == 1  # Counted as "would copy"
        assert not target.exists(), "Dry-run actually copied the file"
        assert src.exists(), "Source file was unexpectedly deleted"

    def test_dry_run_does_not_move(self, tmp_path: Path) -> None:
        """Dry-run should not move files."""
        src = tmp_path / "source.txt"
        src.write_text("original content")

        dest_root = tmp_path / "dest"
        dest_root.mkdir()

        target = dest_root / "target.txt"

        plan = SortPlan(
            dest_path=str(dest_root),
            mode="move",
            on_conflict="overwrite",
            actions=[
                SortAction(
                    input_path=str(src),
                    detected_system="Unknown",
                    planned_target_path=str(target),
                    action="move",
                    status="planned",
                )
            ],
        )

        report = execute_sort(plan, dry_run=True)

        assert report.processed == 1
        assert report.moved == 1  # Counted as "would move"
        assert not target.exists(), "Dry-run actually created target"
        assert src.exists(), "Dry-run actually deleted source"
        assert src.read_text() == "original content", "Source content changed"

    def test_dry_run_does_not_overwrite(self, tmp_path: Path) -> None:
        """Dry-run should not overwrite existing files."""
        src = tmp_path / "source.txt"
        src.write_text("new content")

        dest_root = tmp_path / "dest"
        dest_root.mkdir()

        target = dest_root / "target.txt"
        target.write_text("existing content")

        plan = SortPlan(
            dest_path=str(dest_root),
            mode="copy",
            on_conflict="overwrite",
            actions=[
                SortAction(
                    input_path=str(src),
                    detected_system="Unknown",
                    planned_target_path=str(target),
                    action="copy",
                    status="planned",
                )
            ],
        )

        report = execute_sort(plan, dry_run=True)

        assert target.read_text() == "existing content", "Dry-run overwrote existing file"

    def test_dry_run_does_not_delete_source(self, tmp_path: Path) -> None:
        """Dry-run move should not delete source."""
        src = tmp_path / "source.txt"
        src.write_text("content")

        dest_root = tmp_path / "dest"
        dest_root.mkdir()

        plan = SortPlan(
            dest_path=str(dest_root),
            mode="move",
            on_conflict="rename",
            actions=[
                SortAction(
                    input_path=str(src),
                    detected_system="Unknown",
                    planned_target_path=str(dest_root / "target.txt"),
                    action="move",
                    status="planned",
                )
            ],
        )

        report = execute_sort(plan, dry_run=True)

        assert src.exists(), "Dry-run deleted source file"

    def test_dry_run_conversion_no_external_tools(self, tmp_path: Path, monkeypatch) -> None:
        """Dry-run conversion should not invoke external tools."""
        import src.app.controller as controller

        tool_called = {"count": 0}

        def fake_run(*args, **kwargs):
            tool_called["count"] += 1
            return True, False

        monkeypatch.setattr(controller, "run_conversion_with_cancel", fake_run)

        src = tmp_path / "source.wud"
        src.write_bytes(b"\x00" * 1024)

        dest_root = tmp_path / "dest"
        dest_root.mkdir()

        plan = SortPlan(
            dest_path=str(dest_root),
            mode="copy",
            on_conflict="rename",
            actions=[
                SortAction(
                    input_path=str(src),
                    detected_system="WiiU",
                    planned_target_path=str(dest_root / "output.wux"),
                    action="convert",
                    status="planned",
                    conversion_tool="wudcompress",
                    conversion_tool_key="wudcompress",
                    conversion_args=["--fake"],
                )
            ],
        )

        report = execute_sort(plan, dry_run=True)

        assert tool_called["count"] == 0, "Dry-run invoked external conversion tool"
        assert not (dest_root / "output.wux").exists(), "Dry-run created conversion output"

    def test_dry_run_counts_correctly(self, tmp_path: Path) -> None:
        """Dry-run should correctly count operations."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        for i in range(5):
            (src_dir / f"file_{i}.txt").write_text(f"content {i}")

        dest_root = tmp_path / "dest"

        actions = [
            SortAction(
                input_path=str(src_dir / f"file_{i}.txt"),
                detected_system="Unknown",
                planned_target_path=str(dest_root / f"file_{i}.txt"),
                action="copy",
                status="planned",
            )
            for i in range(5)
        ]

        plan = SortPlan(
            dest_path=str(dest_root),
            mode="copy",
            on_conflict="rename",
            actions=actions,
        )

        report = execute_sort(plan, dry_run=True)

        assert report.processed == 5
        assert report.copied == 5
        assert len(report.errors) == 0
        assert not dest_root.exists()


class TestDryRunWithCancel:
    """Tests for dry-run combined with cancellation."""

    def test_dry_run_respects_cancel_token(self, tmp_path: Path) -> None:
        """Dry-run should still respect cancel token."""
        src = tmp_path / "source.txt"
        src.write_text("data")

        dest_root = tmp_path / "dest"

        plan = SortPlan(
            dest_path=str(dest_root),
            mode="copy",
            on_conflict="rename",
            actions=[
                SortAction(
                    input_path=str(src),
                    detected_system="Unknown",
                    planned_target_path=str(dest_root / "target.txt"),
                    action="copy",
                    status="planned",
                )
            ],
        )

        token = CancelToken()
        token.cancel()

        report = execute_sort(plan, dry_run=True, cancel_token=token)

        assert report.cancelled is True
        assert report.processed == 0


class TestIntegrationPlanExecuteDryRun:
    """Integration tests for plan → execute (dry_run) flow."""

    def test_full_flow_dry_run(self, tmp_path: Path) -> None:
        """Full scan → plan → execute(dry_run) should leave filesystem unchanged."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        rom1 = src_dir / "game.nes"
        rom2 = src_dir / "other.gba"
        rom1.write_bytes(b"\x00" * 100)
        rom2.write_bytes(b"\x00" * 200)

        dest = tmp_path / "dest"

        # Record filesystem state before
        before_files = set(str(p) for p in tmp_path.rglob("*") if p.is_file())

        scan = ScanResult(
            source_path=str(src_dir),
            items=[
                ScanItem(
                    input_path=str(rom1),
                    detected_system="NES",
                    detection_source="manual",
                    detection_confidence=1.0,
                    is_exact=True,
                ),
                ScanItem(
                    input_path=str(rom2),
                    detected_system="GBA",
                    detection_source="manual",
                    detection_confidence=1.0,
                    is_exact=True,
                ),
            ],
            stats={},
            cancelled=False,
        )

        cfg = Config({"features": {"sorting": {"create_console_folders": True}}})
        plan = plan_sort(scan, str(dest), config=cfg, mode="copy", on_conflict="rename")

        report = execute_sort(plan, dry_run=True)

        # Record filesystem state after
        after_files = set(str(p) for p in tmp_path.rglob("*") if p.is_file())

        assert before_files == after_files, "Dry-run modified filesystem"
        assert report.processed == 2
        assert report.copied == 2
        assert len(report.errors) == 0
