"""Save State Manager - F85 Implementation.

Organizes and manages emulator save states.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class SaveStateSlot(Enum):
    """Standard save state slots."""

    SLOT_0 = 0
    SLOT_1 = 1
    SLOT_2 = 2
    SLOT_3 = 3
    SLOT_4 = 4
    SLOT_5 = 5
    SLOT_6 = 6
    SLOT_7 = 7
    SLOT_8 = 8
    SLOT_9 = 9
    QUICK = 100
    AUTO = 101


@dataclass
class SaveState:
    """Represents a save state."""

    path: str
    slot: SaveStateSlot
    rom_path: str
    rom_name: str
    timestamp: float
    size_bytes: int
    screenshot_path: Optional[str] = None
    notes: str = ""
    emulator: str = ""
    core: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def created_at(self) -> datetime:
        """Get creation datetime."""
        return datetime.fromtimestamp(self.timestamp)

    @property
    def size_kb(self) -> float:
        """Get size in KB."""
        return self.size_bytes / 1024

    @property
    def display_name(self) -> str:
        """Get display name."""
        slot_name = f"Slot {self.slot.value}" if self.slot.value < 100 else self.slot.name
        return f"{self.rom_name} - {slot_name}"


class SaveStateManager:
    """Manages save states for ROMs.

    Implements F85: Save-State-Manager

    Features:
    - Organize save states by ROM
    - Backup and restore
    - Transfer between slots
    - Screenshot management
    - Metadata tracking
    """

    # Common save state extensions
    SAVE_STATE_EXTENSIONS = [
        ".state", ".state0", ".state1", ".state2", ".state3",
        ".state4", ".state5", ".state6", ".state7", ".state8",
        ".state9", ".state.auto", ".ss0", ".ss1", ".ss2",
        ".sav", ".srm", ".savestate", ".sta", ".st0",
    ]

    SCREENSHOT_EXTENSIONS = [".png", ".bmp", ".jpg", ".jpeg"]

    def __init__(
        self,
        states_directory: str,
        backup_directory: Optional[str] = None,
    ):
        """Initialize save state manager.

        Args:
            states_directory: Root directory for save states
            backup_directory: Directory for backups
        """
        self._states_dir = Path(states_directory)
        self._backup_dir = Path(backup_directory) if backup_directory else None
        self._states_dir.mkdir(parents=True, exist_ok=True)

        if self._backup_dir:
            self._backup_dir.mkdir(parents=True, exist_ok=True)

        self._metadata_file = self._states_dir / "states_metadata.json"
        self._metadata: Dict[str, Dict[str, Any]] = {}

        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load metadata from file."""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, "r", encoding="utf-8") as f:
                    self._metadata = json.load(f)
            except Exception:
                self._metadata = {}

    def _save_metadata(self) -> None:
        """Save metadata to file."""
        try:
            with open(self._metadata_file, "w", encoding="utf-8") as f:
                json.dump(self._metadata, f, indent=2)
        except Exception:
            pass

    def get_rom_directory(self, rom_path: str) -> Path:
        """Get save state directory for a ROM.

        Args:
            rom_path: Path to ROM

        Returns:
            Directory path
        """
        rom_name = Path(rom_path).stem
        # Sanitize name
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in rom_name)
        return self._states_dir / safe_name

    def list_states(
        self,
        rom_path: Optional[str] = None,
    ) -> List[SaveState]:
        """List save states.

        Args:
            rom_path: Filter by ROM (optional)

        Returns:
            List of save states
        """
        states: List[SaveState] = []

        if rom_path:
            search_dir = self.get_rom_directory(rom_path)
            if not search_dir.exists():
                return []
            search_dirs = [search_dir]
        else:
            search_dirs = [d for d in self._states_dir.iterdir() if d.is_dir()]

        for directory in search_dirs:
            for file_path in directory.iterdir():
                if file_path.suffix.lower() in self.SAVE_STATE_EXTENSIONS:
                    state = self._parse_state_file(file_path)
                    if state:
                        states.append(state)

        # Sort by timestamp
        return sorted(states, key=lambda s: s.timestamp, reverse=True)

    def _parse_state_file(self, file_path: Path) -> Optional[SaveState]:
        """Parse a save state file.

        Args:
            file_path: Path to state file

        Returns:
            SaveState or None
        """
        try:
            stat = file_path.stat()
            rom_name = file_path.parent.name

            # Determine slot
            slot = self._detect_slot(file_path)

            # Check for screenshot
            screenshot = self._find_screenshot(file_path)

            # Get metadata
            state_key = str(file_path)
            meta = self._metadata.get(state_key, {})

            return SaveState(
                path=str(file_path),
                slot=slot,
                rom_path=meta.get("rom_path", ""),
                rom_name=rom_name,
                timestamp=stat.st_mtime,
                size_bytes=stat.st_size,
                screenshot_path=screenshot,
                notes=meta.get("notes", ""),
                emulator=meta.get("emulator", ""),
                core=meta.get("core", ""),
                metadata=meta,
            )
        except Exception:
            return None

    def _detect_slot(self, file_path: Path) -> SaveStateSlot:
        """Detect save state slot from filename."""
        name = file_path.name.lower()

        if "auto" in name:
            return SaveStateSlot.AUTO
        if "quick" in name:
            return SaveStateSlot.QUICK

        # Check for slot number
        for i in range(10):
            if f".state{i}" in name or f".ss{i}" in name or f".st{i}" in name:
                return SaveStateSlot(i)

        return SaveStateSlot.SLOT_0

    def _find_screenshot(self, state_path: Path) -> Optional[str]:
        """Find screenshot for save state."""
        stem = state_path.stem
        directory = state_path.parent

        for ext in self.SCREENSHOT_EXTENSIONS:
            screenshot = directory / f"{stem}{ext}"
            if screenshot.exists():
                return str(screenshot)

        return None

    def create_state_entry(
        self,
        rom_path: str,
        slot: SaveStateSlot,
        emulator: str = "",
        core: str = "",
        notes: str = "",
    ) -> Path:
        """Create entry for new save state.

        Args:
            rom_path: Path to ROM
            slot: Save slot
            emulator: Emulator name
            core: Core name
            notes: User notes

        Returns:
            Path where state should be saved
        """
        directory = self.get_rom_directory(rom_path)
        directory.mkdir(parents=True, exist_ok=True)

        rom_name = Path(rom_path).stem

        if slot == SaveStateSlot.AUTO:
            state_name = f"{rom_name}.state.auto"
        elif slot == SaveStateSlot.QUICK:
            state_name = f"{rom_name}.state.quick"
        else:
            state_name = f"{rom_name}.state{slot.value}"

        state_path = directory / state_name

        # Store metadata
        state_key = str(state_path)
        self._metadata[state_key] = {
            "rom_path": rom_path,
            "emulator": emulator,
            "core": core,
            "notes": notes,
            "created": time.time(),
        }
        self._save_metadata()

        return state_path

    def backup_state(self, state: SaveState, notes: str = "") -> Optional[str]:
        """Backup a save state.

        Args:
            state: State to backup
            notes: Backup notes

        Returns:
            Backup path or None
        """
        if not self._backup_dir:
            return None

        if not Path(state.path).exists():
            return None

        # Create backup name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{state.rom_name}_{state.slot.name}_{timestamp}"

        backup_path = self._backup_dir / state.rom_name
        backup_path.mkdir(parents=True, exist_ok=True)

        dest = backup_path / f"{backup_name}.state"

        try:
            shutil.copy2(state.path, dest)

            # Also backup screenshot if exists
            if state.screenshot_path and Path(state.screenshot_path).exists():
                ss_ext = Path(state.screenshot_path).suffix
                shutil.copy2(state.screenshot_path, backup_path / f"{backup_name}{ss_ext}")

            # Store backup metadata
            meta_path = backup_path / f"{backup_name}.meta.json"
            meta = {
                "original_path": state.path,
                "rom_path": state.rom_path,
                "slot": state.slot.value,
                "notes": notes,
                "backup_time": time.time(),
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)

            return str(dest)
        except Exception:
            return None

    def restore_backup(
        self,
        backup_path: str,
        target_slot: Optional[SaveStateSlot] = None,
    ) -> Optional[SaveState]:
        """Restore a backup.

        Args:
            backup_path: Path to backup
            target_slot: Slot to restore to

        Returns:
            Restored SaveState or None
        """
        if not Path(backup_path).exists():
            return None

        # Read backup metadata
        meta_path = Path(backup_path).with_suffix(".meta.json")
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}
        else:
            meta = {}

        rom_path = meta.get("rom_path", "")
        original_slot = meta.get("slot")

        if target_slot is None:
            if original_slot is not None:
                target_slot = SaveStateSlot(original_slot)
            else:
                target_slot = SaveStateSlot.SLOT_0

        if not rom_path:
            return None

        # Create destination
        dest = self.create_state_entry(
            rom_path,
            target_slot,
            emulator=meta.get("emulator", ""),
            core=meta.get("core", ""),
            notes=f"Restored from backup: {meta.get('notes', '')}",
        )

        try:
            shutil.copy2(backup_path, dest)

            # Return the new state
            return self._parse_state_file(dest)
        except Exception:
            return None

    def delete_state(self, state: SaveState, backup_first: bool = True) -> bool:
        """Delete a save state.

        Args:
            state: State to delete
            backup_first: Create backup before delete

        Returns:
            True if deleted
        """
        if not Path(state.path).exists():
            return False

        if backup_first:
            self.backup_state(state, "Auto-backup before delete")

        try:
            os.remove(state.path)

            # Also remove screenshot
            if state.screenshot_path and Path(state.screenshot_path).exists():
                os.remove(state.screenshot_path)

            # Remove metadata
            state_key = state.path
            if state_key in self._metadata:
                del self._metadata[state_key]
                self._save_metadata()

            return True
        except Exception:
            return False

    def copy_to_slot(
        self,
        state: SaveState,
        target_slot: SaveStateSlot,
    ) -> Optional[SaveState]:
        """Copy state to another slot.

        Args:
            state: Source state
            target_slot: Target slot

        Returns:
            New SaveState or None
        """
        if not Path(state.path).exists():
            return None

        dest = self.create_state_entry(
            state.rom_path,
            target_slot,
            emulator=state.emulator,
            core=state.core,
            notes=f"Copied from {state.slot.name}",
        )

        try:
            shutil.copy2(state.path, dest)

            # Copy screenshot
            if state.screenshot_path and Path(state.screenshot_path).exists():
                ss_ext = Path(state.screenshot_path).suffix
                ss_dest = dest.with_suffix(ss_ext)
                shutil.copy2(state.screenshot_path, ss_dest)

            return self._parse_state_file(dest)
        except Exception:
            return None

    def update_notes(self, state: SaveState, notes: str) -> bool:
        """Update notes for a state.

        Args:
            state: State to update
            notes: New notes

        Returns:
            True if updated
        """
        state_key = state.path
        if state_key not in self._metadata:
            self._metadata[state_key] = {}

        self._metadata[state_key]["notes"] = notes
        self._save_metadata()
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get save state statistics.

        Returns:
            Statistics dict
        """
        states = self.list_states()

        total_size = sum(s.size_bytes for s in states)
        roms_with_states = len(set(s.rom_name for s in states))

        return {
            "total_states": len(states),
            "total_size_mb": total_size / (1024 * 1024),
            "roms_with_states": roms_with_states,
            "oldest_state": min((s.timestamp for s in states), default=None),
            "newest_state": max((s.timestamp for s in states), default=None),
            "slots_usage": {
                slot.name: sum(1 for s in states if s.slot == slot)
                for slot in SaveStateSlot
            },
        }

    def cleanup_orphans(self) -> int:
        """Remove save states for non-existent ROMs.

        Returns:
            Number of states removed
        """
        removed = 0
        states = self.list_states()

        for state in states:
            if state.rom_path and not Path(state.rom_path).exists():
                if self.delete_state(state, backup_first=True):
                    removed += 1

        return removed
