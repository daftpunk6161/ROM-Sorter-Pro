from pathlib import Path

from src.app.controller import ScanItem, suggest_identification_overrides


def test_suggest_identification_overrides(tmp_path: Path) -> None:
    rom_a = tmp_path / "Game (USA).rom"
    rom_b = tmp_path / "Game (Europe).rom"
    rom_c = tmp_path / "Other.rom"
    for rom in (rom_a, rom_b, rom_c):
        rom.write_text("x")

    items = [
        ScanItem(input_path=str(rom_a), detected_system="Unknown"),
        ScanItem(input_path=str(rom_b), detected_system="Unknown"),
        ScanItem(input_path=str(rom_c), detected_system="Unknown"),
    ]

    suggestions = suggest_identification_overrides(str(rom_a), items)

    assert str(rom_b) in suggestions
    assert str(rom_c) not in suggestions