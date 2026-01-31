import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_db_integrity_check(tmp_path):
    from src.app.db_controller import init_db, check_db_integrity

    db_path = tmp_path / "roms.db"
    init_db(str(db_path))
    result = check_db_integrity(str(db_path))

    assert str(result).lower() in {"ok", "ok"}
