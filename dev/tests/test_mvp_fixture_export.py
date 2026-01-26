import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_export_fixtures_creates_archive(tmp_path):
    from scripts.fixtures.export_fixtures import export_fixtures

    out = export_fixtures(str(tmp_path / "fixtures.tar.gz"))
    assert out.exists()
    assert out.stat().st_size > 0
