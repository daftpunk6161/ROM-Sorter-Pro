import json
import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_launchbox_import_creates_overrides(tmp_path):
    from src.app.frontend_imports import import_launchbox_csv_to_overrides
    from src.config import Config

    csv_path = tmp_path / "launchbox.csv"
    csv_path.write_text(
        "Title,ApplicationPath,Platform\nGame A,C:/ROMs/NES/Game A.nes,NES\n",
        encoding="utf-8",
    )

    override_path = tmp_path / "overrides.json"
    cfg = Config({"identification_overrides": {"path": str(override_path)}})

    report = import_launchbox_csv_to_overrides(str(csv_path), config=cfg)

    assert report.imported_rows == 1
    data = json.loads(override_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data[0]["platform_id"] == "NES"
