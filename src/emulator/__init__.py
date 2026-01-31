"""Emulator Integration Module - F83-F86 Implementation.

Provides:
- F83: ROM-Direkt-Start (EmulatorLauncher)
- F84: Core-Zuordnung (CoreMapping)
- F85: Save-State-Manager (SaveStateManager)
- F86: Per-Game-Settings (GameSettings)
"""

from .emulator_launcher import EmulatorLauncher, LaunchConfig, LaunchResult
from .core_mapping import CoreMapping, CoreConfig, CoreMatch
from .save_state_manager import SaveStateManager, SaveState, SaveStateSlot
from .game_settings import GameSettings, GameConfig, SettingsScope

__all__ = [
    # F83
    "EmulatorLauncher",
    "LaunchConfig",
    "LaunchResult",
    # F84
    "CoreMapping",
    "CoreConfig",
    "CoreMatch",
    # F85
    "SaveStateManager",
    "SaveState",
    "SaveStateSlot",
    # F86
    "GameSettings",
    "GameConfig",
    "SettingsScope",
]
