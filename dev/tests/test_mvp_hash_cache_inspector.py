import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_hash_cache_stats_and_clear(tmp_path):
    from src.core.file_utils import calculate_file_hash, get_hash_cache_stats, clear_hash_cache

    rom = tmp_path / "game.rom"
    rom.write_text("data", encoding="utf-8")

    _ = calculate_file_hash(rom, algorithm="sha1")
    stats = get_hash_cache_stats()
    assert stats["currsize"] >= 1

    clear_hash_cache()
    stats_after = get_hash_cache_stats()
    assert stats_after["currsize"] == 0
