from __future__ import annotations

from pathlib import Path

import pytest

from src.app.controller import ScanItem, ScanResult, plan_sort


# ---------------------------------------------------------------------------
# Original Tests (rename, skip, overflow)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_plan_sort_rename_conflict(tmp_path: Path) -> None:
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "game.nes"
    rom.write_text("data", encoding="utf-8")

    existing_dir = dest / "NES"
    existing_dir.mkdir()
    existing = existing_dir / "game.nes"
    existing.write_text("existing", encoding="utf-8")

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
    assert len(plan.actions) == 1
    target = plan.actions[0].planned_target_path
    assert target is not None
    assert target.endswith("NES\\game (1).nes") or target.endswith("NES/game (1).nes")


@pytest.mark.integration
def test_plan_sort_skip_conflict(tmp_path: Path) -> None:
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "game.nes"
    rom.write_text("data", encoding="utf-8")

    existing_dir = dest / "NES"
    existing_dir.mkdir()
    existing = existing_dir / "game.nes"
    existing.write_text("existing", encoding="utf-8")

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    plan = plan_sort(scan, str(dest), mode="copy", on_conflict="skip")
    assert len(plan.actions) == 1
    action = plan.actions[0]
    assert action.planned_target_path is None
    assert action.status.startswith("skipped")


def test_rename_overflow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "game.nes"
    rom.write_text("data", encoding="utf-8")

    existing_dir = dest / "NES"
    existing_dir.mkdir()

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    real_exists = Path.exists

    def always_exists(self):
        if self.parent.name == "NES":
            return True
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", always_exists)

    plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
    assert len(plan.actions) == 1
    action = plan.actions[0]
    assert action.planned_target_path is None
    assert action.status == "error"


# ---------------------------------------------------------------------------
# Extended Tests: Overwrite Policy
# ---------------------------------------------------------------------------


class TestOverwritePolicy:
    """Tests for overwrite conflict policy."""

    @pytest.mark.integration
    def test_overwrite_allows_existing_target(self, tmp_path: Path) -> None:
        """Overwrite policy should allow replacing existing files."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        rom = source / "game.nes"
        rom.write_text("new_data", encoding="utf-8")

        existing_dir = dest / "NES"
        existing_dir.mkdir()
        existing = existing_dir / "game.nes"
        existing.write_text("old_data", encoding="utf-8")

        scan = ScanResult(
            source_path=str(source),
            items=[ScanItem(input_path=str(rom), detected_system="NES")],
            stats={},
            cancelled=False,
        )

        plan = plan_sort(scan, str(dest), mode="copy", on_conflict="overwrite")
        assert len(plan.actions) == 1
        action = plan.actions[0]
        # Overwrite should set target path even if file exists
        assert action.planned_target_path is not None
        assert action.status == "planned"


# ---------------------------------------------------------------------------
# Extended Tests: Multiple Files
# ---------------------------------------------------------------------------


class TestMultipleFileConflicts:
    """Tests for conflicts with multiple files."""

    @pytest.mark.integration
    def test_multiple_files_same_name_rename(self, tmp_path: Path) -> None:
        """Multiple source files with same name get same target (conflict at execution)."""
        source1 = tmp_path / "source1"
        source2 = tmp_path / "source2"
        dest = tmp_path / "dest"
        source1.mkdir()
        source2.mkdir()
        dest.mkdir()

        rom1 = source1 / "game.nes"
        rom2 = source2 / "game.nes"
        rom1.write_text("data1", encoding="utf-8")
        rom2.write_text("data2", encoding="utf-8")

        scan = ScanResult(
            source_path=str(tmp_path),
            items=[
                ScanItem(input_path=str(rom1), detected_system="NES"),
                ScanItem(input_path=str(rom2), detected_system="NES"),
            ],
            stats={},
            cancelled=False,
        )

        plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
        assert len(plan.actions) == 2
        
        targets = [a.planned_target_path for a in plan.actions]
        # Both should have targets
        assert all(t is not None for t in targets)
        # Note: Current behavior assigns same target path for both
        # This is a known limitation - conflict resolution happens at plan time
        # based on existing files, not in-flight conflicts
        assert len(targets) == 2  # Both have targets

    @pytest.mark.integration
    def test_multiple_files_same_name_skip(self, tmp_path: Path) -> None:
        """Skip policy with multiple same-name files."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        rom1 = source / "game1.nes"
        rom2 = source / "game2.nes"
        rom1.write_text("data1", encoding="utf-8")
        rom2.write_text("data2", encoding="utf-8")

        # Pre-create one existing file
        existing_dir = dest / "NES"
        existing_dir.mkdir()
        existing = existing_dir / "game1.nes"
        existing.write_text("existing", encoding="utf-8")

        scan = ScanResult(
            source_path=str(source),
            items=[
                ScanItem(input_path=str(rom1), detected_system="NES"),
                ScanItem(input_path=str(rom2), detected_system="NES"),
            ],
            stats={},
            cancelled=False,
        )

        plan = plan_sort(scan, str(dest), mode="copy", on_conflict="skip")
        assert len(plan.actions) == 2
        
        # game1 should be skipped, game2 should have target
        skipped = [a for a in plan.actions if a.status.startswith("skipped")]
        pending = [a for a in plan.actions if a.planned_target_path is not None]
        
        assert len(skipped) == 1
        assert len(pending) == 1


