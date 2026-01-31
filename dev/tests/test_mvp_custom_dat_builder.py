import sys
from pathlib import Path
import xml.etree.ElementTree as ET

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_custom_dat_builder(tmp_path):
    from src.app.models import ScanItem, ScanResult
    from src.dats.custom_dat_builder import build_custom_dat

    rom = tmp_path / "game.rom"
    rom.write_text("data", encoding="utf-8")

    scan = ScanResult(
        source_path=str(tmp_path),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    output = tmp_path / "custom.dat"
    report = build_custom_dat(scan, str(output), dat_name="Test DAT")

    assert report.total_items == 1
    tree = ET.parse(output)
    rom_nodes = tree.getroot().findall(".//rom")
    assert rom_nodes
    assert "sha1" in rom_nodes[0].attrib
