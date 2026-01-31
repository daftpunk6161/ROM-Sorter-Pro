from pathlib import Path

from src.app.scan_filtering import filter_scan_items
from src.app.models import ScanItem
from src.config import Config


def test_preferred_region_chain_respects_config(tmp_path: Path) -> None:
    rom_usa = tmp_path / "Game (USA).rom"
    rom_eur = tmp_path / "Game (Europe).rom"
    rom_usa.write_text("x")
    rom_eur.write_text("x")

    items = [
        ScanItem(input_path=str(rom_eur), detected_system="SNES", region="Europe"),
        ScanItem(input_path=str(rom_usa), detected_system="SNES", region="USA"),
    ]

    cfg = Config({"prioritization": {"region_priorities": {"USA": 0, "Europe": 1}}})
    filtered = filter_scan_items(items, dedupe_variants=True, config=cfg)

    assert len(filtered) == 1
    assert "USA" in str(filtered[0].input_path)


def test_revision_comparator_prefers_newer(tmp_path: Path) -> None:
    rom_v1 = tmp_path / "Game (USA) v1.0.rom"
    rom_v2 = tmp_path / "Game (USA) v1.1.rom"
    rom_v1.write_text("x")
    rom_v2.write_text("x")

    items = [
        ScanItem(input_path=str(rom_v1), detected_system="SNES", region="USA", version="v1.0"),
        ScanItem(input_path=str(rom_v2), detected_system="SNES", region="USA", version="v1.1"),
    ]

    cfg = Config({"prioritization": {"region_priorities": {"USA": 0}}})
    filtered = filter_scan_items(items, dedupe_variants=True, config=cfg)

    assert len(filtered) == 1
    assert "v1.1" in str(filtered[0].input_path)