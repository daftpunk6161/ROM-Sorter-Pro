from pathlib import Path

from src.scanning.high_performance_scanner import HighPerformanceScanner


def test_magic_bytes_detects_nes(tmp_path: Path) -> None:
    rom = tmp_path / "game.bin"
    rom.write_bytes(b"NES\x1a" + b"\x00" * 16)

    scanner = HighPerformanceScanner()
    system, confidence, source = scanner._detect_system(str(rom), file_size=rom.stat().st_size)

    assert system == "NES"
    assert source == "magic-bytes"
    assert confidence >= 0.85