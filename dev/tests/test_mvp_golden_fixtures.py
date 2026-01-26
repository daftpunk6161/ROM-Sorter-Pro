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


def _normalize_scan_paths(payload: dict, tmp_path: Path) -> dict:
    def _norm(value):
        if isinstance(value, str):
            return value.replace(str(tmp_path), "<TMP>").replace("\\", "/")
        return value

    return {
        "source_path": _norm(payload["source_path"]),
        "stats": payload["stats"],
        "cancelled": payload["cancelled"],
        "items": [
            {
                "input_path": _norm(item["input_path"]),
                "detected_system": item["detected_system"],
                "detection_source": item["detection_source"],
                "detection_confidence": item["detection_confidence"],
                "is_exact": item["is_exact"],
                "signals": item["signals"],
                "candidates": item["candidates"],
            }
            for item in payload["items"]
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


def test_golden_scan_fixture(tmp_path: Path):
    from src.app.controller import ScanItem, ScanResult
    from src.ui.mvp.export_utils import scan_report_to_dict

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
                raw={"signals": ["EXT"], "candidates": ["NES"]},
            )
        ],
        stats={"total": 1},
        cancelled=False,
    )

    payload = scan_report_to_dict(scan)
    fixture_path = ROOT / "dev" / "tests" / "fixtures" / "golden_scan.json"
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert _normalize_scan_paths(payload, tmp_path) == expected


def test_golden_identify_fixture(tmp_path: Path):
    from src.app.controller import ScanItem, identify

    rom = tmp_path / "game.rom"
    rom.write_text("data", encoding="utf-8")

    items = [ScanItem(input_path=str(rom), detected_system="Unknown")]
    config = {"dats": {"index_path": str(tmp_path / "missing.sqlite")}}

    results = identify(items, config=config)
    payload = [
        {
            "platform_id": r.platform_id,
            "confidence": r.confidence,
            "is_exact": r.is_exact,
            "signals": r.signals,
            "candidates": r.candidates,
            "reason": r.reason,
            "input_kind": r.input_kind,
            "normalized_artifact": r.normalized_artifact,
        }
        for r in results
    ]

    fixture_path = ROOT / "dev" / "tests" / "fixtures" / "golden_identify.json"
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert payload == expected
