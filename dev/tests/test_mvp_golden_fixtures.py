import json
import sys
from pathlib import Path

import pytest

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _normalize_paths(payload: dict, tmp_path: Path) -> dict:
    def _norm(value):
        if isinstance(value, str):
            return value.replace(str(tmp_path), "<TMP>").replace("\\", "/")
        return value

    return {
        "dest_path": _norm(payload["dest_path"]),
        "mode": payload["mode"],
        "on_conflict": payload["on_conflict"],
        "actions": [
            {
                "input_path": _norm(action["input_path"]),
                "detected_system": action["detected_system"],
                "planned_target_path": _norm(action["planned_target_path"]),
                "action": action["action"],
                "status": action["status"],
                "error": action["error"],
                "conversion_tool": action["conversion_tool"],
                "conversion_tool_key": action["conversion_tool_key"],
                "conversion_args": action["conversion_args"],
                "conversion_rule": action["conversion_rule"],
                "conversion_output_extension": action["conversion_output_extension"],
            }
            for action in payload["actions"]
        ],
    }


@pytest.mark.integration
def test_golden_plan_fixture(tmp_path: Path):
    from src.app.controller import ScanItem, ScanResult, plan_sort
    from src.config import Config

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    rom_path = src_dir / "game.nes"
    rom_path.write_text("data", encoding="utf-8")

    scan = ScanResult(
        source_path=str(src_dir),
        items=[
            ScanItem(
                input_path=str(rom_path),
                detected_system="NES",
                detection_source="manual",
                detection_confidence=1.0,
                is_exact=True,
            )
        ],
        stats={"total": 1},
        cancelled=False,
    )

    cfg = Config({"features": {"sorting": {"create_console_folders": True}}})
    plan = plan_sort(scan, str(tmp_path / "dest"), config=cfg, mode="copy", on_conflict="rename")

    payload = {
        "dest_path": plan.dest_path,
        "mode": plan.mode,
        "on_conflict": plan.on_conflict,
        "actions": [
            {
                "input_path": action.input_path,
                "detected_system": action.detected_system,
                "planned_target_path": action.planned_target_path,
                "action": action.action,
                "status": action.status,
                "error": action.error,
                "conversion_tool": action.conversion_tool,
                "conversion_tool_key": action.conversion_tool_key,
                "conversion_args": action.conversion_args,
                "conversion_rule": action.conversion_rule,
                "conversion_output_extension": action.conversion_output_extension,
            }
            for action in plan.actions
        ],
    }

    fixture_path = ROOT / "dev" / "tests" / "fixtures" / "golden_plan.json"
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert _normalize_paths(payload, tmp_path) == expected
