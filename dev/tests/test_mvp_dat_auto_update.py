import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_dat_auto_update_from_file(tmp_path):
    from src.config import Config
    from src.dats.auto_update import update_dat_sources

    source = tmp_path / "source.dat"
    source.write_text("DAT", encoding="utf-8")
    dest = tmp_path / "dest.dat"

    cfg = Config(
        {
            "dats": {
                "auto_update": {
                    "sources": [
                        {
                            "name": "Test DAT",
                            "url": str(source),
                            "dest": str(dest),
                        }
                    ]
                }
            }
        }
    )

    report = update_dat_sources(cfg)

    assert report.updated == 1
    assert dest.read_text(encoding="utf-8") == "DAT"
