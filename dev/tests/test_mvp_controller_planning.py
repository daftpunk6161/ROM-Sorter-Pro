import sys
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_plan_sort_is_deterministic(tmp_path):
    from src.app.controller import ScanItem, ScanResult, plan_sort

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    # Create two fake ROM files
    a = source / "b.rom"
    b = source / "a.rom"
    a.write_text("b")
    b.write_text("a")

    scan = ScanResult(
        source_path=str(source),
        items=[
            ScanItem(input_path=str(a), detected_system="NES"),
            ScanItem(input_path=str(b), detected_system="NES"),
        ],
        stats={},
        cancelled=False,
    )

    plan1 = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
    plan2 = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")

    assert [x.input_path for x in plan1.actions] == [x.input_path for x in plan2.actions]
    assert [x.planned_target_path for x in plan1.actions] == [x.planned_target_path for x in plan2.actions]


def test_plan_sort_rename_conflict(tmp_path):
    from src.app.controller import ScanItem, ScanResult, plan_sort

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "game.rom"
    rom.write_text("x")

    # Create a conflicting target file
    (dest / "NES").mkdir()
    (dest / "NES" / "game.rom").write_text("existing")

    scan = ScanResult(
        source_path=str(source),
        items=[ScanItem(input_path=str(rom), detected_system="NES")],
        stats={},
        cancelled=False,
    )

    plan = plan_sort(scan, str(dest), mode="copy", on_conflict="rename")
    assert len(plan.actions) == 1
    assert plan.actions[0].planned_target_path is not None
    assert plan.actions[0].planned_target_path.endswith("game (1).rom")


def test_plan_sort_low_confidence_goes_to_unknown(tmp_path):
    from src.app.controller import ScanItem, ScanResult, plan_sort
    from src.config import Config

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "game.rom"
    rom.write_text("x")

    scan = ScanResult(
        source_path=str(source),
        items=[
            ScanItem(
                input_path=str(rom),
                detected_system="NES",
                detection_confidence=0.5,
                detection_source="extension-unique",
            )
        ],
        stats={},
        cancelled=False,
    )

    cfg = Config(
        {
            "features": {
                "sorting": {
                    "create_unknown_folder": True,
                    "unknown_folder_name": "Unknown",
                    "confidence_threshold": 0.95,
                }
            }
        }
    )

    plan = plan_sort(scan, str(dest), config=cfg, mode="copy", on_conflict="rename")
    assert len(plan.actions) == 1
    assert plan.actions[0].planned_target_path is not None
    assert "Unknown" in plan.actions[0].planned_target_path


def test_plan_sort_low_confidence_skips_when_disabled(tmp_path):
    from src.app.controller import ScanItem, ScanResult, plan_sort
    from src.config import Config

    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()

    rom = source / "game.rom"
    rom.write_text("x")

    scan = ScanResult(
        source_path=str(source),
        items=[
            ScanItem(
                input_path=str(rom),
                detected_system="NES",
                detection_confidence=0.5,
                detection_source="extension-unique",
            )
        ],
        stats={},
        cancelled=False,
    )

    cfg = Config(
        {
            "features": {
                "sorting": {
                    "create_unknown_folder": False,
                    "confidence_threshold": 0.95,
                }
            }
        }
    )

    plan = plan_sort(scan, str(dest), config=cfg, mode="copy", on_conflict="rename")
    assert len(plan.actions) == 1
    assert plan.actions[0].planned_target_path is None
    assert plan.actions[0].status.startswith("skipped")


def test_diff_sort_plans_counts_changes(tmp_path):
    from src.app.controller import diff_sort_plans
    from src.app.models import SortAction, SortPlan

    plan_a = SortPlan(
        dest_path=str(tmp_path / "dest"),
        mode="copy",
        on_conflict="rename",
        actions=[
            SortAction(
                input_path=str(tmp_path / "a.rom"),
                detected_system="NES",
                planned_target_path=str(tmp_path / "dest" / "a.rom"),
                action="copy",
                status="planned",
            ),
            SortAction(
                input_path=str(tmp_path / "b.rom"),
                detected_system="NES",
                planned_target_path=str(tmp_path / "dest" / "b.rom"),
                action="copy",
                status="planned",
            ),
        ],
    )

    plan_b = SortPlan(
        dest_path=str(tmp_path / "dest"),
        mode="copy",
        on_conflict="rename",
        actions=[
            SortAction(
                input_path=str(tmp_path / "a.rom"),
                detected_system="NES",
                planned_target_path=str(tmp_path / "dest" / "a-renamed.rom"),
                action="copy",
                status="planned",
            ),
            SortAction(
                input_path=str(tmp_path / "c.rom"),
                detected_system="NES",
                planned_target_path=str(tmp_path / "dest" / "c.rom"),
                action="copy",
                status="planned",
            ),
        ],
    )

    diff = diff_sort_plans(plan_a, plan_b)
    assert diff["added"] == 1
    assert diff["removed"] == 1
    assert diff["changed"] == 1
