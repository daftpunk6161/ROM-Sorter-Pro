import json
import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_retroarch_playlist_export(tmp_path):
    from src.app.models import SortAction, SortPlan
    from src.ui.mvp.export_utils import write_retroarch_playlist

    dest_root = tmp_path / "dest"
    dest_root.mkdir()
    target = dest_root / "NES" / "Game A.nes"
    target.parent.mkdir(parents=True, exist_ok=True)

    action = SortAction(
        input_path=str(tmp_path / "Game A.nes"),
        detected_system="NES",
        planned_target_path=str(target),
        action="copy",
        status="planned",
    )
    plan = SortPlan(dest_path=str(dest_root), mode="copy", on_conflict="rename", actions=[action])

    playlist_path = tmp_path / "roms.lpl"
    write_retroarch_playlist(plan, str(playlist_path))

    payload = json.loads(playlist_path.read_text(encoding="utf-8"))
    assert payload["items"]
    assert payload["items"][0]["label"] == "Game A"
    assert "Game A.nes" in payload["items"][0]["path"]
