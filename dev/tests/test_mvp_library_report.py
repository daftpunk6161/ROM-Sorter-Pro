from __future__ import annotations

from src.app.controller import ScanItem, ScanResult, SortAction, SortPlan, build_library_report


def test_build_library_report_scan_and_plan() -> None:
    scan = ScanResult(
        source_path="/roms",
        items=[
            ScanItem(input_path="a.rom", detected_system="NES", region="Europe"),
            ScanItem(input_path="b.rom", detected_system="Unknown", region=None),
            ScanItem(input_path="c.rom", detected_system="NES", region="Europe"),
        ],
        stats={},
        cancelled=False,
    )

    plan = SortPlan(
        dest_path="/dest",
        mode="copy",
        on_conflict="rename",
        actions=[
            SortAction(
                input_path="a.rom",
                detected_system="NES",
                planned_target_path="/dest/a.rom",
                action="copy",
                status="planned",
            ),
            SortAction(
                input_path="b.rom",
                detected_system="Unknown",
                planned_target_path=None,
                action="skip",
                status="skipped",
            ),
        ],
    )

    report = build_library_report(scan, plan)
    assert report["scan"]["total_items"] == 3
    assert report["scan"]["unknown_items"] == 1
    assert report["scan"]["systems"]["NES"] == 2
    assert report["plan"]["total_actions"] == 2
    assert report["plan"]["actions"]["copy"] == 1
    assert report["plan"]["statuses"]["skipped"] == 1