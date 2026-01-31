"""Emulator Launcher - F83 Implementation.

Provides direct ROM launch capabilities with configured emulators.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class EmulatorType(Enum):
    """Known emulator types."""

    RETROARCH = "retroarch"
    MESEN = "mesen"
    SNES9X = "snes9x"
    FCEUX = "fceux"
    MGBA = "mgba"
    DUCKSTATION = "duckstation"
    PCSX2 = "pcsx2"
    DOLPHIN = "dolphin"
    CEMU = "cemu"
    YUZU = "yuzu"
    RYUJINX = "ryujinx"
    PPSSPP = "ppsspp"
    DESMUME = "desmume"
    MELONDS = "melonds"
    RPCS3 = "rpcs3"
    XEMU = "xemu"
    CITRA = "citra"
    CUSTOM = "custom"


@dataclass
class LaunchConfig:
    """Configuration for launching a ROM."""

    emulator_path: str
    rom_path: str
    core_path: Optional[str] = None
    arguments: List[str] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    working_directory: Optional[str] = None
    fullscreen: bool = False
    wait_for_exit: bool = False
    timeout: Optional[float] = None


@dataclass
class LaunchResult:
    """Result of a launch operation."""

    success: bool
    process_id: Optional[int] = None
    return_code: Optional[int] = None
    error_message: Optional[str] = None
    launch_time: float = 0.0
    runtime: Optional[float] = None


class EmulatorLauncher:
    """Emulator launcher for direct ROM start.

    Implements F83: ROM-Direkt-Start

    Features:
    - Launch ROMs with configured emulators
    - Support for RetroArch and standalone emulators
    - Custom command-line arguments
    - Process management
    """

    # Default arguments for known emulators
    EMULATOR_DEFAULTS: Dict[EmulatorType, Dict[str, Any]] = {
        EmulatorType.RETROARCH: {
            "fullscreen_arg": "--fullscreen",
            "rom_arg": None,  # ROM is last argument
            "core_arg": "-L",
        },
        EmulatorType.MESEN: {
            "fullscreen_arg": "--fullscreen",
            "rom_arg": None,
        },
        EmulatorType.SNES9X: {
            "fullscreen_arg": "-fullscreen",
            "rom_arg": None,
        },
        EmulatorType.MGBA: {
            "fullscreen_arg": "-f",
            "rom_arg": None,
        },
        EmulatorType.DUCKSTATION: {
            "fullscreen_arg": "-fullscreen",
            "rom_arg": "--",
        },
        EmulatorType.DOLPHIN: {
            "fullscreen_arg": "--config=Dolphin.Display.Fullscreen=True",
            "rom_arg": "-e",
        },
        EmulatorType.PPSSPP: {
            "fullscreen_arg": "--fullscreen",
            "rom_arg": None,
        },
        EmulatorType.MELONDS: {
            "fullscreen_arg": "-f",
            "rom_arg": None,
        },
    }

    def __init__(self):
        """Initialize emulator launcher."""
        self._processes: Dict[int, subprocess.Popen] = {}

    def detect_emulator_type(self, emulator_path: str) -> EmulatorType:
        """Detect emulator type from path.

        Args:
            emulator_path: Path to emulator executable

        Returns:
            Detected EmulatorType
        """
        path_lower = emulator_path.lower()
        name = Path(emulator_path).stem.lower()

        type_keywords = {
            EmulatorType.RETROARCH: ["retroarch"],
            EmulatorType.MESEN: ["mesen"],
            EmulatorType.SNES9X: ["snes9x"],
            EmulatorType.FCEUX: ["fceux"],
            EmulatorType.MGBA: ["mgba", "m-gba"],
            EmulatorType.DUCKSTATION: ["duckstation"],
            EmulatorType.PCSX2: ["pcsx2"],
            EmulatorType.DOLPHIN: ["dolphin"],
            EmulatorType.CEMU: ["cemu"],
            EmulatorType.YUZU: ["yuzu"],
            EmulatorType.RYUJINX: ["ryujinx"],
            EmulatorType.PPSSPP: ["ppsspp"],
            EmulatorType.DESMUME: ["desmume"],
            EmulatorType.MELONDS: ["melonds"],
            EmulatorType.RPCS3: ["rpcs3"],
            EmulatorType.XEMU: ["xemu"],
            EmulatorType.CITRA: ["citra"],
        }

        for emu_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in path_lower or keyword in name:
                    return emu_type

        return EmulatorType.CUSTOM

    def build_command(self, config: LaunchConfig) -> List[str]:
        """Build command line for emulator.

        Args:
            config: Launch configuration

        Returns:
            Command line arguments
        """
        command = [config.emulator_path]
        emu_type = self.detect_emulator_type(config.emulator_path)
        defaults = self.EMULATOR_DEFAULTS.get(emu_type, {})

        # Add core for RetroArch
        if config.core_path and emu_type == EmulatorType.RETROARCH:
            core_arg = defaults.get("core_arg", "-L")
            if core_arg:
                command.append(core_arg)
            command.append(config.core_path)

        # Add fullscreen
        if config.fullscreen:
            fs_arg = defaults.get("fullscreen_arg")
            if fs_arg:
                command.append(fs_arg)

        # Add custom arguments
        command.extend(config.arguments)

        # Add ROM path
        rom_arg = defaults.get("rom_arg")
        if rom_arg:
            command.append(rom_arg)
        command.append(config.rom_path)

        return command

    def launch(self, config: LaunchConfig) -> LaunchResult:
        """Launch ROM with emulator.

        Args:
            config: Launch configuration

        Returns:
            LaunchResult
        """
        start_time = time.time()

        # Validate paths
        if not Path(config.emulator_path).exists():
            return LaunchResult(
                success=False,
                error_message=f"Emulator not found: {config.emulator_path}",
                launch_time=time.time() - start_time,
            )

        if not Path(config.rom_path).exists():
            return LaunchResult(
                success=False,
                error_message=f"ROM not found: {config.rom_path}",
                launch_time=time.time() - start_time,
            )

        if config.core_path and not Path(config.core_path).exists():
            return LaunchResult(
                success=False,
                error_message=f"Core not found: {config.core_path}",
                launch_time=time.time() - start_time,
            )

        # Build command
        command = self.build_command(config)

        # Set up environment
        env = os.environ.copy()
        env.update(config.environment)

        # Set working directory
        cwd = config.working_directory
        if not cwd:
            cwd = str(Path(config.emulator_path).parent)

        try:
            # Launch process
            process = subprocess.Popen(
                command,
                env=env,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                if os.name == "nt"
                else 0,
            )

            self._processes[process.pid] = process
            launch_time = time.time() - start_time

            if config.wait_for_exit:
                try:
                    return_code = process.wait(timeout=config.timeout)
                    runtime = time.time() - start_time - launch_time
                    del self._processes[process.pid]

                    return LaunchResult(
                        success=return_code == 0,
                        process_id=process.pid,
                        return_code=return_code,
                        launch_time=launch_time,
                        runtime=runtime,
                    )
                except subprocess.TimeoutExpired:
                    return LaunchResult(
                        success=True,
                        process_id=process.pid,
                        error_message="Process still running (timeout)",
                        launch_time=launch_time,
                    )

            return LaunchResult(
                success=True,
                process_id=process.pid,
                launch_time=launch_time,
            )

        except FileNotFoundError as e:
            return LaunchResult(
                success=False,
                error_message=f"Emulator executable not found: {e}",
                launch_time=time.time() - start_time,
            )
        except PermissionError as e:
            return LaunchResult(
                success=False,
                error_message=f"Permission denied: {e}",
                launch_time=time.time() - start_time,
            )
        except Exception as e:
            return LaunchResult(
                success=False,
                error_message=f"Launch failed: {e}",
                launch_time=time.time() - start_time,
            )

    def launch_with_retroarch(
        self,
        rom_path: str,
        retroarch_path: str,
        core_path: str,
        fullscreen: bool = False,
        extra_args: Optional[List[str]] = None,
    ) -> LaunchResult:
        """Convenience method for RetroArch launch.

        Args:
            rom_path: Path to ROM
            retroarch_path: Path to RetroArch
            core_path: Path to libretro core
            fullscreen: Launch fullscreen
            extra_args: Additional arguments

        Returns:
            LaunchResult
        """
        config = LaunchConfig(
            emulator_path=retroarch_path,
            rom_path=rom_path,
            core_path=core_path,
            fullscreen=fullscreen,
            arguments=extra_args or [],
        )
        return self.launch(config)

    def launch_standalone(
        self,
        rom_path: str,
        emulator_path: str,
        fullscreen: bool = False,
        extra_args: Optional[List[str]] = None,
    ) -> LaunchResult:
        """Launch ROM with standalone emulator.

        Args:
            rom_path: Path to ROM
            emulator_path: Path to emulator
            fullscreen: Launch fullscreen
            extra_args: Additional arguments

        Returns:
            LaunchResult
        """
        config = LaunchConfig(
            emulator_path=emulator_path,
            rom_path=rom_path,
            fullscreen=fullscreen,
            arguments=extra_args or [],
        )
        return self.launch(config)

    def is_running(self, process_id: int) -> bool:
        """Check if launched process is still running.

        Args:
            process_id: Process ID

        Returns:
            True if running
        """
        if process_id not in self._processes:
            return False

        process = self._processes[process_id]
        return process.poll() is None

    def terminate(self, process_id: int) -> bool:
        """Terminate a launched process.

        Args:
            process_id: Process ID

        Returns:
            True if terminated
        """
        if process_id not in self._processes:
            return False

        process = self._processes[process_id]
        try:
            process.terminate()
            process.wait(timeout=5)
            del self._processes[process_id]
            return True
        except Exception:
            try:
                process.kill()
                del self._processes[process_id]
                return True
            except Exception:
                return False

    def get_running_processes(self) -> List[int]:
        """Get list of running process IDs.

        Returns:
            List of process IDs
        """
        running = []
        for pid, process in list(self._processes.items()):
            if process.poll() is None:
                running.append(pid)
            else:
                del self._processes[pid]
        return running

    def cleanup(self) -> int:
        """Terminate all running processes.

        Returns:
            Number of processes terminated
        """
        count = 0
        for pid in list(self._processes.keys()):
            if self.terminate(pid):
                count += 1
        return count
