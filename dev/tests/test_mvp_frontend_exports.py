import sys
from pathlib import Path
import xml.etree.ElementTree as ET

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_frontend_exports_from_plan(tmp_path):
    from src.app.controller import SortAction, SortPlan
    from src.ui.mvp.export_utils import write_emulationstation_gamelist, write_launchbox_csv

    dest_path = tmp_path / "dest"
    plan = SortPlan(
        dest_path=str(dest_path),
        mode="copy",
        on_conflict="skip",
        actions=[
            SortAction(
                input_path=str(tmp_path / "src" / "game_a.nes"),
                detected_system="NES",
                planned_target_path=str(dest_path / "NES" / "Game A.nes"),
                action="copy",
                status="planned",
            ),
            SortAction(
                input_path=str(tmp_path / "src" / "game_b.nes"),
                detected_system="NES",
                planned_target_path=str(dest_path / "NES" / "Game B.nes"),
                action="copy",
                status="skipped",
            ),
            SortAction(
                input_path=str(tmp_path / "src" / "game_c.nes"),
                detected_system="NES",
                planned_target_path=None,
                action="copy",
                status="error",
                error="boom",
            ),
        ],
    )

    xml_path = tmp_path / "gamelist.xml"
    csv_path = tmp_path / "launchbox.csv"

    write_emulationstation_gamelist(plan, str(xml_path))
    write_launchbox_csv(plan, str(csv_path))

    tree = ET.parse(xml_path)
    root = tree.getroot()
    games = root.findall("game")
    assert len(games) == 1
    path_text = games[0].findtext("path")
    assert path_text is not None
    assert "Game A.nes" in path_text
    assert games[0].findtext("name") == "Game A"
    assert games[0].findtext("platform") == "NES"

    rows = csv_path.read_text(encoding="utf-8").strip().splitlines()
    assert rows[0].startswith("Title,ApplicationPath,Platform")
    assert "Game A" in rows[1]
    assert "NES" in rows[1]
