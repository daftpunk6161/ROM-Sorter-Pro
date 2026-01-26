import sys
import time
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_hash_cache_invalidates_on_file_change(tmp_path):
    from src.core.file_utils import calculate_file_hash
    from src.core import file_utils

    test_file = tmp_path / "rom.bin"
    test_file.write_bytes(b"abc")

    file_utils._calculate_file_hash_cached.cache_clear()
    hits_before = file_utils._calculate_file_hash_cached.cache_info().hits
    hash_before = calculate_file_hash(test_file, algorithm="md5")
    assert hash_before is not None

    hash_cached = calculate_file_hash(test_file, algorithm="md5")
    hits_after = file_utils._calculate_file_hash_cached.cache_info().hits
    assert hash_cached == hash_before
    assert hits_after > hits_before

    test_file.write_bytes(b"abcd")
    time.sleep(0.01)

    hash_after = calculate_file_hash(test_file, algorithm="md5")
    assert hash_after is not None
    assert hash_before != hash_after
