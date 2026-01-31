import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_multi_library_persistence(tmp_path):
    from src.core.multi_library import MultiLibraryManager

    config_dir = tmp_path / "config"
    manager = MultiLibraryManager(config_dir=str(config_dir))
    created = manager.create_library("TestLib", "/roms/test")
    assert created.id
    assert manager.get_active_library() is not None

    reloaded = MultiLibraryManager(config_dir=str(config_dir))
    active = reloaded.get_active_library()
    assert active is not None
    assert active.name == "TestLib"
    assert active.path == "/roms/test"


def test_ai_normalizer_region_version_flags(tmp_path):
    from src.detectors.ai_normalizer import AINameNormalizer

    normalizer = AINameNormalizer(config_dir=str(tmp_path))
    result = normalizer.normalize("Super Mario (U) (v1.1) [b1].nes")
    assert "(USA)" in result.normalized
    assert "(Rev 1.1)" in result.normalized
    assert "Bad Dump" in result.normalized
    assert result.extracted_info.get("region") == "USA"


def test_boxart_preview_local_media(tmp_path):
    from src.ui.preview.boxart_preview import BoxartPreview

    media_root = tmp_path / "media"
    boxart_dir = media_root / "SNES" / "boxart"
    boxart_dir.mkdir(parents=True, exist_ok=True)
    boxart_path = boxart_dir / "Super Mario.png"
    boxart_path.write_bytes(b"fake-image")

    preview = BoxartPreview(cache_dir=str(tmp_path / "cache"), media_dirs=[str(media_root)])
    preview.register_rom("hash1", "Super Mario", "SNES")
    resolved = preview.get_boxart_path("hash1")
    assert resolved is not None
    assert Path(resolved).name == "Super Mario.png"


def test_badge_manager_unlocks_first_rom(tmp_path):
    from src.gamification.badges import BadgeManager

    manager = BadgeManager(config_dir=str(tmp_path))
    unlocked = manager.check_collection_badges(rom_count=1, systems_count=1, verified_count=0)
    assert any(badge.id == "first_rom" for badge in unlocked)
    stats = manager.get_stats()
    assert stats["unlocked_badges"] >= 1


def test_rom_verifier_detects_bad_dump(tmp_path):
    from src.verification.rom_verifier import RomVerifier, FlagType

    rom_path = tmp_path / "Game [b].rom"
    rom_path.write_bytes(b"test")

    verifier = RomVerifier(index=None)
    result = verifier.verify(str(rom_path))
    assert FlagType.BAD_DUMP in result.flag_types
    assert result.is_bad_dump


def test_emulator_launcher_builds_retroarch_command():
    from src.emulator.emulator_launcher import EmulatorLauncher, LaunchConfig

    launcher = EmulatorLauncher()
    config = LaunchConfig(
        emulator_path="retroarch.exe",
        rom_path="game.nes",
        core_path="core.dll",
        fullscreen=True,
    )
    command = launcher.build_command(config)
    assert "retroarch.exe" in command
    assert "-L" in command
    assert "core.dll" in command
    assert "--fullscreen" in command
    assert "game.nes" in command


def test_collection_dashboard_basic_stats():
    from src.analytics.collection_dashboard import CollectionDashboard

    roms = [
        {"path": "/roms/a.nes", "platform": "NES", "region": "USA", "size": 100, "verified": True},
        {"path": "/roms/b.nes", "platform": "NES", "region": "Japan", "size": 200, "verified": False},
    ]
    dashboard = CollectionDashboard()
    stats = dashboard.analyze(roms)
    assert stats.total_roms == 2
    assert stats.total_systems == 1
    assert stats.verified_roms == 1


def test_incremental_backup_detects_changes(tmp_path):
    from src.backup.incremental_backup import IncrementalBackup

    source = tmp_path / "source"
    backup = tmp_path / "backup"
    source.mkdir()
    (source / "game.rom").write_bytes(b"abc")

    backup_runner = IncrementalBackup(str(source), str(backup), use_hash=True)
    result1 = backup_runner.backup()
    assert result1.success
    assert result1.new_files == 1
    assert Path(result1.manifest_path).exists()

    result2 = backup_runner.backup()
    assert result2.success
    assert result2.unchanged_files >= 1