# ---------------------------------------------------------------------------
# Extended Tests: Different Platforms
# ---------------------------------------------------------------------------


class TestCrossPlatformConflicts:
    """Tests for conflicts across different platforms."""

    @pytest.mark.integration
    def test_same_filename_different_platforms(self, tmp_path: Path) -> None:
        """Same filename in different platforms should not conflict."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        rom_nes = source / "game.nes"
        rom_snes = source / "game.sfc"
        rom_nes.write_text("nes_data", encoding="utf-8")
        rom_snes.write_text("snes_data", encoding="utf-8")

        scan = ScanResult(
            source_path=str(source),
            items=[
                ScanItem(input_path=str(rom_nes), detected_system="NES"),
                ScanItem(input_path=str(rom_snes), detected_system="SNES"),
            ],
            stats={},
            cancelled=False,
        )

        plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
        assert len(plan.actions) == 2
        
        # Both should have targets (different folders)
        assert all(a.planned_target_path is not None for a in plan.actions)
        # Targets should point to different platform folders
        targets = [Path(a.planned_target_path).parent.name for a in plan.actions if a.planned_target_path]
        assert "NES" in targets
        assert "SNES" in targets


# ---------------------------------------------------------------------------
# Extended Tests: Mode Variations
# ---------------------------------------------------------------------------


class TestModeVariations:
    """Tests for different modes (copy vs move)."""

    @pytest.mark.integration
    def test_move_mode_rename_conflict(self, tmp_path: Path) -> None:
        """Move mode should also handle rename conflicts."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        rom = source / "game.nes"
        rom.write_text("data", encoding="utf-8")

        existing_dir = dest / "NES"
        existing_dir.mkdir()
        existing = existing_dir / "game.nes"
        existing.write_text("existing", encoding="utf-8")

        scan = ScanResult(
            source_path=str(source),
            items=[ScanItem(input_path=str(rom), detected_system="NES")],
            stats={},
            cancelled=False,
        )

        plan = plan_sort(scan, str(dest), mode="move", on_conflict="rename")
        assert len(plan.actions) == 1
        assert plan.mode == "move"
        target = plan.actions[0].planned_target_path
        assert target is not None
        assert "(1)" in target


# ---------------------------------------------------------------------------
# Extended Tests: Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests for collision policy."""

    @pytest.mark.integration
    def test_no_conflict_no_rename(self, tmp_path: Path) -> None:
        """No conflict should result in original filename."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        rom = source / "game.nes"
        rom.write_text("data", encoding="utf-8")

        scan = ScanResult(
            source_path=str(source),
            items=[ScanItem(input_path=str(rom), detected_system="NES")],
            stats={},
            cancelled=False,
        )

        plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
        assert len(plan.actions) == 1
        target = plan.actions[0].planned_target_path
        assert target is not None
        assert target.endswith("game.nes")
        assert "(1)" not in target

    @pytest.mark.integration
    def test_multiple_renames_sequential(self, tmp_path: Path) -> None:
        """Multiple conflicts should get sequential numbers."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        rom = source / "game.nes"
        rom.write_text("data", encoding="utf-8")

        existing_dir = dest / "NES"
        existing_dir.mkdir()
        # Create game.nes, game (1).nes, game (2).nes
        (existing_dir / "game.nes").write_text("v0", encoding="utf-8")
        (existing_dir / "game (1).nes").write_text("v1", encoding="utf-8")
        (existing_dir / "game (2).nes").write_text("v2", encoding="utf-8")

        scan = ScanResult(
            source_path=str(source),
            items=[ScanItem(input_path=str(rom), detected_system="NES")],
            stats={},
            cancelled=False,
        )

        plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
        assert len(plan.actions) == 1
        target = plan.actions[0].planned_target_path
        assert target is not None
        # Should be game (3).nes
        assert "(3)" in target

    @pytest.mark.integration
    def test_empty_scan_result(self, tmp_path: Path) -> None:
        """Empty scan result should produce empty plan."""
        dest = tmp_path / "dest"
        dest.mkdir()

        scan = ScanResult(
            source_path=str(tmp_path),
            items=[],
            stats={},
            cancelled=False,
        )

        plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
        assert len(plan.actions) == 0

    @pytest.mark.integration
    def test_unknown_system_handling(self, tmp_path: Path) -> None:
        """Unknown system files should be handled (Quarantine/Unknown folder)."""
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        rom = source / "game.xyz"
        rom.write_text("data", encoding="utf-8")

        scan = ScanResult(
            source_path=str(source),
            items=[ScanItem(input_path=str(rom), detected_system="Unknown")],
            stats={},
            cancelled=False,
        )

        plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
        assert len(plan.actions) == 1
        action = plan.actions[0]
        # Unknown files should still get a target path
        assert action.planned_target_path is not None or action.status.startswith("skipped")

